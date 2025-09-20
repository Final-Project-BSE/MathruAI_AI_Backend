"""
RAG system search and retrieval API endpoints - FIXED VERSION.
"""
from flask import Blueprint, request, current_app
from datetime import datetime
import logging

from chatbot.utils.response_utils import (
    create_success_response, 
    create_error_response, 
    validate_rag_system,
    validate_json_request,
    validate_search_params,
    log_api_request
)

rag_bp = Blueprint('rag', __name__)
logger = logging.getLogger(__name__)

@rag_bp.route('/search', methods=['POST'])
def search_knowledge():
    """Advanced semantic search with FAISS."""
    log_api_request('/search', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
        
    try:
        data = request.get_json()
        
        # Validate request
        validation_error = validate_json_request(data, ['query'])
        if validation_error:
            return create_error_response(validation_error, 400)
            
        query = data['query'].strip()
        top_k = data.get('top_k', 3)
        similarity_threshold = data.get('similarity_threshold', 0.1)
        
        # Validate search parameters
        param_error = validate_search_params(top_k, similarity_threshold)
        if param_error:
            return create_error_response(param_error, 400)
            
        logger.info(f"Search request - Query: {query[:100]}..., top_k: {top_k}, threshold: {similarity_threshold}")
        
        start_time = datetime.now()
        
        # Perform search
        context = current_app.rag_system.find_relevant_context(
            query, 
            top_k=top_k, 
            similarity_threshold=similarity_threshold
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Handle context result - it might be a list or string
        if isinstance(context, list):
            chunks = [str(chunk).strip() for chunk in context if str(chunk).strip()]
        else:
            # Split context into chunks for display
            chunks = [chunk.strip() for chunk in str(context).split('\n\n') if chunk.strip()]
        
        return create_success_response({
            "query": query,
            "relevant_chunks": chunks,
            "num_chunks_found": len(chunks),
            "processing_time_seconds": round(processing_time, 3),
            "search_method": "FAISS vector similarity",
            "parameters": {
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
        })
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return create_error_response(f"Search failed: {str(e)}")

@rag_bp.route('/context', methods=['POST'])
def get_context():
    """Get raw context without generating a response."""
    log_api_request('/context', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
        
    try:
        data = request.get_json()
        
        # Validate request
        validation_error = validate_json_request(data, ['query'])
        if validation_error:
            return create_error_response(validation_error, 400)
            
        query = data['query'].strip()
        top_k = data.get('top_k', 5)
        similarity_threshold = data.get('similarity_threshold', 0.1)
        
        # Validate search parameters
        param_error = validate_search_params(top_k, similarity_threshold)
        if param_error:
            return create_error_response(param_error, 400)
        
        start_time = datetime.now()
        
        # Get context
        context = current_app.rag_system.find_relevant_context(
            query, 
            top_k=top_k, 
            similarity_threshold=similarity_threshold
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Convert context to string if it's a list
        context_str = str(context) if not isinstance(context, str) else context
        
        # Simple token count (approximate)
        token_count = len(context_str.split()) if context_str else 0
        
        return create_success_response({
            "query": query,
            "context": context_str,
            "context_length": len(context_str),
            "token_count": token_count,
            "processing_time_seconds": round(processing_time, 3),
            "parameters": {
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return create_error_response(f"Context retrieval failed: {str(e)}")

@rag_bp.route('/stats', methods=['GET'])
def get_rag_stats():
    """Get RAG system statistics."""
    log_api_request('/stats', 'GET', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    try:
        stats = current_app.rag_system.get_system_stats()
        
        return create_success_response({
            "rag_stats": stats,
            "system_info": {
                "status": "operational",
                "features_enabled": [
                    "FAISS vector search",
                    "Semantic similarity search",
                    "PDF document processing",
                    "Query logging and analytics",
                    "Smart text chunking"
                ]
            }
        }, "RAG system statistics retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting RAG stats: {str(e)}")
        return create_error_response(f"Failed to retrieve RAG stats: {str(e)}")