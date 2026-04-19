"""Utility functions for API response formatting."""
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import logging

from flask import jsonify

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now().isoformat()


def create_success_response(
    data: Dict[str, Any],
    message: str = "Success",
    status_code: int = 200,
) -> Tuple:
    response_data = {
        "status": "success",
        "message": message,
        "timestamp": _timestamp(),
        **data,
    }
    return jsonify(response_data), status_code


def create_error_response(
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> Tuple:
    response_data = {
        "status": "error",
        "message": message,
        "timestamp": _timestamp(),
    }
    if details:
        response_data["details"] = details
    return jsonify(response_data), status_code


def validate_rag_system(rag_system) -> Tuple[bool, Optional[str]]:
    if not rag_system:
        return False, "RAG system not initialized"
    return True, None


def log_api_request(endpoint: str, method: str, remote_addr: str, data: Optional[Dict] = None):
    logger.info("%s %s - %s", method, endpoint, remote_addr)
    if data and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Request data: %s...", str(data)[:200])


def validate_json_request(data: Dict, required_fields: list) -> Optional[str]:
    if not data:
        return "Request body must be JSON"

    for field in required_fields:
        if field not in data:
            return f"'{field}' field is required"
        if isinstance(data[field], str) and not data[field].strip():
            return f"'{field}' cannot be empty"

    return None


def validate_pagination_params(page: int = 1, per_page: int = 10, max_per_page: int = 100) -> Optional[str]:
    if page < 1:
        return "Page number must be greater than 0"
    if per_page < 1:
        return "Items per page must be greater than 0"
    if per_page > max_per_page:
        return f"Items per page cannot exceed {max_per_page}"
    return None


def validate_search_params(top_k: int, similarity_threshold: float) -> Optional[str]:
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        return "top_k must be an integer between 1 and 20"
    if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1:
        return "similarity_threshold must be a number between 0 and 1"
    return None
