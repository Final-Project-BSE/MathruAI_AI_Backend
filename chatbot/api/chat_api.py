import logging
from datetime import datetime

from flask import Blueprint, current_app, request

from chatbot.utils.AuthUtils import require_auth
from chatbot.utils.response_utils import (
    create_error_response,
    create_success_response,
    log_api_request,
    validate_json_request,
    validate_pagination_params,
    validate_rag_system,
    validate_search_params,
)

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)


def generate_chat_title(message: str, max_length: int = 60) -> str:
    if not message:
        return "New chat"
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        return "New chat"
    return cleaned[:max_length].rstrip() + ("..." if len(cleaned) > max_length else "")


def _get_db_manager():
    rag_system = getattr(current_app, 'rag_system', None)
    return getattr(rag_system, 'db_manager', None)


def _ensure_db_available():
    db_manager = _get_db_manager()
    return db_manager is not None and getattr(db_manager, 'connection', None) is not None


def _validate_session_ownership(session_id, user_id):
    db_manager = _get_db_manager()
    session_owner = db_manager.get_session_owner(session_id)
    return session_owner == user_id


@chat_bp.route('/chat', methods=['POST'])
@require_auth
def chat():
    log_api_request('/chat', 'POST', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)

    try:
        data = request.get_json()
        validation_error = validate_json_request(data, ['message'])
        if validation_error:
            return create_error_response(validation_error, 400)

        user_message = data['message'].strip()
        session_id = data.get('session_id')
        top_k = data.get('top_k', 3)
        similarity_threshold = data.get('similarity_threshold', 0.1)

        param_error = validate_search_params(top_k, similarity_threshold)
        if param_error:
            return create_error_response(param_error, 400)

        if not session_id and _ensure_db_available():
            session_id = _get_db_manager().create_chat_session(user_id=user_id, session_name="New chat")

        if session_id and _ensure_db_available() and not _validate_session_ownership(session_id, user_id):
            return create_error_response("Access denied to this chat session", 403)

        logger.info("Chat request - User: %s, Session: %s, Query: %s...", user_id, session_id, user_message[:100])
        start_time = datetime.now()
        original_method = current_app.rag_system.find_relevant_context

        def custom_find_context(query):
            return original_method(query, top_k=top_k, similarity_threshold=similarity_threshold)

        current_app.rag_system.find_relevant_context = custom_find_context
        try:
            response_text = current_app.rag_system.generate_response(user_message)
            processing_time = (datetime.now() - start_time).total_seconds()
            if session_id and _ensure_db_available():
                db_manager = _get_db_manager()
                db_manager.store_chat_message(
                    session_id=session_id,
                    user_id=user_id,
                    message=user_message,
                    response=response_text,
                    message_type='assistant',
                    response_time_ms=int(processing_time * 1000),
                    context_chunks_count=top_k,
                    similarity_threshold=similarity_threshold,
                    top_k=top_k,
                )
                current_title = db_manager.get_chat_session_title(session_id, user_id)
                message_count = db_manager.get_chat_session_message_count(session_id, user_id)
                if current_title and current_title.strip().lower() == "new chat" and message_count == 1:
                    db_manager.update_chat_session_title(session_id, user_id, generate_chat_title(user_message))

            return create_success_response({
                "response": response_text,
                "processing_time_seconds": round(processing_time, 3),
                "user_id": user_id,
                "session_id": session_id,
                "parameters_used": {
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                },
            })
        finally:
            current_app.rag_system.find_relevant_context = original_method
    except Exception as exc:
        logger.error("Error in chat for user %s: %s", user_id, exc)
        return create_error_response(f"Chat processing failed: {str(exc)}")


