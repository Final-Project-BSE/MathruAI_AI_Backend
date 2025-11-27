import os
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import logging
from dailyrecommendationAI.config import Config
from dailyrecommendationAI.database_manager import DatabaseManager
from dailyrecommendationAI.vector_database import VectorDatabase
from dailyrecommendationAI.pdf_processor import PDFProcessor
from dailyrecommendationAI.ai_service import AIService

logger = logging.getLogger(__name__)

class PregnancyRAGSystem:
    def __init__(self):
        # Initialize components
        self.database_manager = DatabaseManager()
        self.vector_database = VectorDatabase()
        self.pdf_processor = PDFProcessor()
        self.ai_service = AIService()
        
        # Create directories if they don't exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        logger.info("Pregnancy RAG System initialized successfully")
    
    def process_pdf(self, pdf_path: str, filename: str) -> bool:
        """Process PDF and add to vector database"""
        try:
            # Process PDF
            success, chunks, error_msg = self.pdf_processor.process_pdf(pdf_path)
            
            if not success:
                logger.error(f"PDF processing failed: {error_msg}")
                return False
            
            # Add chunks to vector database
            success = self.vector_database.add_chunks(chunks, filename)
            
            if success:
                logger.info(f"Successfully processed {filename} with {len(chunks)} chunks")
                return True
            else:
                logger.error(f"Failed to add chunks to vector database for {filename}")
                return False
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return False
    
    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar chunks using vector similarity"""
        return self.vector_database.search_similar_chunks(query, top_k)
    
    def get_daily_recommendation(self, user_id: int) -> str:
        """Get daily recommendation for user"""
        try:
            # Get user data
            user = self.database_manager.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return "User not found"
            
            logger.info(f"Processing recommendation for user {user_id}: {user['name']}, week {user['pregnancy_week']}")
            
            # Check if recommendation already exists for today
            today = datetime.now().date()
            existing_rec = self.database_manager.get_recommendation_for_date(user_id, today)
            
            if existing_rec:
                logger.info(f"Returning existing recommendation for user {user_id}")
                return existing_rec
            
            # Generate new recommendation
            query = f"pregnancy week {user['pregnancy_week']} daily advice nutrition exercise"
            logger.info(f"Searching knowledge base with query: {query}")
            context_chunks = self.search_similar_chunks(query)
            
            logger.info(f"Found {len(context_chunks)} relevant chunks")
            
            # Generate recommendation (either AI or fallback)
            if context_chunks:
                chunk_texts = [chunk[0] for chunk in context_chunks]
                logger.info("Attempting to generate AI recommendation with context")
                recommendation = self.ai_service.generate_recommendation(user, chunk_texts)
            else:
                logger.info("No context chunks found, using fallback recommendation")
                recommendation = self.ai_service.get_fallback_recommendation(user)
                
            
            # Save recommendation
            self.database_manager.save_recommendation(user_id, recommendation, today)
            
            logger.info(f"Recommendation generated and saved for user {user_id}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting daily recommendation: {e}")
            # Even in case of error, provide fallback
            try:
                user = self.database_manager.get_user(user_id)
                if user:
                    return self.ai_service.get_fallback_recommendation(user)
                else:
                    return "User not found"
                    
            except Exception as e2:
                logger.error(f"Error in fallback: {e2}")
                return "System temporarily unavailable. Please try again later."
    
    def register_user(self, name: str, pregnancy_week: int, preferences: str = '') -> int:
        """Register a new user"""
        return self.database_manager.register_user(name, pregnancy_week, preferences)
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        return self.database_manager.get_user(user_id)
    
    def update_user(self, user_id: int, name: str = None, pregnancy_week: int = None, preferences: str = None) -> bool:
        """Update user information"""
        return self.database_manager.update_user(user_id, name, pregnancy_week, preferences)
    
    def get_recommendation_history(self, user_id: int, limit: int = 30) -> List[Dict]:
        """Get recommendation history for user"""
        return self.database_manager.get_recommendation_history(user_id, limit)
    
    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        stats = {
            'vector_database': self.vector_database.get_stats(),
            'database_status': self.database_manager.is_connected(),
            'ai_service': self.ai_service.get_ai_status()
        }
        
        # Add database stats if available
        if self.database_manager.is_connected():
            db_stats = self.database_manager.get_stats()
            stats.update(db_stats)
        
        return stats
    
    def get_debug_info(self, user_id: int) -> Dict:
        """Get debug information for troubleshooting"""
        debug_info = {
            'user_id': user_id,
            'database_connected': self.database_manager.is_connected(),
            'vector_db_size': len(self.vector_database.document_chunks),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add AI service status
        debug_info.update(self.ai_service.get_ai_status())
        
        # Add user information if available
        if self.database_manager.is_connected():
            user = self.database_manager.get_user(user_id)
            if user:
                debug_info['user_found'] = True
                debug_info['user_data'] = {
                    'name': user['name'],
                    'pregnancy_week': user['pregnancy_week'],
                    'preferences': user['preferences']
                }
                
                # Test search
                query = f"pregnancy week {user['pregnancy_week']} daily advice nutrition exercise"
                context_chunks = self.search_similar_chunks(query)
                debug_info['search_results'] = len(context_chunks)
                
                if context_chunks:
                    debug_info['top_result'] = {
                        'text_preview': context_chunks[0][0][:200] + "..." if len(context_chunks[0][0]) > 200 else context_chunks[0][0],
                        'similarity_score': context_chunks[0][1]
                    }
                
                # Generate fallback recommendation
                fallback_rec = self.ai_service.get_fallback_recommendation(user)
                debug_info['fallback_recommendation'] = fallback_rec
                
            else:
                debug_info['user_found'] = False
        
        return debug_info
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file has allowed extension"""
        return self.pdf_processor.allowed_file(filename)
    
    def close_connections(self):
        """Close all database connections"""
        self.database_manager.close_connection()