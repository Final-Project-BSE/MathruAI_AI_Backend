"""Token management utilities for context truncation and token counting."""
import logging
from typing import List

import tiktoken
from nltk.tokenize import sent_tokenize

from chatbot.utils.nltk_utils import ensure_punkt

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token counting and context truncation."""

    def __init__(self, model_name: str = "llama-3.1-8b-instant", max_context_tokens: int = 3000):
        self.model_name = model_name
        self.max_context_tokens = max_context_tokens
        ensure_punkt()
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as exc:
            self.tokenizer = None
            logger.warning("tiktoken not available, using approximate token counting: %s", exc)

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return max(1, len(text) // 4)

    def truncate_context(self, context_chunks: List[str], query: str, system_prompt: str) -> str:
        if not context_chunks:
            return ""

        system_tokens = self.count_tokens(system_prompt)
        query_tokens = self.count_tokens(query)
        response_buffer = 500
        available_tokens = self.max_context_tokens - system_tokens - query_tokens - response_buffer

        if available_tokens <= 0:
            logger.warning("Query too long, using minimal context")
            return context_chunks[0][:500]

        truncated_context_parts: List[str] = []
        current_tokens = 0

        for chunk in context_chunks:
            chunk_tokens = self.count_tokens(chunk)
            if current_tokens + chunk_tokens <= available_tokens:
                truncated_context_parts.append(chunk)
                current_tokens += chunk_tokens
                continue

            remaining_tokens = available_tokens - current_tokens
            if remaining_tokens > 50:
                chars_to_fit = remaining_tokens * 4
                partial_chunk = chunk[:chars_to_fit]
                try:
                    sentences = sent_tokenize(partial_chunk)
                    if len(sentences) > 1:
                        partial_chunk = " ".join(sentences[:-1])
                except Exception:
                    pass
                if partial_chunk.strip():
                    truncated_context_parts.append(partial_chunk)
            break

        truncated_context = "\n\n".join(truncated_context_parts)
        logger.info(
            "Context truncated to %s tokens (limit: %s)",
            self.count_tokens(truncated_context),
            available_tokens,
        )
        return truncated_context

    def estimate_response_tokens(self, context: str, query: str, system_prompt: str) -> int:
        return self.count_tokens(system_prompt) + self.count_tokens(context) + self.count_tokens(query)
