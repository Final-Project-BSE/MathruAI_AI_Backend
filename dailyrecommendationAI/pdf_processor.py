import os
import fitz
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from typing import List, Tuple
import logging
from dailyrecommendationAI.config import Config

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except:
    pass

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.chunk_size = Config.CHUNK_SIZE
        self.overlap = Config.CHUNK_OVERLAP
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file has allowed extension"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()
            
            doc.close()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    #divides the long PDF text into smaller, overlapping chunks
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into overlapping chunks"""
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.overlap
        
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_pdf(self, pdf_path: str) -> Tuple[bool, List[str], str]:
        """Process PDF and return success status, chunks, and any error message"""
        try:
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                return False, [], "No text extracted from PDF"
            
            # Chunk text
            chunks = self.chunk_text(text)
            
            if not chunks:
                return False, [], "No chunks created from PDF text"
            
            logger.info(f"Successfully processed PDF with {len(chunks)} chunks")
            return True, chunks, ""
            
        except Exception as e:
            error_msg = f"Error processing PDF: {e}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def validate_pdf_content(self, text: str) -> bool:
        """Validate if extracted text contains meaningful content"""
        if not text or len(text.strip()) < 50:
            return False
        
        # Check if text contains meaningful words (not just special characters)
        words = word_tokenize(text.lower())
        meaningful_words = [word for word in words if word.isalpha() and len(word) > 2]
        
        return len(meaningful_words) > 10
    
    def get_text_statistics(self, text: str) -> dict:
        """Get statistics about the extracted text"""
        if not text:
            return {}
        
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        return {
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'average_sentence_length': len(words) / len(sentences) if sentences else 0
        }