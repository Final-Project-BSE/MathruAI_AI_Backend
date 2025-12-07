"""
Flask application initialization with user authentication integration.
"""
from flask import Flask
from flask_cors import CORS
import logging
import os

# Import all blueprints that should be available
from chatbot.api.chat_api import chat_bp
from chatbot.api.upload_api import upload_bp 

from chatbot.utils.response_utils import create_error_response
from chatbot.database.manager import DatabaseManager
from chatbot.utils.AuthUtils import AuthUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application with authentication."""
    app = Flask(__name__)
    
    # Enable CORS for your frontend
    CORS(app, origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8080"   # Spring Boot backend
    ])
    
    # Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd')
    app.config['SPRING_BOOT_URL'] = os.getenv('SPRING_BOOT_URL', 'http://localhost:8080')
    
    # MISSING CONFIGURATION FOR UPLOAD API
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_FILE_SIZE'] = 16 * 1024 * 1024  # 16MB
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize authentication
    auth_utils = AuthUtils(app.config['JWT_SECRET_KEY'])
    app.auth_utils = auth_utils
    logger.info("Authentication utils initialized")
    
    # Initialize database manager
    try:
        db_manager = DatabaseManager()
        app.db_manager = db_manager
        logger.info("Database manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")
        app.db_manager = None
    
    # Initialize your RAG system
    try:   
        class MockRAGSystem:
            def __init__(self, db_manager):
                self.db_manager = db_manager
                
            def generate_response(self, query):
                return f"Mock response for: {query}"
                
            def find_relevant_context(self, query, top_k=3, similarity_threshold=0.1):
                return ["Mock context chunk 1", "Mock context chunk 2"]
                
            def get_system_stats(self):
                return {
                    'total_chunks': 42,
                    'faiss_index_size': 42,
                    'database_connected': self.db_manager and self.db_manager.connection is not None,
                    'embedding_model': 'mock-model',
                    'embedding_dimension': 384
                }
                
            def update_knowledge_base_from_pdf(self, file_path):
                # Mock PDF processing
                logger.info(f"Mock processing PDF: {file_path}")
                return True
        
        app.rag_system = MockRAGSystem(db_manager)
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        app.rag_system = None
    
    # REGISTER ALL BLUEPRINTS
    try:
        # Chat API (this one was already working)
        app.register_blueprint(chat_bp, url_prefix='/api')
        logger.info("Registered chat blueprint at /api")
        
        # Upload API (was missing)
        app.register_blueprint(upload_bp, url_prefix='/api')
        logger.info("Registered upload blueprint at /api")
        
    except ImportError as e:
        logger.error(f"Failed to import blueprint: {e}")
        logger.error("Make sure all blueprint files exist in chatbot/api/")
    except Exception as e:
        logger.error(f"Failed to register blueprints: {e}")
    
    # Global error handler
    @app.errorhandler(Exception)
    def handle_error(error):
        logger.error(f"Unhandled error: {str(error)}")
        return create_error_response("Internal server error", 500)
    
    # Main health check endpoint
    @app.route('/api/health')
    def health_check():
        return {
            "status": "healthy",
            "service": "ai-chatbot",
            "auth_configured": hasattr(app, 'auth_utils'),
            "db_connected": app.db_manager and app.db_manager.connection is not None,
            "rag_initialized": hasattr(app, 'rag_system') and app.rag_system is not None,
            "blueprints_registered": [rule.endpoint for rule in app.url_map.iter_rules()]
        }
    
    # Test authentication endpoint (for debugging)
    @app.route('/api/test-auth')
    def test_auth():
        user = app.auth_utils.get_current_user()
        if user:
            return {"authenticated": True, "user": user}
        else:
            return {"authenticated": False}, 401
    
    # Debug endpoint to list all routes
    @app.route('/api/debug/routes')
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            })
        return {
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['rule'])
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Print registered routes for debugging
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} {list(rule.methods)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)