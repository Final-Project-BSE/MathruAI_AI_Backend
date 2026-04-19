"""PDF text extraction utilities."""
import logging
from typing import Dict, List, Optional

import fitz

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    text_parts: List[str] = []
    try:
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text()
                if page_text and page_text.strip():
                    text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")
        text = "".join(text_parts)
        logger.info("Successfully extracted %s characters from %s", len(text), file_path)
        return text
    except Exception as exc:
        logger.error("Error extracting from PDF %s: %s", file_path, exc)
        return ""


def extract_text_from_multiple_pdfs(file_paths: list) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for file_path in file_paths:
        text = extract_text_from_pdf(file_path)
        if text:
            results[file_path] = text
        else:
            logger.warning("No text extracted from %s", file_path)
    return results


def get_pdf_metadata(file_path: str) -> Optional[dict]:
    try:
        with fitz.open(file_path) as doc:
            metadata = dict(doc.metadata or {})
            metadata['page_count'] = doc.page_count
            return metadata
    except Exception as exc:
        logger.error("Error extracting metadata from %s: %s", file_path, exc)
        return None
