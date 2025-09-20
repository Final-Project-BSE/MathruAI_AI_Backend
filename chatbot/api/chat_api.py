"""
Chat and conversation management API endpoints with user authentication.
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

# Import the corrected authentication decorator
from chatbot.utils.AuthUtils import require_auth

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@chat_bp.route('/debug-secret', methods=['GET'])
def debug_secret():
    import base64
    original_secret = current_app.config['JWT_SECRET_KEY']
    
    try:
        decoded_secret = base64.b64decode(original_secret)
        return {
            "original_length": len(original_secret),
            "decoded_length": len(decoded_secret),
            "original_preview": original_secret[:20] + "...",
            "decoded_preview": decoded_secret[:10].hex() + "..."
        }
    except Exception as e:
        return {"error": str(e)}

# Add this to chat_api.py temporarily
@chat_bp.route('/debug-token', methods=['POST'])
def debug_token():
    import jwt
    from flask import request
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return {"error": "No Authorization header"}
    
    token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
    
    try:
        # Get token without verification to see its structure
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        return {
            "header": header,
            "payload": payload,
            "secret_preview": current_app.config['JWT_SECRET_KEY'][:10] + "..."
        }
    except Exception as e:
        return {"error": str(e)}

@chat_bp.route('/chat', methods=['POST'])
@require_auth  # Now using the corrected decorator
def chat():
    """Interactive chat with AI assistant with user-specific session support."""
    log_api_request('/chat', 'POST', request.remote_addr)
    
    # Get authenticated user
    user = request.current_user
    user_id = user['user_id']
    
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
        
        # Create session if not provided - NOW LINKED TO USER
        if not session_id and current_app.rag_system.db_manager and current_app.rag_system.db_manager.connection:
            session_id = current_app.rag_system.db_manager.create_chat_session(
                user_id=user_id,
                session_name=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        # Verify session belongs to current user (SECURITY CHECK)
        if session_id:
            session_owner = current_app.rag_system.db_manager.get_session_owner(session_id)
            if session_owner != user_id:
                return create_error_response("Access denied to this chat session", 403)
        
        logger.info(f"Chat request - User: {user_id}, Session: {session_id}, Query: {user_message[:100]}...")
        
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
            
            # Store chat messages in database with user context
            if session_id and current_app.rag_system.db_manager and current_app.rag_system.db_manager.connection:
                current_app.rag_system.db_manager.store_chat_message(
                    session_id=session_id,
                    user_id=user_id,
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
                "user_id": user_id,
                "session_id": session_id,
                "parameters_used": {
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold
                }
            }
            
            return create_success_response(response_data)
            
        finally:
            # Restore original method
            current_app.rag_system.find_relevant_context = original_method
        
    except Exception as e:
        logger.error(f"Error in chat for user {user_id}: {str(e)}")
        return create_error_response(f"Chat processing failed: {str(e)}")


@chat_bp.route('/chats', methods=['GET'])
@require_auth
def get_user_chat_sessions():
    """Get chat sessions for the authenticated user only."""
    log_api_request('/chats', 'GET', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
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
        
        # Get sessions ONLY for the authenticated user
        sessions = current_app.rag_system.db_manager.get_user_chat_sessions(user_id, limit)
        
        return create_success_response({
            "sessions": sessions,
            "total_count": len(sessions),
            "user_id": user_id,
            "limit": limit
        }, "User chat sessions retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting chat sessions for user {user_id}: {str(e)}")
        return create_error_response(f"Failed to get chat sessions: {str(e)}")


@chat_bp.route('/chats', methods=['POST'])
@require_auth
def create_user_chat_session():
    """Create a new chat session for the authenticated user."""
    log_api_request('/chats', 'POST', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
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
        
        # Create session linked to user
        session_id = current_app.rag_system.db_manager.create_chat_session(
            user_id=user_id,
            session_name=session_name
        )
        
        if session_id > 0:
            return create_success_response({
                "session_id": session_id,
                "user_id": user_id,
                "session_name": session_name or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }, "Chat session created successfully")
        else:
            return create_error_response("Failed to create chat session")
            
    except Exception as e:
        logger.error(f"Error creating chat session for user {user_id}: {str(e)}")
        return create_error_response(f"Failed to create chat session: {str(e)}")


@chat_bp.route('/chats/<int:session_id>', methods=['GET'])
@require_auth
def get_user_chat_history(session_id):
    """Get chat history for a specific session (user-owned only)."""
    log_api_request(f'/chats/{session_id}', 'GET', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        # Security check: verify session belongs to user
        session_owner = current_app.rag_system.db_manager.get_session_owner(session_id)
        if session_owner != user_id:
            return create_error_response("Access denied to this chat session", 403)
        
        # Get messages for user's session
        messages = current_app.rag_system.db_manager.get_user_chat_messages(user_id, session_id)
        
        return create_success_response({
            "session_id": session_id,
            "user_id": user_id,
            "messages": messages,
            "message_count": len(messages)
        }, "Chat history retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting chat history for user {user_id}, session {session_id}: {str(e)}")
        return create_error_response(f"Failed to get chat history: {str(e)}")


@chat_bp.route('/chats/<int:session_id>', methods=['DELETE'])
@require_auth
def delete_user_chat_session(session_id):
    """Delete a user's chat session (user-owned only)."""
    log_api_request(f'/chats/{session_id}', 'DELETE', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        # Delete session (includes user ownership check)
        success = current_app.rag_system.db_manager.delete_user_chat_session(session_id, user_id)
        
        if success:
            return create_success_response({
                "session_id": session_id,
                "user_id": user_id,
                "deleted": True
            }, "Chat session deleted successfully")
        else:
            return create_error_response("Chat session not found or access denied", 404)
            
    except Exception as e:
        logger.error(f"Error deleting chat session for user {user_id}: {str(e)}")
        return create_error_response(f"Failed to delete chat session: {str(e)}")


@chat_bp.route('/chats/<int:session_id>/export', methods=['GET'])
@require_auth
def export_user_chat_session(session_id):
    """Export user's chat session as JSON."""
    log_api_request(f'/chats/{session_id}/export', 'GET', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        # Security check: verify session belongs to user
        session_owner = current_app.rag_system.db_manager.get_session_owner(session_id)
        if session_owner != user_id:
            return create_error_response("Access denied to this chat session", 403)
        
        # Get messages for export
        messages = current_app.rag_system.db_manager.get_user_chat_messages(user_id, session_id)
        
        if not messages:
            return create_error_response("Chat session not found or has no messages", 404)
        
        # Format for export
        export_data = {
            "session_id": session_id,
            "user_id": user_id,
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
        logger.error(f"Error exporting chat session for user {user_id}: {str(e)}")
        return create_error_response(f"Failed to export chat session: {str(e)}")

# Add this debug endpoint to your Flask app

@chat_bp.route('/api/debug-jwt', methods=['POST'])

def debug_jwt():
    """Debug JWT token issues."""
    import jwt
    from flask import request
    
    try:
        # Get token from request
        data = request.get_json()
        token = data.get('token') if data else None
        
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            return {"error": "No token provided"}
        
        # Try to get unverified header and payload
        try:
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            return {
                "token_header": header,
                "token_payload": payload,
                "expected_secret": app.config['JWT_SECRET_KEY'][:10] + "...",  # Only show first 10 chars
                "algorithms_tried": ['HS256', 'HS512']
            }
        except Exception as e:
            return {"error": f"Could not parse token: {str(e)}"}
            
    except Exception as e:
        return {"error": f"Debug failed: {str(e)}"}


@chat_bp.route('/user/stats', methods=['GET'])
@require_auth
def get_user_statistics():
    """Get chat statistics for the authenticated user."""
    log_api_request('/user/stats', 'GET', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    
    if not current_app.rag_system.db_manager or not current_app.rag_system.db_manager.connection:
        return create_error_response("Database not available", 503)
    
    try:
        days = request.args.get('days', 7, type=int)
        
        # Get user statistics
        stats = current_app.rag_system.db_manager.get_user_statistics(user_id, days)
        
        return create_success_response(stats, "User statistics retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting user statistics for {user_id}: {str(e)}")
        return create_error_response(f"Failed to get user statistics: {str(e)}")


# Keep the streaming chat endpoint for future use
@chat_bp.route('/chat/stream', methods=['POST'])
@require_auth
def chat_stream():
    """
    Streaming chat endpoint for future real-time features.
    Currently returns standard response but structured for streaming.
    """
    log_api_request('/chat/stream', 'POST', request.remote_addr)
    
    user = request.current_user
    user_id = user['user_id']
    
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
            "user_id": user_id,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error in streaming chat for user {user_id}: {str(e)}")
        return create_error_response(f"Streaming chat failed: {str(e)}")

        