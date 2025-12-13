"""
Flask application factory and configuration.
"""
from flask import Flask, request
from flask_cors import CORS
import os
import logging
from datetime import datetime
import traceback

from chatbot.core.rag_system import VectorRAGSystem
from chatbot.utils.response_utils import create_error_response
from chatbot.config.settings import RAGConfig

# Get chatbot directory path
CHATBOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging to use chatbot/logs directory
log_file = os.path.join(CHATBOT_DIR, 'logs', 'app.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Chatbot directory: {CHATBOT_DIR}")
logger.info(f"Log file: {log_file}")

def create_app():
    """
    Create and configure Flask application.
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, origins=['*'])  # Configure more specifically in production
    
    # Application configuration
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
    app.config['UPLOAD_FOLDER'] = RAGConfig.UPLOAD_DIR  # chatbot/uploads
    app.config['MAX_FILE_SIZE'] = 16 * 1024 * 1024  # 16MB
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Create upload directory if it doesn't exist (already done by RAGConfig)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Configure logging
    setup_logging()
    
    # Initialize RAG system
    app.rag_system = initialize_rag_system()
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register request logging
    setup_request_logging(app)
    
    return app


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )


def initialize_rag_system():
    """
    Initialize RAG system with error handling.
    
    Returns:
        VectorRAGSystem or None: Initialized RAG system or None if failed
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Initializing RAG system...")
        rag_system = VectorRAGSystem(
            embedding_model='all-MiniLM-L6-v2',
            chunk_size=1000,
            chunk_overlap=200
        )
        logger.info("RAG system initialized successfully")
        
        # Log initial stats
        stats = rag_system.get_system_stats()
        logger.info(f"Initial KB stats: {stats}")
        
        return rag_system
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def register_blueprints(app):
    """Register API blueprints."""
    from chatbot.api.chat_api import chat_bp
    from chatbot.api.upload_api import upload_bp
    
    app.register_blueprint(chat_bp)
    app.register_blueprint(upload_bp)


def register_error_handlers(app):
    """Register global error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        return create_error_response("Endpoint not found", 404)
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return create_error_response("Method not allowed", 405)
    
    @app.errorhandler(413)
    def too_large(error):
        return create_error_response("File too large. Maximum size is 16MB.", 413)
    
    @app.errorhandler(500)
    def internal_error(error):
        logger = logging.getLogger(__name__)
        logger.error(f"Internal server error: {str(error)}")
        return create_error_response("Internal server error", 500)


def setup_request_logging(app):
    """Setup request logging middleware."""
    logger = logging.getLogger(__name__)
    
    @app.before_request
    def log_request():
        """Log incoming requests."""
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")


def allowed_file(filename: str, app) -> bool:
    """Check if file extension is allowed."""
    return ('.' in filename and 
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])