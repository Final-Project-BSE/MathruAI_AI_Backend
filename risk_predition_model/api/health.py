from flask import Blueprint, jsonify
from risk_predition_model.app import get_predictor

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    predictor = get_predictor()
    
    return jsonify({
        'status': 'healthy',
        'message': 'Maternal Risk & Advice Prediction API is running',
        'model_loaded': predictor is not None,
        'api_version': '2.0',
        'endpoints': {
            '/predict': 'POST - Predict risk level and health advice',
            '/predict-risk-only': 'POST - Predict only risk level (backward compatibility)',
            '/model-info': 'GET - Get model information',
            '/batch-predict': 'POST - Batch predictions',
            '/health': 'GET - Health check'
        }
    })

@health_bp.route('/health', methods=['GET'])
def health():
    """Alternative health check endpoint"""
    return health_check()