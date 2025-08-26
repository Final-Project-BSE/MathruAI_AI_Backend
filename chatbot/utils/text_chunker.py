"""
Advanced text chunking utilities with multiple strategies.
"""
import re
import tiktoken
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from typing import List
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Advanced text chunking with multiple strategies."""
    
    def __init__(self, max_chunk_size: int = 800, overlap_size: int = 100, min_chunk_size: int = 100):
        """
        Initialize text chunker.
        
        Args:
            max_chunk_size (int): Maximum size of each chunk
            overlap_size (int): Overlap between chunks
            min_chunk_size (int): Minimum size of valid chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            logger.warning("tiktoken not available, using approximate token counting")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: approximate token count
            return len(text.split()) * 1.3
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """
        Chunk text by sentences with overlap.
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of text chunks
        """
        try:
            sentences = sent_tokenize(text)
        except Exception as e:
            logger.warning(f"Sentence tokenization failed: {e}, using simple splitting")
            sentences = re.split(r'[.!?]+', text)
            
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed max size, finalize current chunk
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_sentences = []
                overlap_length = 0
                
                # Add sentences from the end for overlap
                for i in range(len(current_chunk) - 1, -1, -1):
                    sent_len = len(current_chunk[i])
                    if overlap_length + sent_len <= self.overlap_size:
                        overlap_sentences.insert(0, current_chunk[i])
                        overlap_length += sent_len
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunk text by paragraphs with size limits.
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of text chunks
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            para_length = len(paragraph)
            
            # If paragraph alone exceeds max size, split it further
            if para_length > self.max_chunk_size:
                # Finalize current chunk first
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph by sentences
                para_chunks = self.chunk_by_sentences(paragraph)
                chunks.extend(para_chunks)
                continue
            
            # If adding this paragraph would exceed max size, finalize current chunk
            if current_length + para_length > self.max_chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)
                
                # Start new chunk with potential overlap
                if self.overlap_size > 0 and current_chunk:
                    # Keep last paragraph for overlap if it fits
                    last_para = current_chunk[-1]
                    if len(last_para) <= self.overlap_size:
                        current_chunk = [last_para]
                        current_length = len(last_para)
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(paragraph)
            current_length += para_length + 2  # +2 for \n\n
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        return chunks
    
    def smart_chunk(self, text: str) -> List[str]:
        """
        Intelligent chunking that tries multiple strategies.
        
        Args:
            text (str): Input text
            
        Returns:
            List[str]: List of optimally chunked text
        """
        # Clean the text first
        text = self.clean_text(text)
        
        if len(text) <= self.max_chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []
        
        # Try paragraph-based chunking first
        chunks = self.chunk_by_paragraphs(text)
        
        # If chunks are still too large, use sentence-based chunking
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.max_chunk_size:
                sentence_chunks = self.chunk_by_sentences(chunk)
                final_chunks.extend(sentence_chunks)
            else:
                final_chunks.append(chunk)
        
        # Filter out chunks that are too small
        valid_chunks = [chunk for chunk in final_chunks if len(chunk) >= self.min_chunk_size]
        
        logger.info(f"Smart chunking created {len(valid_chunks)} valid chunks from {len(text)} characters")
        
        return valid_chunks
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text (str): Input text
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page markers
        text = re.sub(r'\n--- Page \d+ ---\n', '\n\n', text)
        
        # Fix common PDF extraction issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase and uppercase
        text = re.sub(r'(\.)([A-Z])', r'\1 \2', text)    # Add space after period if missing
        
        # Remove excessive newlines but preserve paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def get_chunk_stats(self, chunks: List[str]) -> dict:
        """
        Get statistics about chunks.
        
        Args:
            chunks (List[str]): List of text chunks
            
        Returns:
            dict: Statistics about the chunks
        """
        if not chunks:
            return {"count": 0, "avg_length": 0, "min_length": 0, "max_length": 0}
        
        lengths = [len(chunk) for chunk in chunks]
        
        return {
            "count": len(chunks),
            "avg_length": sum(lengths) // len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_length": sum(lengths)
        }