@chat_bp.route('/chats', methods=['GET'])
@require_auth
def get_user_chat_sessions():
    log_api_request('/chats', 'GET', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        limit = request.args.get('limit', 50, type=int)
        validation_error = validate_pagination_params(per_page=limit, max_per_page=100)
        if validation_error:
            return create_error_response(validation_error, 400)
        sessions = _get_db_manager().get_user_chat_sessions(user_id, limit)
        return create_success_response({
            "sessions": sessions,
            "total_count": len(sessions),
            "user_id": user_id,
            "limit": limit,
        }, "User chat sessions retrieved successfully")
    except Exception as exc:
        logger.error("Error getting chat sessions for user %s: %s", user_id, exc)
        return create_error_response(f"Failed to get chat sessions: {str(exc)}")


@chat_bp.route('/chats', methods=['POST'])
@require_auth
def create_user_chat_session():
    log_api_request('/chats', 'POST', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        data = request.get_json() or {}
        session_name = data.get('session_name')
        if session_name and (len(session_name.strip()) == 0 or len(session_name) > 255):
            return create_error_response("Session name must be between 1 and 255 characters", 400)
        session_id = _get_db_manager().create_chat_session(user_id=user_id, session_name=session_name or "New chat")
        if session_id > 0:
            return create_success_response({
                "session_id": session_id,
                "user_id": user_id,
                "session_name": session_name or "New chat",
            }, "Chat session created successfully")
        return create_error_response("Failed to create chat session")
    except Exception as exc:
        logger.error("Error creating chat session for user %s: %s", user_id, exc)
        return create_error_response(f"Failed to create chat session: {str(exc)}")


@chat_bp.route('/chats/<int:session_id>', methods=['PATCH'])
@require_auth
def update_user_chat_session(session_id):
    log_api_request(f'/chats/{session_id}', 'PATCH', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        data = request.get_json() or {}
        session_name = (data.get('session_name') or "").strip()
        if not session_name:
            return create_error_response("session_name is required", 400)
        if len(session_name) > 255:
            return create_error_response("Session name must be 255 characters or less", 400)
        if not _validate_session_ownership(session_id, user_id):
            return create_error_response("Access denied to this chat session", 403)
        success = _get_db_manager().update_chat_session_title(session_id=session_id, user_id=user_id, session_name=session_name)
        if not success:
            return create_error_response("Failed to update chat session", 400)
        return create_success_response({
            "session_id": session_id,
            "user_id": user_id,
            "session_name": session_name,
            "updated": True,
        }, "Chat session updated successfully")
    except Exception as exc:
        logger.error("Error updating chat session for user %s: %s", user_id, exc)
        return create_error_response(f"Failed to update chat session: {str(exc)}")


@chat_bp.route('/chats/<int:session_id>', methods=['GET'])
@require_auth
def get_user_chat_history(session_id):
    log_api_request(f'/chats/{session_id}', 'GET', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        if not _validate_session_ownership(session_id, user_id):
            return create_error_response("Access denied to this chat session", 403)
        messages = _get_db_manager().get_user_chat_messages(user_id, session_id)
        return create_success_response({
            "session_id": session_id,
            "user_id": user_id,
            "messages": messages,
            "message_count": len(messages),
        }, "Chat history retrieved successfully")
    except Exception as exc:
        logger.error("Error getting chat history for user %s, session %s: %s", user_id, session_id, exc)
        return create_error_response(f"Failed to get chat history: {str(exc)}")


@chat_bp.route('/chats/<int:session_id>', methods=['DELETE'])
@require_auth
def delete_user_chat_session(session_id):
    log_api_request(f'/chats/{session_id}', 'DELETE', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        success = _get_db_manager().delete_user_chat_session(session_id, user_id)
        if success:
            return create_success_response({
                "session_id": session_id,
                "user_id": user_id,
                "deleted": True,
            }, "Chat session deleted successfully")
        return create_error_response("Chat session not found or access denied", 404)
    except Exception as exc:
        logger.error("Error deleting chat session for user %s: %s", user_id, exc)
        return create_error_response(f"Failed to delete chat session: {str(exc)}")


@chat_bp.route('/chats/<int:session_id>/export', methods=['GET'])
@require_auth
def export_user_chat_session(session_id):
    log_api_request(f'/chats/{session_id}/export', 'GET', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        if not _validate_session_ownership(session_id, user_id):
            return create_error_response("Access denied to this chat session", 403)
        messages = _get_db_manager().get_user_chat_messages(user_id, session_id)
        if not messages:
            return create_error_response("Chat session not found or has no messages", 404)
        export_data = {
            "session_id": session_id,
            "user_id": user_id,
            "export_timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "conversation": [],
        }
        for msg in messages:
            if msg['message_type'] == 'assistant':
                export_data["conversation"].append({
                    "timestamp": msg['created_at'],
                    "user_message": msg['message'],
                    "assistant_response": msg['response'],
                    "response_time_ms": msg.get('response_time_ms'),
                    "context_chunks_used": msg.get('context_chunks_count'),
                })
        return create_success_response(export_data, "Chat session exported successfully")
    except Exception as exc:
        logger.error("Error exporting chat session for user %s: %s", user_id, exc)
        return create_error_response(f"Failed to export chat session: {str(exc)}")

@chat_bp.route('/user/stats', methods=['GET'])
@require_auth
def get_user_statistics():
    log_api_request('/user/stats', 'GET', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    if not _ensure_db_available():
        return create_error_response("Database not available", 503)
    try:
        days = request.args.get('days', 7, type=int)
        stats = _get_db_manager().get_user_statistics(user_id, days)
        return create_success_response(stats, "User statistics retrieved successfully")
    except Exception as exc:
        logger.error("Error getting user statistics for %s: %s", user_id, exc)
        return create_error_response(f"Failed to get user statistics: {str(exc)}")


@chat_bp.route('/chat/stream', methods=['POST'])
@require_auth
def chat_stream():
    log_api_request('/chat/stream', 'POST', request.remote_addr)
    user_id = request.current_user['user_id']
    is_valid, error_msg = validate_rag_system(current_app.rag_system)
    if not is_valid:
        return create_error_response(error_msg, 503)
    try:
        data = request.get_json()
        validation_error = validate_json_request(data, ['message'])
        if validation_error:
            return create_error_response(validation_error, 400)
        user_message = data['message'].strip()
        session_id = data.get('session_id')
        start_time = datetime.now()
        response_text = current_app.rag_system.generate_response(user_message)
        processing_time = (datetime.now() - start_time).total_seconds()
        return create_success_response({
            "response": response_text,
            "processing_time_seconds": round(processing_time, 3),
            "stream_support": "planned",
            "user_id": user_id,
            "session_id": session_id,
        })
    except Exception as exc:
        logger.error("Error in streaming chat for user %s: %s", user_id, exc)
        return create_error_response(f"Streaming chat failed: {str(exc)}")
