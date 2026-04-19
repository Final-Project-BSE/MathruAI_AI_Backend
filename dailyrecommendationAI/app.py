from flask import Flask
from flask_cors import CORS
import logging

from dailyrecommendationAI.config import Config
from dailyrecommendationAI.api_routes import api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={
            r"/*": {
                "origins": Config.CORS_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "expose_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
            }
        },
    )

    app.register_blueprint(api)

    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'error': 'File too large. Maximum allowed size is 16MB'}, 413

    @app.errorhandler(500)
    def internal_error(error):
        logger.error('Internal error: %s', error)
        return {'error': 'Internal server error'}, 500

    logger.info('=' * 50)
    logger.info('Pregnancy RAG System API Starting')
    logger.info('JWT Verification Mode: %s', Config.JWT_VERIFY_MODE)
    logger.info('Spring Boot Auth URL: %s', Config.SPRING_BOOT_AUTH_URL)
    logger.info('Database: %s/%s', Config.DB_HOST, Config.DB_NAME)
    logger.info('CORS Origins: %s', Config.CORS_ORIGINS)
    logger.info('=' * 50)

    return app


if __name__ == '__main__':
    app = create_app()
    logger.info('Starting server on %s:%s', Config.HOST, Config.PORT)
    app.run(
        debug=Config.DEBUG,
        port=Config.PORT,
        host=Config.HOST,
    )
