"""Thin wrapper around the Groq API. Every AI call in ClauseClear goes through here."""
import json
import logging
import re
import os

from dotenv import load_dotenv
from services.grounding import is_grounded
from services.prompts import (
    ADVICE_REFUSAL,
    CHAT_SYSTEM_PROMPT,
    CHECKLIST_SYSTEM_PROMPT,
    DISCLAIMER,
    NOT_ADDRESSED,
    RISK_SYSTEM_PROMPT,
    SIMPLIFY_SYSTEM_PROMPT,
    build_chat_message,
    wrap_document,
)
from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    Groq,
    RateLimitError,
)

load_dotenv()
logger = logging.getLogger(__name__)

# Configurable so a retired model can be swapped without touching code.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TIMEOUT_SECONDS = 60

_client = None


class LLMError(Exception):
    """An AI-call failure with a message that is safe to show to the user."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise LLMError("The AI service is not configured on the server.", 500)
        _client = Groq(api_key=api_key, timeout=TIMEOUT_SECONDS)
    return _client


def call_llm(system_prompt, user_message, *, json_mode=False,
             temperature=0.2, max_tokens=4096):
    """Send one request to Groq and return the reply text.

    Raises LLMError (with a user-safe message) if anything goes wrong.
    """
    client = _get_client()

    extra = {}
    if json_mode:
        extra["response_format"] = {"type": "json_object"}
        # gpt-oss models "think" before answering; low effort saves tokens and time.
    if MODEL.startswith("openai/gpt-oss"):
        extra["extra_body"] = {"reasoning_effort": "low"}

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            **extra,
        )
    except AuthenticationError as exc:
        logger.warning("Groq rejected the API key: %s", exc)
        raise LLMError("The AI service rejected the server's API key.", 500) from exc
    except RateLimitError as exc:
        logger.warning("Groq rate limit: %s", exc)
        raise LLMError(
            "The AI service is busy (rate limit reached). "
            "Please wait a minute and try again.", 429,
        ) from exc
    except APIConnectionError as exc:  # also covers timeouts
        logger.warning("Could not reach Groq: %s", exc)
        raise LLMError(
            "Could not reach the AI service. Please try again.", 503
        ) from exc
    except APIStatusError as exc:
        # Full details go to the server log only, never to the user.
        logger.warning("Groq API error %s: %s", exc.status_code, exc)
        if exc.status_code == 413:
            raise LLMError(
                "This document is too long for the AI service's current limits.", 413
            ) from exc
        raise LLMError("The AI service returned an error. Please try again.", 502) from exc

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise LLMError("The AI returned an empty response. Please try again.")
    return content.strip()
# ---------------------------------------------------------------------------
# Helpers for reading and validating AI output
# ---------------------------------------------------------------------------
def _parse_json(raw):
    """Turn the model's reply into a dict, or raise a user-safe LLMError."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        try:
            data = json.loads(raw[start:end + 1]) if start != -1 and end > start else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        logger.warning("AI reply was not a valid JSON object: %.200s", raw)
        raise LLMError("The AI returned an unreadable response. Please try again.")
    return data


# Models sometimes write special hyphens and spaces; store plain ones.
_PLAIN = str.maketrans({"\u2010": "-", "\u2011": "-", "\u00a0": " ", "\u202f": " "})


def _text(value):
    return value.translate(_PLAIN).strip() if isinstance(value, str) else ""


def _items(value):
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------------------
# Feature 1: simplification
# ---------------------------------------------------------------------------
def simplify_document(document_text):
    raw = call_llm(
        SIMPLIFY_SYSTEM_PROMPT,
        wrap_document(document_text),
        json_mode=True,
        max_tokens=3000,
    )
    data = _parse_json(raw)

    sections = []
    for item in _items(data.get("sections")):
        if isinstance(item, dict):
            title, explanation = _text(item.get("title")), _text(item.get("explanation"))
            if title and explanation:
                sections.append({"title": title, "explanation": explanation})

    obligations = [_text(x) for x in _items(data.get("key_obligations")) if _text(x)]

    dates = []
    for item in _items(data.get("key_dates")):
        if isinstance(item, dict):
            date, description = _text(item.get("date")), _text(item.get("description"))
            if date and description:
                dates.append({"date": date, "description": description})

    overview = _text(data.get("overview"))
    if not overview or not sections:
        raise LLMError("The AI returned an incomplete summary. Please try again.")

    return {
        "overview": overview,
        "sections": sections,
        "key_obligations": obligations,
        "key_dates": dates,
        "disclaimer": DISCLAIMER,  # fixed text from our code, not the AI
    }
# ---------------------------------------------------------------------------
# Feature 2: risk / clause scanner
# ---------------------------------------------------------------------------
_RISK_ORDER = {"high": 0, "medium": 1, "low": 2}

# Sentences that give advice about signing are removed by code, not just by prompt.
_ADVICE_PATTERN = re.compile(
    r"\b(do not|don't|should not|shouldn't|must not|never)\s+sign\b"
    r"|\bshould\s+(sign|accept|reject|negotiate)\b"
    r"|\b(i|we)\s+recommend\b|\bnot advisable\b",
    re.IGNORECASE,
)


