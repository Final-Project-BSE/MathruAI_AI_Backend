import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'secret-key-here')
    DEBUG = True
    PORT = 5000
    
    # File upload settings - THESE WERE MISSING AND CAUSING THE ERROR
    UPLOAD_FOLDER = 'uploads'
    VECTOR_DB_PATH = 'vector_db'
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    # API settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'pregnancy_rag')
    
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