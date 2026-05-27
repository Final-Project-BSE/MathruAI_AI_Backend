"""Shared NLTK bootstrap helpers."""
import logging

import nltk

logger = logging.getLogger(__name__)
_PUNKT_READY = False


def ensure_punkt() -> None:
    global _PUNKT_READY

    if _PUNKT_READY:
        return

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        logger.info("Downloading NLTK punkt tokenizer")
        nltk.download("punkt", quiet=True)

    _PUNKT_READY = True
