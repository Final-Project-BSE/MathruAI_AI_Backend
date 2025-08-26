"""
Utility functions for API response formatting.
"""
from flask import jsonify
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def create_success_response(data: Dict[str, Any], message: str = "Success", status_code: int = 200) -> Tuple:
    """
    Create standardized success response.
    
    Args:
        data (Dict): Response data
        message (str): Success message
        status_code (int): HTTP status code
        
    Returns:
        Tuple: Flask response tuple (json, status_code)
    """
    response_data = {
        "status": "success",
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    return jsonify(response_data), status_code


def create_error_response(message: str, status_code: int = 500, details: Optional[Dict] = None) -> Tuple:
    """
    Create standardized error response.
    
    Args:
        message (str): Error message
        status_code (int): HTTP status code
        details (Dict, optional): Additional error details
        
    Returns:
        Tuple: Flask response tuple (json, status_code)
    """
    response_data = {
        "status": "error",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        response_data["details"] = details
    
    return jsonify(response_data), status_code


def validate_rag_system(rag_system) -> Tuple[bool, Optional[str]]:
    """
    Validate RAG system availability.
    
    Args:
        rag_system: RAG system instance
        
    Returns:
        Tuple: (is_valid, error_message)
    """
    if not rag_system:
        return False, "RAG system not initialized"
    return True, None


def log_api_request(endpoint: str, method: str, remote_addr: str, data: Optional[Dict] = None):
    """
    Log API request details.
    
    Args:
        endpoint (str): API endpoint
        method (str): HTTP method
        remote_addr (str): Client IP address
        data (Dict, optional): Request data (for logging)
    """
    logger.info(f"{method} {endpoint} - {remote_addr}")
    if data and logger.isEnabledFor(logging.DEBUG):
        # Only log data in debug mode for privacy
        logger.debug(f"Request data: {str(data)[:200]}...")


def validate_json_request(data: Dict, required_fields: list) -> Optional[str]:
    """
    Validate JSON request data.
    
    Args:
        data (Dict): Request JSON data
        required_fields (list): List of required field names
        
    Returns:
        Optional[str]: Error message if validation fails, None if valid
    """
    if not data:
        return "Request body must be JSON"
    
    for field in required_fields:
        if field not in data:
            return f"'{field}' field is required"
        
        # Check for empty string values
        if isinstance(data[field], str) and not data[field].strip():
            return f"'{field}' cannot be empty"
    
    return None


def validate_pagination_params(page: int = 1, per_page: int = 10, max_per_page: int = 100) -> Optional[str]:
    """
    Validate pagination parameters.
    
    Args:
        page (int): Page number
        per_page (int): Items per page
        max_per_page (int): Maximum allowed items per page
        
    Returns:
        Optional[str]: Error message if validation fails, None if valid
    """
    if page < 1:
        return "Page number must be greater than 0"
    
    if per_page < 1:
        return "Items per page must be greater than 0"
    
    if per_page > max_per_page:
        return f"Items per page cannot exceed {max_per_page}"
    
    return None


def validate_search_params(top_k: int, similarity_threshold: float) -> Optional[str]:
    """
    Validate search parameters.
    
    Args:
        top_k (int): Number of results to retrieve
        similarity_threshold (float): Similarity threshold
        
    Returns:
        Optional[str]: Error message if validation fails, None if valid
    """
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        return "top_k must be an integer between 1 and 20"
    
    if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1:
        return "similarity_threshold must be a number between 0 and 1"
    
    return None