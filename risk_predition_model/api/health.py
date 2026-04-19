"""
Health check endpoints for Maternal Risk Prediction API
"""
import logging
from flask import Blueprint, jsonify

from risk_predition_model.app import get_predictor

health_bp = Blueprint("health", __name__)
logger = logging.getLogger(__name__)


@health_bp.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    model_loaded = False
    try:
        get_predictor()
        model_loaded = True
    except Exception as e:
        logger.warning(f"Predictor not available: {e}")

    return jsonify({
        "status": "healthy",
        "message": "Maternal Risk & Advice Prediction API is running",
        "model_loaded": model_loaded,
        "api_version": "2.0",
        "endpoints": {
            "POST /api/predict/store": "Store new prediction",
            "GET /api/predict/latest": "Get latest prediction",
            "GET /api/predict/history": "Get prediction history",
            "GET /api/predict/user/<id>/latest": "Get user latest prediction",
            "GET /maternal/": "Health check",
            "GET /maternal/health": "Health check"
        }
    })


@health_bp.route("/health", methods=["GET"])
def health():
    """Alternative health check endpoint"""
    return health_check()