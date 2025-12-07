"""
Health check endpoints for Maternal Risk Prediction API
"""
from flask import Blueprint, jsonify
import logging

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

print("✓ Health blueprint created")


@health_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Try to check if predictor can be loaded
    model_loaded = False
    try:
        from risk_predition_model.model.predict import RiskAdvicePredictor
        predictor = RiskAdvicePredictor()
        model_loaded = True
    except Exception as e:
        logger.warning(f"Predictor not available: {e}")
    
    return jsonify({
        'status': 'healthy',
        'message': 'Maternal Risk & Advice Prediction API is running',
        'model_loaded': model_loaded,
        'api_version': '2.0',
        'endpoints': {
            'POST /api/predict/store': 'Store new prediction (JWT required)',
            'GET /api/predict/latest': 'Get latest prediction (JWT required)',
            'GET /api/predict/history': 'Get prediction history (JWT required)',
            'GET /api/predict/user/<id>/latest': 'Get user latest prediction (JWT required)',
            'GET /maternal/': 'Health check',
            'GET /maternal/health': 'Health check'
        }
    })


@health_bp.route('/health', methods=['GET'])
def health():
    """Alternative health check endpoint"""
    return health_check()


@health_bp.route('/model-info', methods=['GET'])
def model_info():
    """Get model information"""
    try:
        from risk_predition_model.model.predict import RiskAdvicePredictor
        predictor = RiskAdvicePredictor()
        
        # Try to get model info if the method exists
        try:
            model_info_data = predictor.get_model_info()
            feature_importance = predictor.get_feature_importance()
            
            return jsonify({
                'status': 'success',
                'data': {
                    'model_details': model_info_data,
                    'feature_importance': feature_importance,
                    'capabilities': {
                        'risk_prediction': True,
                        'health_advice': True,
                        'multi_output': True,
                        'batch_processing': True
                    },
                    'api_version': '2.0'
                }
            })
        except AttributeError:
            # Methods don't exist, return basic info
            return jsonify({
                'status': 'success',
                'message': 'Model loaded but info methods not available',
                'model_loaded': True,
                'api_version': '2.0'
            })
        
    except Exception as e:
        logger.error(f"Model info error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Could not load model',
            'message': str(e)
        }), 500


print("✓ Health blueprint module loaded with routes")