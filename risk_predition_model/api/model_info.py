"""
Model info endpoints for Maternal Risk Prediction API
"""
import logging
from flask import Blueprint, jsonify

from risk_predition_model.app import get_predictor

model_info_bp = Blueprint("model_info", __name__)
logger = logging.getLogger(__name__)


@model_info_bp.route("/model-info", methods=["GET"])
def model_info():
    """Get comprehensive model information"""
    try:
        predictor = get_predictor()

        model_info_data = predictor.get_model_info()
        feature_importance = predictor.get_feature_importance()

        return jsonify({
            "status": "success",
            "data": {
                "model_details": model_info_data,
                "feature_importance": feature_importance,
                "capabilities": {
                    "risk_prediction": True,
                    "health_advice": True,
                    "multi_output": True,
                    "batch_processing": True
                },
                "api_version": "2.0"
            }
        })
    except AttributeError:
        return jsonify({
            "status": "success",
            "message": "Model loaded but info methods not available",
            "model_loaded": True,
            "api_version": "2.0"
        })
    except Exception as e:
        logger.error(f"Model info error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Could not load model",
            "message": str(e)
        }), 500