"""Checks that AI output is really grounded in the uploaded document."""
import re

_REPLACEMENTS = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2212": "-", "\u00a0": " ",
})


def normalize(text):
    """Lowercase, unify quotes/dashes and collapse whitespace for comparison."""
    text = str(text).translate(_REPLACEMENTS).lower()
    return re.sub(r"\s+", " ", text).strip()


def is_grounded(excerpt, document_text):
    """True if the excerpt appears in the document.

    An excerpt may use "..." to skip words; every piece around the "..."
    must then appear in the document.
    """
    haystack = normalize(document_text)
    pieces = [normalize(p).strip(" .,;:\"'") for p in re.split(r"\.\.\.|\u2026", excerpt)]
    pieces = [p for p in pieces if len(p) >= 4]
    if not pieces or len(normalize(excerpt)) < 12:
        return False
    return all(piece in haystack for piece in pieces)