"""Extract plain text from PDF and DOCX files."""
import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

MIN_TEXT_CHARS = 50


class DocumentParseError(Exception):
    """Raised with a user-friendly message when a file can't be read."""

# Fancy dashes and invisible characters that can trip up AI models and text matching.
_CHAR_MAP = str.maketrans({
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2212": "-",
    "\u00a0": " ", "\u202f": " ", "\u200b": "", "\u00ad": "",
})


def _clean(text):
    text = text.replace("\x00", "").translate(_CHAR_MAP)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def _extract_pdf(path):
    reader = PdfReader(str(path))
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise DocumentParseError(
            "This PDF is password-protected. Please upload an unlocked copy."
        )
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages), len(reader.pages)


def _extract_docx(path):
    """Read paragraphs AND tables, in the order they appear in the document."""
    doc = Document(str(path))
    lines = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            text = Paragraph(child, doc).text.strip()
            if text:
                lines.append(text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, doc).rows:
                cells = []
                for cell in row.cells:
                    value = cell.text.strip()
                    # merged cells repeat the same text; skip duplicates
                    if value and (not cells or cells[-1] != value):
                        cells.append(value)
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


def extract_text(path):
    """Return (text, page_count). page_count is None for DOCX files."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            text, pages = _extract_pdf(path)
        elif ext == ".docx":
            text, pages = _extract_docx(path), None
        else:
            raise DocumentParseError("Only PDF and DOCX files are supported.")
    except DocumentParseError:
        raise
    except Exception as exc:  # corrupted or unusual files
        raise DocumentParseError(
            "Could not read this file. It may be corrupted or protected."
        ) from exc

    text = _clean(text)
    if len(text) < MIN_TEXT_CHARS:
        raise DocumentParseError(
            "No readable text was found. Scanned or image-only documents "
            "aren't supported yet."
        )
    return text, pages