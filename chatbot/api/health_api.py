"""
Health check and system status API endpoints - FIXED VERSION.
"""
from flask import Blueprint, current_app, jsonify, request
from datetime import datetime
import logging

from chatbot.utils.response_utils import create_success_response, create_error_response, log_api_request

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

@health_bp.route('/', methods=['GET'])
def api_index():
    """API documentation and status."""
    log_api_request('/', 'GET', request.remote_addr)
    
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
            "/api/": "GET - API documentation and status",
            "/api/health": "GET - Comprehensive system health check", 
            "/api/stats": "GET - Knowledge base and system statistics",
            "/api/chat": "POST - Interactive chat with AI assistant",
            "/api/chats": "GET - Get list of chat sessions, POST - Create new chat session",
            "/api/chats/<session_id>": "GET - Get chat history, DELETE - Delete chat session",
            "/api/search": "POST - Advanced semantic search",
            "/api/upload": "POST - Upload and process PDF documents",
            "/api/upload/status": "GET - Upload system status"
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
    log_api_request('/health', 'GET', request.remote_addr)
    
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
                    "dimension": stats.get("embedding_dimension", "unknown")
                },
                "database": {
                    "status": "healthy" if stats["database_connected"] else "disconnected",
                    "connected": stats["database_connected"]
                },
                "embedding_model": {
                    "status": "healthy",
                    "model": stats["embedding_model"]
                },
                "authentication": {
                    "status": "healthy" if hasattr(current_app, 'auth_utils') else "not_configured",
                    "configured": hasattr(current_app, 'auth_utils')
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
    log_api_request('/stats', 'GET', request.remote_addr)
    
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
            },
            "database_status": {
                "connected": stats.get("database_connected", False),
                "manager_available": hasattr(current_app, 'db_manager') and current_app.db_manager is not None
            },
            "authentication": {
                "configured": hasattr(current_app, 'auth_utils'),
                "jwt_secret_configured": bool(current_app.config.get('JWT_SECRET_KEY'))
            }
        }
        
        return create_success_response({
            "knowledge_base_stats": stats,
            "system_info": system_info
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return create_error_response(f"Failed to retrieve stats: {str(e)}")

@health_bp.route('/debug', methods=['GET'])
def debug_info():
    """Get debug information about the system."""
    log_api_request('/debug', 'GET', request.remote_addr)
    
    debug_info = {
        "flask_app_configured": True,
        "rag_system": {
            "initialized": hasattr(current_app, 'rag_system') and current_app.rag_system is not None,
            "type": type(current_app.rag_system).__name__ if hasattr(current_app, 'rag_system') else None
        },
        "database": {
            "manager_initialized": hasattr(current_app, 'db_manager') and current_app.db_manager is not None,
            "connection_available": (hasattr(current_app, 'db_manager') and 
                                   current_app.db_manager and 
                                   current_app.db_manager.connection is not None)
        },
        "authentication": {
            "auth_utils_initialized": hasattr(current_app, 'auth_utils'),
            "jwt_secret_key_set": bool(current_app.config.get('JWT_SECRET_KEY'))
        },
        "upload_config": {
            "upload_folder": current_app.config.get('UPLOAD_FOLDER'),
            "allowed_extensions": current_app.config.get('ALLOWED_EXTENSIONS'),
            "max_file_size": current_app.config.get('MAX_FILE_SIZE')
        },
        "registered_blueprints": [bp.name for bp in current_app.blueprints.values()],
        "routes": [
            {
                "rule": str(rule),
                "endpoint": rule.endpoint,
                "methods": list(rule.methods)
            }
            for rule in current_app.url_map.iter_rules()
        ]
    }
    
    return create_success_response(debug_info, "Debug information retrieved successfully")