def _strip_advice(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s for s in sentences if not _ADVICE_PATTERN.search(s)).strip()


def analyze_risks(document_text):
    raw = call_llm(
        RISK_SYSTEM_PROMPT,
        wrap_document(
            document_text,
            "Scan this document for important clauses following your instructions.",
        ),
        json_mode=True,
        max_tokens=3500,
    )
    data = _parse_json(raw)
    if not isinstance(data.get("risks"), list):
        raise LLMError("The AI returned an incomplete analysis. Please try again.")

    risks, dropped = [], 0
    for item in data["risks"]:
        if not isinstance(item, dict):
            dropped += 1
            continue
        excerpt = _text(item.get("clause_excerpt"))[:400]
        level = _text(item.get("risk_level")).lower()
        why = _strip_advice(_text(item.get("why_it_matters")))
        section = _text(item.get("section_reference")) or "Not specified"

        # Keep only items that are complete AND quote text really in the document.
        if level not in _RISK_ORDER or not why or not is_grounded(excerpt, document_text):
            dropped += 1
            continue
        risks.append({
            "clause_excerpt": excerpt,
            "risk_level": level,
            "why_it_matters": why,
            "section_reference": section,
        })

    if dropped:
        logger.warning("Dropped %d risk item(s) that failed validation", dropped)

    risks.sort(key=lambda r: _RISK_ORDER[r["risk_level"]])
    return {"risks": risks[:12], "disclaimer": DISCLAIMER}
# ---------------------------------------------------------------------------
# Feature 4: checklist generator
# ---------------------------------------------------------------------------
def _grounded_entries(raw_items, text_key, document_text, limit):
    """Keep entries with text and an exact supporting quote found in the document."""
    kept, dropped = [], 0
    for item in _items(raw_items):
        if not isinstance(item, dict):
            dropped += 1
            continue
        text = _strip_advice(_text(item.get(text_key)))
        evidence = _text(item.get("evidence"))[:300]
        source = _text(item.get("source_clause")) or "Not specified"
        if not text or not is_grounded(evidence, document_text):
            dropped += 1
            continue
        kept.append({text_key: text, "source_clause": source, "evidence": evidence})
    return kept[:limit], dropped


def generate_checklist(document_text):
    raw = call_llm(
        CHECKLIST_SYSTEM_PROMPT,
        wrap_document(document_text, "Create the checklist following your instructions."),
        json_mode=True,
        max_tokens=3500,
    )
    data = _parse_json(raw)
    if not any(key in data for key in ("action_items", "questions_for_lawyer", "key_dates")):
        raise LLMError("The AI returned an incomplete checklist. Please try again.")

    actions, d1 = _grounded_entries(data.get("action_items"), "item", document_text, 12)
    questions, d2 = _grounded_entries(
        data.get("questions_for_lawyer"), "question", document_text, 6
    )

    dates, d3 = [], 0
    for item in _items(data.get("key_dates")):
        if not isinstance(item, dict):
            d3 += 1
            continue
        date = _text(item.get("date"))
        description = _text(item.get("description"))
        source = _text(item.get("source_clause")) or "Not specified"
        # The date wording itself must appear in the document. Never trust a computed date.
        if not date or not description or not is_grounded(date, document_text, min_chars=5):
            d3 += 1
            continue
        dates.append({"date": date, "description": description, "source_clause": source})

    if d1 + d2 + d3:
        logger.warning(
            "Dropped checklist entries that failed validation: actions=%d questions=%d dates=%d",
            d1, d2, d3,
        )

    return {
        "action_items": actions,
        "questions_for_lawyer": questions,
        "key_dates": dates[:15],
        "disclaimer": DISCLAIMER,
    }
# ---------------------------------------------------------------------------
# Feature 3: document Q&A
# ---------------------------------------------------------------------------
def _format_history(history):
    """Turn the client's chat history into a short, sanitized text block."""
    lines = []
    for turn in _items(history)[-6:]:
        if not isinstance(turn, dict):
            continue
        role = {"user": "User", "assistant": "Assistant"}.get(turn.get("role"))
        content = _text(turn.get("content"))[:800]
        if role and content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def answer_question(document_text, question, history=None):
    raw = call_llm(
        CHAT_SYSTEM_PROMPT,
        build_chat_message(document_text, _format_history(history), question),
        json_mode=True,
        max_tokens=2000,
    )
    data = _parse_json(raw)
    kind = _text(data.get("type")).lower()

    if kind == "advice_request":
        return {"answered": False, "answer": ADVICE_REFUSAL, "sources": []}

    answer = _text(data.get("answer"))
    sources = []
    for item in _items(data.get("sources")):
        if not isinstance(item, dict):
            continue
        quote = _text(item.get("quote"))[:300]
        if is_grounded(quote, document_text):
            sources.append({
                "section": _text(item.get("section")) or "Not specified",
                "quote": quote,
            })

    # An answer is shown only if it is backed by a real quote from the document.
    if kind != "answer" or not answer or not sources:
        if kind == "answer":
            logger.warning("Answer had no verifiable quote; replaced with not-addressed reply")
        return {"answered": False, "answer": NOT_ADDRESSED, "sources": []}

    return {"answered": True, "answer": answer, "sources": sources[:3]}