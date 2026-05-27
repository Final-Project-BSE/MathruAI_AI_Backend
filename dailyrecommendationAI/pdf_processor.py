import fitz
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from typing import List, Tuple
import logging

from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)

for resource in ('punkt',):
    try:
        nltk.data.find(f'tokenizers/{resource}')
    except LookupError:
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            logger.warning('Could not download NLTK resource: %s', resource)


class PDFProcessor:
    def __init__(self):
        self.chunk_size = Config.CHUNK_SIZE
        self.overlap = Config.CHUNK_OVERLAP
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS

    def allowed_file(self, filename: str) -> bool:
        """Check if file has allowed extension."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            text_parts = []
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            return ''.join(text_parts)
        except Exception as e:
            logger.error('Error extracting text from PDF: %s', e)
            return ''

    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into overlapping chunks by sentence."""
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap if overlap is not None else self.overlap

        sentences = sent_tokenize(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_len = len(sentence) + 1

            if current_length + sentence_len <= chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_len
                continue

            if current_chunk:
                chunks.append(' '.join(current_chunk))

            if overlap > 0 and current_chunk:
                overlap_sentences = []
                overlap_length = 0
                for previous_sentence in reversed(current_chunk):
                    previous_length = len(previous_sentence) + 1
                    if overlap_length + previous_length > overlap:
                        break
                    overlap_sentences.insert(0, previous_sentence)
                    overlap_length += previous_length
                current_chunk = overlap_sentences[:]
                current_length = sum(len(s) + 1 for s in current_chunk)
            else:
                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_length += sentence_len

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def process_pdf(self, pdf_path: str) -> Tuple[bool, List[str], str]:
        """Process PDF and return success status, chunks and error message."""
        try:
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                return False, [], 'No text extracted from PDF'

            chunks = self.chunk_text(text)
            if not chunks:
                return False, [], 'No chunks created from PDF text'

            logger.info('Successfully processed PDF with %s chunks', len(chunks))
            return True, chunks, ''

        except Exception as e:
            error_msg = f'Error processing PDF: {e}'
            logger.error(error_msg)
            return False, [], error_msg

    def validate_pdf_content(self, text: str) -> bool:
        """Validate if extracted text contains meaningful content."""
        if not text or len(text.strip()) < 50:
            return False

        words = word_tokenize(text.lower())
        meaningful_words = [word for word in words if word.isalpha() and len(word) > 2]
        return len(meaningful_words) > 10

    def get_text_statistics(self, text: str) -> dict:
        """Get statistics about the extracted text."""
        if not text:
            return {}

        sentences = sent_tokenize(text)
        words = word_tokenize(text)

        return {
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'average_sentence_length': len(words) / len(sentences) if sentences else 0,
        }
