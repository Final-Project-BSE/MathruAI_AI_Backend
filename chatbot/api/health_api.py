"""
Health check and system status API endpoints.
"""
from flask import Blueprint, current_app, jsonify
from datetime import datetime
import logging
import traceback

from chatbot.utils.response_utils import create_success_response, create_error_response, log_api_request

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)


@health_bp.route('/', methods=['GET'])
def index():
    """API documentation and status."""
    log_api_request('/', 'GET', request.remote_addr if 'request' in globals() else 'unknown')
    
    system_status = "healthy" if current_app.rag_system else "unhealthy"
    
    api_info = {
        "name": "Enhanced Pregnancy RAG API",
        "version": "2.3",
        "status": system_status,
        "description": "Advanced RAG system with FAISS vector search, MySQL storage, and chat history management",
        "features": [
            "FAISS vector indexing for fast similarity search",
            "MySQL database for metadata and search logging",
            "Chat session management with history",
            "Advanced semantic search with configurable parameters",
            "PDF document processing and ingestion",
            "Smart text chunking with overlap",
            "Query analytics and performance monitoring",
            "Robust caching and persistence",
            "Comprehensive error handling and logging",
            "Modular API structure for easy extension"
        ],
        "endpoints": {
            "/": "GET - API documentation and status",
            "/health": "GET - Comprehensive system health check",
            "/stats": "GET - Knowledge base and system statistics",
            "/chat": "POST - Interactive chat with AI assistant",
            "/chats": "GET - Get list of chat sessions, POST - Create new chat session",
            "/chats/<session_id>": "GET - Get chat history, DELETE - Delete chat session",
            "/search": "POST - Advanced semantic search",
            "/upload": "POST - Upload and process PDF documents",
            "/reinitialize": "POST - Reinitialize RAG system (admin)"
        },
        "parameter_specs": {
            "chat_parameters": {
                "message": "Required - User message/question",
                "session_id": "Optional - Chat session ID",
                "top_k": "Optional - Number of relevant chunks (default: 3)",
                "similarity_threshold": "Optional - Minimum similarity score (default: 0.1)"
            },
            "search_parameters": {
                "query": "Required - Search query",
                "top_k": "Optional - Number of results (default: 3)",
                "similarity_threshold": "Optional - Minimum similarity score (default: 0.1)"
            }
        }
    }
    
    if current_app.rag_system:
        try:
            stats = current_app.rag_system.get_system_stats()
            api_info["current_stats"] = stats
        except Exception as e:
            api_info["stats_error"] = str(e)
    
    return jsonify(api_info)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check."""
    log_api_request('/health', 'GET', request.remote_addr if 'request' in globals() else 'unknown')
    
    health_info = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "rag_system_ready": current_app.rag_system is not None,
        "components": {}
    }
    
    if current_app.rag_system:
        try:
            stats = current_app.rag_system.get_system_stats()
            health_info["components"] = {
                "knowledge_base": {
                    "status": "healthy" if stats["total_chunks"] > 0 else "empty",
                    "total_chunks": stats["total_chunks"]
                },
                "faiss_index": {
                    "status": "healthy" if stats["faiss_index_size"] > 0 else "empty",
                    "vectors": stats["faiss_index_size"],
                    "dimension": stats["embedding_dimension"]
                },
                "database": {
                    "status": "healthy" if stats["database_connected"] else "disconnected",
                    "connected": stats["database_connected"]
                },
                "embedding_model": {
                    "status": "healthy",
                    "model": stats["embedding_model"]
                }
            }
            
            # Overall health assessment
            if (stats["total_chunks"] == 0 or 
                stats["faiss_index_size"] == 0 or 
                not stats["database_connected"]):
                health_info["status"] = "degraded"
                
        except Exception as e:
            health_info["error"] = str(e)
            health_info["status"] = "unhealthy"
            logger.error(f"Health check error: {str(e)}")
    else:
        health_info["status"] = "unhealthy"
        health_info["error"] = "RAG system not initialized"
    
    status_code = 200 if health_info["status"] in ["healthy", "degraded"] else 503
    return jsonify(health_info), status_code


@health_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get comprehensive system statistics."""
    log_api_request('/stats', 'GET', request.remote_addr if 'request' in globals() else 'unknown')
    
    if not current_app.rag_system:
        return create_error_response("RAG system not initialized", 503)
    
    try:
        stats = current_app.rag_system.get_system_stats()
        
        # Enhanced system information
        system_info = {
            "system_status": "operational",
            "initialization_time": datetime.now().isoformat(),
            "features_enabled": [
                "FAISS vector search",
                "MySQL metadata storage", 
                "Semantic similarity search",
                "PDF document processing",
                "Query logging and analytics",
                "Smart text chunking",
                "Embedding caching",
                "Modular API architecture"
            ],
            "performance_metrics": {
                "embedding_model": stats.get("embedding_model", "all-MiniLM-L6-v2"),
                "embedding_dimension": stats.get("embedding_dimension", 384),
                "index_type": "FAISS IndexFlatIP with IDMap"
            }
        }
        
        return create_success_response({
            "knowledge_base_stats": stats,
            "system_info": system_info
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return create_error_response(f"Failed to retrieve stats: {str(e)}")


@health_bp.route('/reinitialize', methods=['POST'])
def reinitialize_system():
    """Reinitialize RAG system (admin endpoint)."""
    log_api_request('/reinitialize', 'POST', request.remote_addr if 'request' in globals() else 'unknown')
    
    try:
        logger.info("Reinitializing RAG system...")
        
        # Close existing system if available
        if current_app.rag_system:
            try:
                current_app.rag_system.__del__()
            except:
                pass
        
        # Reinitialize
        from core.app import initialize_rag_system
        current_app.rag_system = initialize_rag_system()
        
        if current_app.rag_system:
            stats = current_app.rag_system.get_system_stats()
            return create_success_response({
                "reinitialized": True,
                "stats": stats
            }, "RAG system reinitialized successfully")
        else:
            return create_error_response("Failed to reinitialize RAG system", 500)
            
    except Exception as e:
        logger.error(f"Error reinitializing system: {str(e)}")
        return create_error_response(f"Reinitialization failed: {str(e)}")