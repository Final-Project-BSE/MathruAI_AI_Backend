"""Flask application factory and configuration."""
import logging
import os
import traceback

from flask import Flask, request
from flask_cors import CORS

from chatbot.core.rag_system import VectorRAGSystem
from chatbot.utils.response_utils import create_error_response
from chatbot.config.settings import RAGConfig, APIConfig
from chatbot.utils.auth_utils import AuthUtils

# Get chatbot directory path
CHATBOT_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)


def create_app():
    """ Create and configure Flask application. """
    app = Flask(__name__)

    # Configure CORS
    CORS(app, origins=["*"])

    # Application configuration
    app.config["ALLOWED_EXTENSIONS"] = {"pdf"}
    app.config["UPLOAD_FOLDER"] = RAGConfig.UPLOAD_DIR
    app.config["MAX_FILE_SIZE"] = 16 * 1024 * 1024
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    app.config["DEBUG"] = APIConfig.DEBUG

    # Create required directories
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Configure logging once
    setup_logging()

    logger.info("Chatbot directory: %s", CHATBOT_DIR)
    logger.info("Upload folder: %s", app.config["UPLOAD_FOLDER"])

    # Initialize auth utils
    app.auth_utils = AuthUtils(APIConfig.JWT_SECRET_KEY)

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
    """Configure application logging to console only."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers during reload/dev restarts
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)


def initialize_rag_system():
    """Initialize RAG system with error handling."""
    try:
        logger.info("Initializing RAG system...")
        rag_system = VectorRAGSystem(
            embedding_model=RAGConfig.EMBEDDING_MODEL,
            chunk_size=RAGConfig.CHUNK_SIZE,
            chunk_overlap=RAGConfig.CHUNK_OVERLAP,
        )
        logger.info("RAG system initialized successfully")

        # Log initial stats
        stats = rag_system.get_system_stats()
        logger.info("Initial KB stats: %s", stats)

        return rag_system

    except Exception as exc:
        logger.error("Error initializing RAG system: %s", str(exc))
        logger.error("Traceback: %s", traceback.format_exc())
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
        logger.error("Internal server error: %s", str(error))
        logger.error("Traceback: %s", traceback.format_exc())
        return create_error_response("Internal server error", 500)


def setup_request_logging(app):
    """Setup request logging middleware."""

    @app.before_request
    def log_request():
        """Log incoming requests."""
        logger.info("%s %s - %s", request.method, request.path, request.remote_addr)