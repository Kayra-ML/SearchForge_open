import io
import re
import unicodedata
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. PDF text extraction disabled.")


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _find_snippet(text: str, query: str, context_chars: int = 150) -> Optional[str]:
    normalized_text = _normalize_text(text)
    normalized_query = _normalize_text(query)

    pattern = re.compile(re.escape(normalized_query), re.IGNORECASE)
    match = pattern.search(normalized_text)
    if not match:
        return None

    start = max(0, match.start() - context_chars)
    end = min(len(normalized_text), match.end() + context_chars)

    snippet = normalized_text[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(normalized_text):
        snippet = snippet + "..."

    snippet = " ".join(snippet.split())
    return snippet


def extract_matches_from_pdf(
    pdf_bytes: bytes,
    query: str,
    max_snippets: int = 3,
    context_chars: int = 150,
) -> Tuple[List[dict], bool]:
    """
    Returns (matches, ocr_required).
    matches is a list of {"page": int, "snippet": str}
    ocr_required is True if PDF has no extractable text.
    """
    if not PYMUPDF_AVAILABLE:
        return [], False

    matches = []
    total_text_found = False

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_number in range(len(doc)):
            if len(matches) >= max_snippets:
                break
            page = doc[page_number]
            text = page.get_text()
            if text.strip():
                total_text_found = True
            snippet = _find_snippet(text, query, context_chars)
            if snippet:
                matches.append({
                    "page": page_number + 1,
                    "snippet": snippet,
                })
        doc.close()
    except Exception as e:
        logger.error("PDF extraction error: %s", type(e).__name__)
        return [], False

    ocr_required = not total_text_found and len(matches) == 0
    return matches, ocr_required


def check_pdf_has_text(pdf_bytes: bytes) -> bool:
    if not PYMUPDF_AVAILABLE:
        return False
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_number in range(min(3, len(doc))):
            if doc[page_number].get_text().strip():
                doc.close()
                return True
        doc.close()
        return False
    except Exception:
        return False