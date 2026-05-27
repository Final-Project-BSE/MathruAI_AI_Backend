import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
from risk_predition_model.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

_predictor = None


def get_predictor():
    """Lazy-load and cache predictor instance."""
    global _predictor
    if _predictor is None:
        from risk_predition_model.model.predict import RiskAdvicePredictor
        _predictor = RiskAdvicePredictor()
    return _predictor


def create_app():
    """Create and configure Flask app."""
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)

    CORS(
        app,
        origins=["http://localhost:3000", "http://localhost:8080"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True
    )

    logger.info("Initializing database...")
    try:
        from risk_predition_model.model.database import get_db_manager
        get_db_manager()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    logger.info("Loading prediction model...")
    try:
        get_predictor()
        logger.info("Prediction model loaded")
    except Exception as e:
        logger.error(f"Model loading error: {e}")

    logger.info("Registering blueprints...")
    try:
        from risk_predition_model.api.prediction import prediction_bp
        from risk_predition_model.api.health import health_bp
        from risk_predition_model.api.model_info import model_info_bp
        from risk_predition_model.api.health_monitoring import health_monitoring_bp

        app.register_blueprint(prediction_bp, url_prefix="/api/predict")
        app.register_blueprint(health_bp, url_prefix="/maternal")
        app.register_blueprint(model_info_bp, url_prefix="/maternal")
        app.register_blueprint(health_monitoring_bp, url_prefix="/api/monitoring")

        logger.info("✓ Blueprints registered")
    except Exception as e:
        logger.error(f"Blueprint registration error: {e}")

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Pregnancy Risk Prediction API",
            "version": "1.0",
            "auth": "JWT enabled"
        }), 200

    @app.route("/", methods=["GET"])
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
                "GET /api/monitoring/midwife/<midwife_id>/patient/<patient_id>/latest": "Get latest patient prediction for a managed patient (AUTH REQUIRED)",
                "PUT /api/monitoring/midwife/<midwife_id>/patient/<patient_id>/prediction/<prediction_id>": "Update an existing patient prediction by midwife (AUTH REQUIRED)",
                "GET /health": "Health check (No auth)"
            },
            "auth_header": "Authorization: Bearer <jwt_token>"
        }), 200

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


if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=os.environ.get("DEBUG", "False").lower() == "true",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000))
    )