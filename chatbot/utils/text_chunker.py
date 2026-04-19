"""Advanced text chunking utilities with multiple strategies."""
import logging
import re
from typing import List

import tiktoken
from nltk.tokenize import sent_tokenize

from chatbot.utils.nltk_utils import ensure_punkt

logger = logging.getLogger(__name__)


class TextChunker:
    def __init__(self, max_chunk_size: int = 800, overlap_size: int = 100, min_chunk_size: int = 100):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        ensure_punkt()
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            logger.warning("tiktoken not available, using approximate token counting")

    def count_tokens(self, text: str) -> int:
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return int(len(text.split()) * 1.3)

    def chunk_by_sentences(self, text: str) -> List[str]:
        try:
            sentences = sent_tokenize(text)
        except Exception as exc:
            logger.warning("Sentence tokenization failed: %s, using simple splitting", exc)
            sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)

                overlap_sentences: List[str] = []
                overlap_length = 0
                for existing in reversed(current_chunk):
                    existing_len = len(existing)
                    if overlap_length + existing_len <= self.overlap_size:
                        overlap_sentences.insert(0, existing)
                        overlap_length += existing_len
                    else:
                        break
                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks

    def chunk_by_paragraphs(self, text: str) -> List[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for paragraph in paragraphs:
            para_length = len(paragraph)
            if para_length > self.max_chunk_size:
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_length = 0
                chunks.extend(self.chunk_by_sentences(paragraph))
                continue

            if current_length + para_length > self.max_chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)

                if self.overlap_size > 0 and current_chunk and len(current_chunk[-1]) <= self.overlap_size:
                    current_chunk = [current_chunk[-1]]
                    current_length = len(current_chunk[-1])
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(paragraph)
            current_length += para_length + 2

        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks

    def smart_chunk(self, text: str) -> List[str]:
        text = self.clean_text(text)
        if len(text) <= self.max_chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []

        chunks = self.chunk_by_paragraphs(text)
        final_chunks: List[str] = []
        for chunk in chunks:
            if len(chunk) > self.max_chunk_size:
                final_chunks.extend(self.chunk_by_sentences(chunk))
            else:
                final_chunks.append(chunk)

        valid_chunks = [chunk for chunk in final_chunks if len(chunk) >= self.min_chunk_size]
        logger.info("Smart chunking created %s valid chunks from %s characters", len(valid_chunks), len(text))
        return valid_chunks

    def clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n--- Page \d+ ---\n", "\n\n", text)
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        text = re.sub(r"(\.)([A-Z])", r"\1 \2", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_chunk_stats(self, chunks: List[str]) -> dict:
        if not chunks:
            return {"count": 0, "avg_length": 0, "min_length": 0, "max_length": 0}
        lengths = [len(chunk) for chunk in chunks]
        return {
            "count": len(chunks),
            "avg_length": sum(lengths) // len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_length": sum(lengths),
        }
