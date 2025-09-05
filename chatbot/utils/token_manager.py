"""
Token management utilities for context truncation and token counting.
"""
import tiktoken
import nltk
from nltk.tokenize import sent_tokenize
from typing import List
import logging

logger = logging.getLogger(__name__)

# Download required NLTK data (only runs one time)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')


class TokenManager:
    """Manages token counting and context truncation."""
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant", max_context_tokens: int = 3000):
        """
        Initialize token manager.
        
        Args:
            model_name (str): Name of the language model
            max_context_tokens (int): Maximum tokens for context
        """
        self.model_name = model_name
        self.max_context_tokens = max_context_tokens
        
        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            self.tokenizer = None
            logger.warning(f"tiktoken not available, using approximate token counting: {e}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text accurately.
        
        Args:
            text (str): Input text
            
        Returns:
            int: Number of tokens
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: approximate token count (1 token ≈ 4 characters)
            return len(text) // 4
    
    def truncate_context(self, context_chunks: List[str], query: str, system_prompt: str) -> str:
        """
        Truncate context to fit within token limits.
        
        Args:
            context_chunks (List[str]): List of context chunks
            query (str): User query
            system_prompt (str): System prompt
            
        Returns:
            str: Truncated context that fits within limits
        """
        if not context_chunks:
            return ""
        
        # Reserve tokens for system prompt, query, and response
        system_tokens = self.count_tokens(system_prompt)
        query_tokens = self.count_tokens(query)
        response_buffer = 500  # Reserve for response
        
        available_tokens = self.max_context_tokens - system_tokens - query_tokens - response_buffer
        
        if available_tokens <= 0:
            logger.warning("Query too long, using minimal context")
            return context_chunks[0][:500]  # Use first 500 chars as fallback
        
        # Build context within token limit
        truncated_context = ""
        current_tokens = 0
        
        for chunk in context_chunks:
            chunk_tokens = self.count_tokens(chunk)
            
            if current_tokens + chunk_tokens <= available_tokens:
                if truncated_context:
                    truncated_context += "\n\n"
                truncated_context += chunk
                current_tokens += chunk_tokens
            else:
                # Try to fit partial chunk
                remaining_tokens = available_tokens - current_tokens
                if remaining_tokens > 50:  # Only if we have reasonable space
                    # Estimate characters we can fit
                    chars_to_fit = remaining_tokens * 4  # Approximate
                    partial_chunk = chunk[:chars_to_fit]
                    
                    # Try to end at a sentence boundary
                    try:
                        sentences = sent_tokenize(partial_chunk)
                        if len(sentences) > 1:
                            partial_chunk = ' '.join(sentences[:-1])
                    except Exception:
                        # If sentence tokenization fails, use original partial chunk
                        pass
                    
                    if truncated_context:
                        truncated_context += "\n\n"
                    truncated_context += partial_chunk
                break
        
        final_tokens = self.count_tokens(truncated_context)
        logger.info(f"Context truncated to {final_tokens} tokens (limit: {available_tokens})")
        
        return truncated_context
    
    def estimate_response_tokens(self, context: str, query: str, system_prompt: str) -> int:
        """
        Estimate total tokens for a complete request.
        
        Args:
            context (str): Context text
            query (str): User query
            system_prompt (str): System prompt
            
        Returns:
            int: Estimated total tokens
        """
        return (
            self.count_tokens(system_prompt) +
            self.count_tokens(context) +
            self.count_tokens(query)
        )