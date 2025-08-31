"""
Configuration settings for the RAG system.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    """Database configuration settings."""
    
    HOST: str = os.getenv('MYSQL_HOST', 'localhost')
    USER: str = os.getenv('MYSQL_USER', 'root')
    PASSWORD: str = os.getenv('MYSQL_PASSWORD', '20000624')
    DATABASE: str = os.getenv('MYSQL_DATABASE', 'rag_system')
    PORT: int = int(os.getenv('MYSQL_PORT', '3306'))


class RAGConfig:
    """RAG system configuration settings."""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    print(".....................................................................................................................................")
    print(GROQ_API_KEY)
    
    # Model settings
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    LLM_MODEL: str = os.getenv('LLM_MODEL', 'llama3-8b-8192')
    
    # Chunking settings
    CHUNK_SIZE: int = int(os.getenv('CHUNK_SIZE', '800'))
    CHUNK_OVERLAP: int = int(os.getenv('CHUNK_OVERLAP', '100'))
    MIN_CHUNK_SIZE: int = int(os.getenv('MIN_CHUNK_SIZE', '50'))
    
    # Token management
    MAX_CONTEXT_TOKENS: int = int(os.getenv('MAX_CONTEXT_TOKENS', '3000'))
    MAX_RESPONSE_TOKENS: int = int(os.getenv('MAX_RESPONSE_TOKENS', '500'))
    
    # Search settings
    DEFAULT_TOP_K: int = int(os.getenv('DEFAULT_TOP_K', '5'))
    SIMILARITY_THRESHOLD: float = float(os.getenv('SIMILARITY_THRESHOLD', '0.1'))
    
    # File paths
    DATA_DIR: str = os.getenv('DATA_DIR', 'data')
    CACHE_DIR: str = os.path.join(DATA_DIR, 'cache')
    RAW_DATA_DIR: str = os.path.join(DATA_DIR, 'raw')
    PROCESSED_DATA_DIR: str = os.path.join(DATA_DIR, 'processed')
    
    # Knowledge base files
    KB_FILE: str = os.path.join(CACHE_DIR, 'knowledge_base.pkl')
    FAISS_INDEX_FILE: str = os.path.join(CACHE_DIR, 'faiss_index.bin')
    HASH_FILE: str = os.path.join(CACHE_DIR, 'kb_hash.txt')
    DEFAULT_KB_FILE: str = os.path.join(RAW_DATA_DIR, 'pregnancy_guide.txt')


class APIConfig:
    """API configuration settings."""
    
    HOST: str = os.getenv('API_HOST', '0.0.0.0')
    PORT: int = int(os.getenv('API_PORT', '8000'))
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    RELOAD: bool = os.getenv('RELOAD', 'True').lower() == 'true'


def validate_config():
    """Validate that required configuration is present."""
    if not RAGConfig.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is required but not found in environment variables")
    
    # Create directories if they don't exist
    os.makedirs(RAGConfig.DATA_DIR, exist_ok=True)
    os.makedirs(RAGConfig.CACHE_DIR, exist_ok=True)
    os.makedirs(RAGConfig.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(RAGConfig.PROCESSED_DATA_DIR, exist_ok=True)


# Validate configuration on import
validate_config()