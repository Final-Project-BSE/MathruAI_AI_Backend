import os
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: str = 'False') -> bool:
    return os.getenv(name, default).strip().lower() == 'true'


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Config:
    BASE_DIR = Path(__file__).resolve().parent

    # Flask / API
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')
    DEBUG = _get_bool('DEBUG', 'True')
    RELOAD = _get_bool('RELOAD', 'False')
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = _get_int('API_PORT', 5000)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Paths
    UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
    VECTOR_DB_PATH = str(BASE_DIR / 'vector_db')

    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_FILE_SIZE = MAX_CONTENT_LENGTH

    # JWT Auth
    JWT_SECRET_BASE64 = os.getenv('JWT_SECRET_KEY', os.getenv('JWT_SECRET', ''))
    try:
        JWT_SECRET = base64.b64decode(JWT_SECRET_BASE64) if JWT_SECRET_BASE64 else b''
    except Exception:
        JWT_SECRET = JWT_SECRET_BASE64.encode() if JWT_SECRET_BASE64 else b''

    SPRING_BOOT_AUTH_URL = os.getenv('SPRING_BOOT_AUTH_URL', 'http://localhost:8080/api/auth')
    JWT_VERIFY_MODE = os.getenv('JWT_VERIFY_MODE', 'local')
    JWT_EXPIRATION_MS = _get_int('JWT_EXPIRATION_MS', 604800000)

    # AI settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('LLM_MODEL', 'llama-3.1-8b-instant')
    MAX_TOKENS = _get_int('MAX_RESPONSE_TOKENS', 200)
    TEMPERATURE = _get_float('TEMPERATURE', 0.7)

    # Embedding / retrieval
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    EMBEDDING_DIMENSION = 384
    CHUNK_SIZE = _get_int('CHUNK_SIZE', 500)
    CHUNK_OVERLAP = _get_int('CHUNK_OVERLAP', 50)
    MIN_CHUNK_SIZE = _get_int('MIN_CHUNK_SIZE', 100)
    MAX_CONTEXT_TOKENS = _get_int('MAX_CONTEXT_TOKENS', 1200)
    DEFAULT_TOP_K = _get_int('DEFAULT_TOP_K', 5)
    SIMILARITY_THRESHOLD = _get_float('SIMILARITY_THRESHOLD', 0.3)

    # Database settings
    DB_HOST = os.getenv('MYSQL_HOST', os.getenv('DB_HOST', 'localhost'))
    DB_USER = os.getenv('MYSQL_USER', os.getenv('DB_USER', 'root'))
    DB_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', ''))
    DB_NAME = os.getenv('MYSQL_DATABASE', os.getenv('DB_NAME', 'MathruAi_Database'))
    DB_PORT = _get_int('MYSQL_PORT', 3306)

    # CORS settings
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            'CORS_ORIGINS',
            'http://localhost:3000,http://localhost:8080'
        ).split(',')
        if origin.strip()
    ]
