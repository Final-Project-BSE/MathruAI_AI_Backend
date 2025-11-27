"""
Main Flask Application for Pregnancy Risk Prediction with JWT Auth
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # CORS - Allow credentials for JWT
    CORS(app, 
         origins=["http://localhost:3000", "http://localhost:8080"],  # Add your frontend URLs
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)
    
    logger.info("Initializing database...")
    try:
        from model.database import get_db_manager
        db_manager = get_db_manager()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    logger.info("Loading prediction model...")
    try:
        from model.predict import RiskAdvicePredictor
        predictor = RiskAdvicePredictor()
        logger.info("✓ Prediction model loaded")
    except Exception as e:
        logger.error(f"Model loading error: {e}")
    
    # Register blueprints
    logger.info("Registering blueprints...")
    try:
        from api.prediction import prediction_bp
        app.register_blueprint(prediction_bp, url_prefix='/api/predict')
        logger.info("✓ Prediction blueprint registered")
    except Exception as e:
        logger.error(f"Blueprint registration error: {e}")
    
    # Health check (No authentication required)
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Pregnancy Risk Prediction API",
            "version": "1.0",
            "auth": "JWT enabled"
        }), 200
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            "message": "Pregnancy Risk Prediction API",
            "version": "1.0",
            "authentication": "JWT Required (Bearer token)",
            "endpoints": {
                "POST /api/predict/store": "Store new prediction (AUTH REQUIRED)",
                "GET /api/predict/get/<id>": "Get specific prediction (AUTH REQUIRED)",
                "GET /api/predict/latest": "Get latest prediction (AUTH REQUIRED)",
                "GET /api/predict/history": "Get all predictions (AUTH REQUIRED)",
                "PUT /api/predict/update/<id>": "Update prediction (AUTH REQUIRED)",
                "DELETE /api/predict/delete/<id>": "Delete prediction (AUTH REQUIRED)",
                "GET /health": "Health check (No auth)"
            },
            "auth_header": "Authorization: Bearer <jwt_token>"
        }), 200
    
    # Error handlers
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "status": "error",
            "error": "Unauthorized",
            "message": "Valid authentication token required"
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You don't have permission to access this resource"
        }), 403
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)