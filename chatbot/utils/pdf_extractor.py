"""
PDF text extraction utilities.
"""
import fitz  # PyMuPDF
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text from a PDF file with better error handling.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    text = ""
    
    try:
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():  # Only add non-empty pages
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
                    
        logger.info(f"Successfully extracted {len(text)} characters from {file_path}")
        
    except Exception as e:
        logger.error(f"Error extracting from PDF {file_path}: {str(e)}")
        
    return text


def extract_text_from_multiple_pdfs(file_paths: list) -> dict:
    """
    Extract text from multiple PDF files.
    
    Args:
        file_paths (list): List of PDF file paths
        
    Returns:
        dict: Dictionary mapping file paths to extracted text
    """
    results = {}
    
    for file_path in file_paths:
        try:
            text = extract_text_from_pdf(file_path)
            if text:
                results[file_path] = text
            else:
                logger.warning(f"No text extracted from {file_path}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            
    return results


def get_pdf_metadata(file_path: str) -> Optional[dict]:
    """
    Extract metadata from a PDF file.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        Optional[dict]: PDF metadata or None if error
    """
    try:
        with fitz.open(file_path) as doc:
            metadata = doc.metadata
            metadata['page_count'] = doc.page_count
            return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
        return None