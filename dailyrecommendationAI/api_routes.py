import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from config import Config
from pregnancy_rag_system import PregnancyRAGSystem

logger = logging.getLogger(__name__)

# Create blueprint for API routes
api = Blueprint('api', __name__, url_prefix='/api')

# Initialize RAG system
rag_system = PregnancyRAGSystem()

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'vector_db_size': len(rag_system.vector_database.document_chunks),
        'database_connected': rag_system.database_manager.is_connected(),
        'groq_available': rag_system.ai_service.groq_available
    })

@api.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """Upload and process PDF file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not rag_system.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process PDF
        success = rag_system.process_pdf(file_path, filename)
        
        # Clean up
        os.remove(file_path)
        
        if success:
            return jsonify({
                'message': f'File {filename} uploaded and processed successfully',
                'filename': filename,
                'vector_db_size': len(rag_system.vector_database.document_chunks)
            })
        else:
            return jsonify({'error': 'Failed to process PDF file'}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        name = data.get('name')
        pregnancy_week = data.get('pregnancy_week')
        preferences = data.get('preferences', '')
        
        if not name or not pregnancy_week:
            return jsonify({'error': 'Name and pregnancy_week are required'}), 400
        
        if not isinstance(pregnancy_week, int) or pregnancy_week < 1 or pregnancy_week > 42:
            return jsonify({'error': 'Pregnancy week must be between 1 and 42'}), 400
        
        if not rag_system.database_manager.is_connected():
            return jsonify({'error': 'Database connection not available'}), 500
        
        user_id = rag_system.register_user(name, pregnancy_week, preferences)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id,
            'name': name,
            'pregnancy_week': pregnancy_week,
            'preferences': preferences
        })
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information"""
    try:
        if not rag_system.database_manager.is_connected():
            return jsonify({'error': 'Database connection not available'}), 500
        
        user = rag_system.get_user(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user_id': user['id'],
            'name': user['name'],
            'pregnancy_week': user['pregnancy_week'],
            'preferences': user['preferences'],
            'created_at': user['created_at'].isoformat() if user['created_at'] else None
        })
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if not rag_system.database_manager.is_connected():
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Check if user exists
        user = rag_system.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get update fields
        name = data.get('name')
        pregnancy_week = data.get('pregnancy_week')
        preferences = data.get('preferences')
        
        if pregnancy_week is not None and (not isinstance(pregnancy_week, int) or pregnancy_week < 1 or pregnancy_week > 42):
            return jsonify({'error': 'Pregnancy week must be between 1 and 42'}), 400
        
        # Update user
        success = rag_system.update_user(user_id, name, pregnancy_week, preferences)
        
        if not success:
            return jsonify({'error': 'Failed to update user'}), 500
        
        # Get updated user data
        updated_user = rag_system.get_user(user_id)
        
        return jsonify({
            'message': 'User updated successfully',
            'user_id': user_id,
            'name': updated_user['name'],
            'pregnancy_week': updated_user['pregnancy_week'],
            'preferences': updated_user['preferences']
        })
        
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/recommendation/<int:user_id>', methods=['GET'])
def get_recommendation(user_id):
    """Get daily recommendation for user"""
    try:
        recommendation = rag_system.get_daily_recommendation(user_id)
        
        return jsonify({
            'user_id': user_id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'recommendation': recommendation
        })
        
    except Exception as e:
        logger.error(f"Get recommendation error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/search', methods=['POST'])
def search_knowledge_base():
    """Search the knowledge base for relevant information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        query = data.get('query')
        top_k = data.get('top_k', 5)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            return jsonify({'error': 'top_k must be between 1 and 20'}), 400
        
        results = rag_system.search_similar_chunks(query, top_k)
        
        formatted_results = []
        for chunk, score in results:
            formatted_results.append({
                'text': chunk,
                'similarity_score': score
            })
        
        return jsonify({
            'query': query,
            'results_count': len(formatted_results),
            'results': formatted_results
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/recommendations/history/<int:user_id>', methods=['GET'])
def get_recommendation_history(user_id):
    """Get recommendation history for user"""
    try:
        if not rag_system.database_manager.is_connected():
            return jsonify({'error': 'Database connection not available'}), 500
        
        recommendations = rag_system.get_recommendation_history(user_id)
        
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                'date': rec['recommendation_date'].isoformat() if rec['recommendation_date'] else None,
                'recommendation': rec['recommendation'],
                'created_at': rec['created_at'].isoformat() if rec['created_at'] else None
            })
        
        return jsonify({
            'user_id': user_id,
            'recommendations_count': len(formatted_recommendations),
            'recommendations': formatted_recommendations
        })
        
    except Exception as e:
        logger.error(f"Get recommendation history error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/debug/recommendation/<int:user_id>', methods=['GET'])
def debug_recommendation(user_id):
    """Debug endpoint to check recommendation generation process"""
    try:
        debug_info = rag_system.get_debug_info(user_id)
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Debug error: {e}")
        return jsonify({'error': str(e)}), 500

@api.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        stats = rag_system.get_system_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500