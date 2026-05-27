"""Configuration settings"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

CHATBOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise ValueError(f"{name} is required but not found in environment variables")
    return value


def _get_int_env(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return int(default)


def _get_float_env(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


class DatabaseConfig:
    """Database configuration settings."""

    HOST: str = _get_env('MYSQL_HOST', 'localhost')
    USER: str = _get_env('MYSQL_USER', 'root')
    PASSWORD: str = _get_env('MYSQL_PASSWORD', '')
    DATABASE: str = _get_env('MYSQL_DATABASE', 'MathruAi_Database')
    PORT: int = _get_int_env('MYSQL_PORT', '3306')


class RAGConfig:
    """RAG system configuration settings."""

    GROQ_API_KEY: str = _get_env('GROQ_API_KEY', '')

    EMBEDDING_MODEL: str = _get_env('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    LLM_MODEL: str = _get_env('LLM_MODEL', 'llama-3.1-8b-instant')

    CHUNK_SIZE: int = _get_int_env('CHUNK_SIZE', '800')
    CHUNK_OVERLAP: int = _get_int_env('CHUNK_OVERLAP', '100')
    MIN_CHUNK_SIZE: int = _get_int_env('MIN_CHUNK_SIZE', '50')

    MAX_CONTEXT_TOKENS: int = _get_int_env('MAX_CONTEXT_TOKENS', '3000')
    MAX_RESPONSE_TOKENS: int = _get_int_env('MAX_RESPONSE_TOKENS', '500')

    DEFAULT_TOP_K: int = _get_int_env('DEFAULT_TOP_K', '5')
    SIMILARITY_THRESHOLD: float = _get_float_env('SIMILARITY_THRESHOLD', '0.1')

    BASE_DIR: str = CHATBOT_DIR
    DATA_DIR: str = os.path.join(CHATBOT_DIR, 'data')
    CACHE_DIR: str = os.path.join(CHATBOT_DIR, 'data', 'cache')
    RAW_DATA_DIR: str = os.path.join(CHATBOT_DIR, 'data', 'raw')
    PROCESSED_DATA_DIR: str = os.path.join(CHATBOT_DIR, 'data', 'processed')
    UPLOAD_DIR: str = os.path.join(CHATBOT_DIR, 'uploads')

    KB_FILE: str = os.path.join(CACHE_DIR, 'knowledge_base.pkl')
    FAISS_INDEX_FILE: str = os.path.join(CACHE_DIR, 'faiss_index.bin')
    HASH_FILE: str = os.path.join(CACHE_DIR, 'kb_hash.txt')
    DEFAULT_KB_FILE: str = os.path.join(RAW_DATA_DIR, 'pregnancy_guide.txt')


class APIConfig:
    """API configuration settings."""

    HOST: str = _get_env('API_HOST', '0.0.0.0')
    PORT: int = _get_int_env('API_PORT', '8000')
    DEBUG: bool = _get_env('DEBUG', 'False').lower() == 'true'
    RELOAD: bool = _get_env('RELOAD', 'True').lower() == 'true'
    JWT_SECRET_KEY: str = _get_env('JWT_SECRET_KEY', '')
    SPRING_BOOT_URL: str = _get_env('SPRING_BOOT_URL', 'http://localhost:8080')


def validate_config():
    """Validate required configuration and create project directories."""
    if not RAGConfig.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is required but not found in environment variables")

    directories = [
        RAGConfig.DATA_DIR,
        RAGConfig.CACHE_DIR,
        RAGConfig.RAW_DATA_DIR,
        RAGConfig.PROCESSED_DATA_DIR,
        RAGConfig.UPLOAD_DIR,
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)