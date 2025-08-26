import os
import logging
from flask import Flask
from flask_cors import CORS
from risk_predition_model.config import config

# Global predictor instance
predictor = None
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern for creating Flask app"""
    global predictor
    
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(config[os.environ.get('FLASK_ENV', 'default')])
    
    # Enable CORS for all routes
    CORS(app)
    
    # Initialize predictor
    try:
        # Import here to avoid circular imports
        from risk_predition_model.model.predict import RiskAdvicePredictor
        
        # Use the correct model path
        model_path = 'risk_predition_model/model/maternal_risk_advice_model.pkl'
        if os.path.exists(model_path):
            predictor = RiskAdvicePredictor(model_path)
            logger.info("Multi-output model loaded successfully")
        else:
            logger.error(f"Model file not found at: {model_path}")
            predictor = None
    except ImportError as e:
        logger.error(f"Failed to import RiskAdvicePredictor: {str(e)}")
        predictor = None
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        predictor = None
    
    # Register blueprints only if they can be imported
    try:
        from risk_predition_model.api.health import health_bp
        from risk_predition_model.api.prediction import prediction_bp
        from risk_predition_model.api.model_info import model_info_bp
        
        app.register_blueprint(health_bp)
        app.register_blueprint(prediction_bp)
        app.register_blueprint(model_info_bp)
        logger.info("Blueprints registered successfully")
    except ImportError as e:
        logger.error(f"Failed to import blueprints: {str(e)}")
    
    return app

def get_predictor():
    """Get the global predictor instance"""
    return predictor