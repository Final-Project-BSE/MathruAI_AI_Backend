"""
Chat and conversation management API endpoints.
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
    validate_pagination_params,
    log_api_request
)

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """Interactive chat with AI assistant with session support."""
    log_api_request('/chat', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
        
    try:
        data = request.get_json()
        
        # Validate request
        validation_error = validate_json_request(data, ['message'])
        if validation_error:
            return create_error_response(validation_error, 400)
            
        user_message = data['message'].strip()
        session_id = data.get('session_id')
        
        # Extract optional parameters
        top_k = data.get('top_k', 3)
        similarity_threshold = data.get('similarity_threshold', 0.1)
        
        # Validate search parameters
        param_error = validate_search_params(top_k, similarity_threshold)
        if param_error:
            return create_error_response(param_error, 400)
        
        # Create session if not provided and database is available
        if not session_id and current_app.rag_system.db_manager and current_app.rag_system.db_manager.connection:
            session_id = current_app.rag_system.db_manager.create_chat_session()
        
        logger.info(f"Chat request - Session: {session_id}, Query: {user_message[:100]}..., top_k: {top_k}, threshold: {similarity_threshold}")
        
        start_time = datetime.now()
        
        # Store original method and temporarily modify retrieval parameters
        original_method = current_app.rag_system.find_relevant_context
        
        def custom_find_context(query):
            return original_method(query, top_k=top_k, similarity_threshold=similarity_threshold)
        
        # Temporarily replace method
        current_app.rag_system.find_relevant_context = custom_find_context
        
        try:
            # Generate response
            response_text = current_app.rag_system.generate_response(user_message)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Store chat messages in database if session exists
            if session_id and current_app.rag_system.db_manager and current_app.rag_system.db_manager.connection:
                current_app.rag_system.db_manager.store_chat_message(
                    session_id=session_id,
                    message=user_message,
                    response=response_text,
                    message_type='assistant',
                    response_time_ms=int(processing_time * 1000),
                    context_chunks_count=top_k,
                    similarity_threshold=similarity_threshold,
                    top_k=top_k
                )
            
            response_data = {
                "response": response_text,
                "processing_time_seconds": round(processing_time, 3),
                "search_method": "FAISS vector similarity + MySQL logging",
                "parameters_used": {
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold
                }
            }
            
            # Include session_id in response
            if session_id:
                response_data["session_id"] = session_id
            
            return create_success_response(response_data)
            
        finally:
            # Restore original method
            current_app.rag_system.find_relevant_context = original_method
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return create_error_response(f"Chat processing failed: {str(e)}")


@chat_bp.route('/chats', methods=['GET'])
def get_chat_sessions():
    """Get list of all chat sessions."""
    log_api_request('/chats', 'GET', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Validate pagination
        validation_error = validate_pagination_params(per_page=limit, max_per_page=100)
        if validation_error:
            return create_error_response(validation_error, 400)
        
        sessions = current_app.rag_system.db_manager.get_chat_sessions(limit)
        
        return create_success_response({
            "sessions": sessions,
            "total_count": len(sessions),
            "limit": limit
        }, "Chat sessions retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting chat sessions: {str(e)}")
        return create_error_response(f"Failed to get chat sessions: {str(e)}")


@chat_bp.route('/chats', methods=['POST'])
def create_chat_session():
    """Create a new chat session."""
    log_api_request('/chats', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        data = request.get_json() or {}
        session_name = data.get('session_name')
        
        # Validate session name if provided
        if session_name and (len(session_name.strip()) == 0 or len(session_name) > 255):
            return create_error_response("Session name must be between 1 and 255 characters", 400)
        
        session_id = current_app.rag_system.db_manager.create_chat_session(session_name)
        
        if session_id > 0:
            return create_success_response({
                "session_id": session_id,
                "session_name": session_name or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }, "Chat session created successfully")
        else:
            return create_error_response("Failed to create chat session")
            
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        return create_error_response(f"Failed to create chat session: {str(e)}")


@chat_bp.route('/chats/<int:session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a specific session."""
    log_api_request(f'/chats/{session_id}', 'GET', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        messages = current_app.rag_system.db_manager.get_chat_messages(session_id)
        
        return create_success_response({
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages)
        }, "Chat history retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return create_error_response(f"Failed to get chat history: {str(e)}")


@chat_bp.route('/chats/<int:session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """Delete a chat session."""
    log_api_request(f'/chats/{session_id}', 'DELETE', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        success = current_app.rag_system.db_manager.delete_chat_session(session_id)
        
        if success:
            return create_success_response({
                "session_id": session_id,
                "deleted": True
            }, "Chat session deleted successfully")
        else:
            return create_error_response("Chat session not found or already deleted", 404)
            
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        return create_error_response(f"Failed to delete chat session: {str(e)}")


@chat_bp.route('/chats/<int:session_id>/export', methods=['GET'])
def export_chat_session(session_id):
    """
    Export chat session as JSON.
    New endpoint for future data export needs.
    """
    log_api_request(f'/chats/{session_id}/export', 'GET', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        messages = current_app.rag_system.db_manager.get_chat_messages(session_id)
        
        if not messages:
            return create_error_response("Chat session not found or has no messages", 404)
        
        # Format for export
        export_data = {
            "session_id": session_id,
            "export_timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "conversation": []
        }
        
        for msg in messages:
            if msg['message_type'] == 'assistant':
                export_data["conversation"].append({
                    "timestamp": msg['created_at'],
                    "user_message": msg['message'],
                    "assistant_response": msg['response'],
                    "response_time_ms": msg.get('response_time_ms'),
                    "context_chunks_used": msg.get('context_chunks_count')
                })
        
        return create_success_response(export_data, "Chat session exported successfully")
        
    except Exception as e:
        logger.error(f"Error exporting chat session: {str(e)}")
        return create_error_response(f"Failed to export chat session: {str(e)}")


@chat_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    Streaming chat endpoint for future real-time features.
    Currently returns standard response but structured for streaming.
    """
    log_api_request('/chat/stream', 'POST', request.remote_addr)
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
        
    try:
        data = request.get_json()
        
        # Validate request
        validation_error = validate_json_request(data, ['message'])
        if validation_error:
            return create_error_response(validation_error, 400)
            
        user_message = data['message'].strip()
        session_id = data.get('session_id')
        
        # For now, use regular response generation
        # In future, this can be enhanced with Server-Sent Events
        start_time = datetime.now()
        response_text = current_app.rag_system.generate_response(user_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return create_success_response({
            "response": response_text,
            "processing_time_seconds": round(processing_time, 3),
            "stream_support": "planned",
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error in streaming chat: {str(e)}")
        return create_error_response(f"Streaming chat failed: {str(e)}")