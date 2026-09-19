"""Temporary check that the Groq connection works. Run: python test_groq.py"""
import json
import logging

from services.groq_service import MODEL, LLMError, call_llm

logging.basicConfig(level=logging.WARNING)
print(f"Model: {MODEL}\n")

print("Test 1: plain text")
try:
    print("Reply:", call_llm("Answer in one short sentence.", "Say hello to ClauseClear."))
except LLMError as err:
    print("FAILED:", err)

print("\nTest 2: JSON mode")
raw = ""
try:
    raw = call_llm(
        'Reply only with a JSON object like {"ok": true, "word": "..."}',
        "Return JSON with ok=true and word=hello.",
        json_mode=True,
    )
    print("Parsed:", json.loads(raw))
except LLMError as err:
    print("FAILED:", err)
except json.JSONDecodeError:
    print("FAILED: reply was not valid JSON:", raw)