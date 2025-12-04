import os
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    VECTOR_DB_PATH = 'vector_db'
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    # JWT Authentication
    JWT_SECRET_BASE64 = os.getenv('JWT_SECRET', 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd')
    
    # Decode the base64 secret to match Spring Boot's configuration
    try:
        JWT_SECRET = base64.b64decode(JWT_SECRET_BASE64)
    except Exception:
        JWT_SECRET = JWT_SECRET_BASE64  # Fallback if not base64
    
    # Spring Boot authentication service URL
    SPRING_BOOT_AUTH_URL = os.getenv('SPRING_BOOT_AUTH_URL', 'http://localhost:8080/api/auth')
    
    JWT_VERIFY_MODE = os.getenv('JWT_VERIFY_MODE', 'local')
    
    # JWT expiration
    JWT_EXPIRATION_MS = int(os.getenv('JWT_EXPIRATION_MS', 604800000))  # 7 days default
    
    # API settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '20000624')
    DB_NAME = os.getenv('DB_NAME', 'MathruAi_Database')
    
    # Vector settings
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    EMBEDDING_DIMENSION = 384
    
    # Text processing settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    
    # AI model settings
    GROQ_MODEL = "llama-3.1-8b-instant"
    MAX_TOKENS = 200
    TEMPERATURE = 0.7
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')