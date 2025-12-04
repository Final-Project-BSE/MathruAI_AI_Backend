from flask import Flask
from flask_cors import CORS
import logging
from dailyrecommendationAI.config import Config
from dailyrecommendationAI.api_routes import api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for Spring Boot frontend
    CORS(app, resources={
        r"/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Register blueprints
    app.register_blueprint(api)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return {'error': 'Internal server error'}, 500
    
    # Log startup info
    logger.info("="*50)
    logger.info("Pregnancy RAG System API Starting")
    logger.info(f"JWT Verification Mode: {Config.JWT_VERIFY_MODE}")
    logger.info(f"Spring Boot Auth URL: {Config.SPRING_BOOT_AUTH_URL}")
    logger.info(f"Database: {Config.DB_HOST}/{Config.DB_NAME}")
    logger.info(f"CORS Origins: {Config.CORS_ORIGINS}")
    logger.info("="*50)
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info(f"Starting server on port {Config.PORT}")
    app.run(
        debug=Config.DEBUG, 
        port=Config.PORT,
        host='0.0.0.0'  # Allow external connections
    )