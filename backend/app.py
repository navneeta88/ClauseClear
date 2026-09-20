"""ClauseClear backend API."""
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from services.document_parser import DocumentParseError, extract_text
from services.groq_service import (
    LLMError,
    analyze_risks,
    answer_question,
    generate_checklist,
    simplify_document,
)
from services.s3_service import upload_original

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MAX_FILE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
DOC_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")  # exactly what uuid4().hex produces
MAX_DOC_CHARS = int(os.getenv("MAX_DOC_CHARS", "16000"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024

# Only our React dev server may call this API from a browser.
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Rate limiting protects the AI quota. In-memory storage is fine for one local server.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["300 per hour"],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# Errors and headers
# ---------------------------------------------------------------------------
class ApiError(Exception):
    """An error with a message that is safe to show to the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({"error": str(err)}), err.status


@app.errorhandler(LLMError)
def handle_llm_error(err):
    return jsonify({"error": str(err)}), err.status_code


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": f"File is too large. Maximum size is {MAX_FILE_MB} MB."}), 413


@app.errorhandler(429)
def too_many_requests(_error):
    return jsonify({"error": "Too many requests. Please wait a minute and try again."}), 429


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def server_error(_error):
    # Details stay in the server log. Users never see stack traces.
    return jsonify({"error": "Something went wrong on the server. Please try again."}), 500


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def looks_like_expected_type(ext, header):
    """Check the file's first bytes, not just its extension."""
    if ext == ".pdf":
        return header.startswith(b"%PDF-")
    if ext == ".docx":
        return header.startswith(b"PK\x03\x04")  # DOCX files are ZIP archives
    return False


def get_document_text(payload):
    """Validate the document_id from a request and return that document's text."""
    document_id = payload.get("document_id") if isinstance(payload, dict) else None
    # Strict pattern check: stops path tricks like "../../secret"
    if not isinstance(document_id, str) or not DOC_ID_PATTERN.match(document_id):
        raise ApiError("Invalid document ID.")

    text_file = UPLOAD_DIR / document_id / "text.txt"
    if not text_file.is_file():
        raise ApiError("Document not found. Please upload it again.", 404)

    text = text_file.read_text(encoding="utf-8")
    if len(text) > MAX_DOC_CHARS:
        raise ApiError(
            "This document is too long for the AI service's current limits "
            f"(limit: {MAX_DOC_CHARS:,} characters, this one has {len(text):,}).",
            422,
        )
    return text


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
@limiter.exempt
def health():
    return jsonify({
        "status": "ok",
        "service": "ClauseClear API",
        "groq_key_configured": bool(os.getenv("GROQ_API_KEY")),
    })


@app.post("/api/upload")
@limiter.limit("10 per minute")
def upload():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "No file was uploaded."}), 400

    raw_name = file.filename
    ext = Path(raw_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Only PDF and DOCX files are supported."}), 400

    header = file.stream.read(8)
    file.stream.seek(0)
    if not looks_like_expected_type(ext, header):
        return jsonify({"error": "This file is empty or is not a valid PDF/DOCX."}), 400

    # Display name only. On disk we never use the user's filename.
    safe_name = secure_filename(raw_name)
    if not safe_name.lower().endswith(ext):
        safe_name = f"document{ext}"

    document_id = uuid.uuid4().hex
    doc_dir = UPLOAD_DIR / document_id
    doc_dir.mkdir(parents=True)
    saved_path = doc_dir / f"original{ext}"
    file.save(saved_path)

    # Extract text. If the file can't be read, delete it and report why.
    try:
        text, page_count = extract_text(saved_path)
    except DocumentParseError as err:
        shutil.rmtree(doc_dir, ignore_errors=True)
        return jsonify({"error": str(err)}), 422

    (doc_dir / "text.txt").write_text(text, encoding="utf-8")
    stored_in_s3 = upload_original(saved_path, document_id, ext)

    meta = {
        "document_id": document_id,
        "filename": safe_name,
        "extension": ext,
        "size_bytes": saved_path.stat().st_size,
        "char_count": len(text),
        "word_count": len(text.split()),
        "page_count": page_count,
        "stored_in_s3": stored_in_s3,
    }
    (doc_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return jsonify(meta), 201


@app.post("/api/simplify")
@limiter.limit("10 per minute")
def simplify():
    text = get_document_text(request.get_json(silent=True))
    return jsonify(simplify_document(text))


@app.post("/api/analyze-risks")
@limiter.limit("10 per minute")
def risks():
    text = get_document_text(request.get_json(silent=True))
    return jsonify(analyze_risks(text))


@app.post("/api/checklist")
@limiter.limit("10 per minute")
def checklist():
    text = get_document_text(request.get_json(silent=True))
    return jsonify(generate_checklist(text))


@app.post("/api/chat")
@limiter.limit("30 per minute")
def chat():
    payload = request.get_json(silent=True)
    text = get_document_text(payload)
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ApiError("Please type a question.")
    if len(question) > 500:
        raise ApiError("Questions can be at most 500 characters.")
    return jsonify(answer_question(text, question.strip(), payload.get("history")))


if __name__ == "__main__":
    # Debug (auto-reload) is for local development only. Set FLASK_DEBUG=0 for any deployment.
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG", "1") == "1")