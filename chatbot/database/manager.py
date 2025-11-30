"""
this is example manager.py
"""
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
import hashlib
from typing import List, Dict, Optional
import logging

from chatbot.config.settings import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections"""
    
    def __init__(self):
        """Initialize database manager."""
        self.connection = None
        self.db_name = DatabaseConfig.DATABASE
        self.connect()
        self.setup_tables()

    def connect(self):
        """Connect to MySQL server and create database if it doesn't exist."""
        try:
            # First connect without database to create it if needed
            temp_connection = mysql.connector.connect(
                host=DatabaseConfig.HOST,
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD,
                port=DatabaseConfig.PORT
            )
            logger.info("Connected to MySQL server")

            cursor = temp_connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`")
            logger.info(f"Database `{self.db_name}` ensured")

            cursor.close()
            temp_connection.close()

            # Now connect to the specific database
            self.connection = mysql.connector.connect(
                host=DatabaseConfig.HOST,
                database=self.db_name,
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD,
                port=DatabaseConfig.PORT
            )
            logger.info(f"Connected to MySQL database `{self.db_name}`")

        except Error as e:
            logger.error(f"MySQL connection error: {e}")
            self.connection = None

    def setup_tables(self):
        """Create necessary tables with user support."""
        if not self.connection:
            logger.warning("No connection: Skipping table setup")
            return
        
        try:
            cursor = self.connection.cursor()
            
            # Create document_chunks table (unchanged)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    chunk_text LONGTEXT NOT NULL,
                    source_file VARCHAR(255),
                    chunk_index INT,
                    chunk_size INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    embedding_vector_id INT,
                    metadata JSON,
                    chunk_hash VARCHAR(64),
                    INDEX idx_source_file (source_file),
                    INDEX idx_chunk_index (chunk_index),
                    INDEX idx_embedding_id (embedding_vector_id),
                    INDEX idx_chunk_hash (chunk_hash)
                )
            """)
            
            # Create search_logs table with user tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(50),
                    query TEXT NOT NULL,
                    response LONGTEXT,
                    relevant_chunks_count INT,
                    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    similarity_threshold FLOAT,
                    top_k INT,
                    response_time_ms INT,
                    context_tokens INT,
                    INDEX idx_timestamp (search_timestamp),
                    INDEX idx_user_id (user_id)
                )
            """)

            # Create chat_sessions table with user support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    session_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    message_count INT DEFAULT 0,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_updated_at (updated_at),
                    INDEX idx_is_active (is_active)
                )
            """)
            
            # Create chat_messages table with user support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id INT NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    response LONGTEXT,
                    message_type ENUM('user', 'assistant') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INT,
                    context_chunks_count INT,
                    similarity_threshold FLOAT,
                    top_k INT,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_id (session_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_message_type (message_type)
                )
            """)
            
            # Add user_id column to existing tables if not exists
            try:
                cursor.execute("ALTER TABLE chat_sessions ADD COLUMN user_id VARCHAR(50) NOT NULL AFTER id")
                cursor.execute("CREATE INDEX idx_user_id ON chat_sessions(user_id)")
                logger.info("Added user_id column to chat_sessions")
            except Error:
                pass  # Column probably already exists
            
            try:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN user_id VARCHAR(50) NOT NULL AFTER session_id")
                cursor.execute("CREATE INDEX idx_user_id ON chat_messages(user_id)")
                logger.info("Added user_id column to chat_messages")
            except Error:
                pass  # Column probably already exists
            
            self.connection.commit()
            logger.info("Database tables setup complete with user support")
            
        except Error as e:
            logger.error(f"Error setting up tables: {e}")

    def create_chat_session(self, user_id: str, session_name: str = None) -> int:
        """
        Create a new chat session for a specific user.
        
        Args:
            user_id (str): ID of the user
            session_name (str, optional): Name for the session
            
        Returns:
            int: Session ID or -1 if error
        """
        if not self.connection:
            return -1
        
        if not session_name:
            session_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s)
            """, (user_id, session_name))
            
            self.connection.commit()
            session_id = cursor.lastrowid
            logger.info(f"Created chat session: {session_id} for user: {user_id}")
            return session_id
            
        except Error as e:
            logger.error(f"Error creating chat session: {e}")
            return -1

    def store_chunk(self, chunk_text: str, source_file: str, chunk_index: int, 
                   embedding_vector_id: int, metadata: dict = None) -> int:
        """
        Store a document chunk with metadata and size tracking.
        
        Args:
            chunk_text (str): The text content of the chunk
            source_file (str): Source file name
            chunk_index (int): Index of the chunk in the source
            embedding_vector_id (int): ID of the embedding vector
            metadata (dict, optional): Additional metadata
            
        Returns:
            int: ID of stored chunk or -1 if error
        """
        if not self.connection:
            return -1
        
        try:
            # Calculate chunk hash for deduplication
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()
            chunk_size = len(chunk_text)
            
            cursor = self.connection.cursor()
            
            # Check if chunk already exists
            cursor.execute("""
                SELECT id FROM document_chunks WHERE chunk_hash = %s
            """, (chunk_hash,))
            
            if cursor.fetchone():
                logger.debug(f"Chunk already exists (hash: {chunk_hash[:8]}...)")
                return -1
            
            cursor.execute("""
                INSERT INTO document_chunks 
                (chunk_text, source_file, chunk_index, chunk_size, embedding_vector_id, metadata, chunk_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (chunk_text, source_file, chunk_index, chunk_size, embedding_vector_id, 
                  json.dumps(metadata) if metadata else None, chunk_hash))
            
            self.connection.commit()
            chunk_id = cursor.lastrowid
            logger.debug(f"Stored chunk {chunk_id} ({chunk_size} chars)")
            return chunk_id
            
        except Error as e:
            logger.error(f"Error storing chunk: {e}")
            return -1

    def get_user_chat_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        Get list of chat sessions for a specific user.
        
        Args:
            user_id (str): ID of the user
            limit (int): Maximum number of sessions to return
            
        Returns:
            List[Dict]: List of chat session data for the user
        """
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, session_name, created_at, updated_at, message_count
                FROM chat_sessions 
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY updated_at DESC 
                LIMIT %s
            """, (user_id, limit))
            
            sessions = cursor.fetchall()
            
            # Convert datetime objects to strings for JSON serialization
            for session in sessions:
                session['created_at'] = session['created_at'].isoformat()
                session['updated_at'] = session['updated_at'].isoformat()
            
            return sessions
            
        except Error as e:
            logger.error(f"Error getting user chat sessions: {e}")
            return []

    def get_session_owner(self, session_id: int) -> Optional[str]:
        """
        Get the owner (user_id) of a chat session.
        
        Args:
            session_id (int): ID of the chat session
            
        Returns:
            str: User ID of the session owner, or None if not found
        """
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT user_id FROM chat_sessions WHERE id = %s AND is_active = TRUE
            """, (session_id,))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Error as e:
            logger.error(f"Error getting session owner: {e}")
            return None

    def get_user_chat_messages(self, user_id: str, session_id: int) -> List[Dict]:
        """
        Get all messages for a user's chat session.
        
        Args:
            user_id (str): ID of the user
            session_id (int): ID of the chat session
            
        Returns:
            List[Dict]: List of chat messages for the user
        """
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, message, response, message_type, created_at, 
                       response_time_ms, context_chunks_count
                FROM chat_messages 
                WHERE session_id = %s AND user_id = %s 
                ORDER BY created_at ASC
            """, (session_id, user_id))
            
            messages = cursor.fetchall()
            
            # Convert datetime objects to strings
            for message in messages:
                message['created_at'] = message['created_at'].isoformat()
            
            return messages
            
        except Error as e:
            logger.error(f"Error getting user chat messages: {e}")
            return []

    def store_chat_message(self, session_id: int, user_id: str, message: str, 
                          response: str = None, message_type: str = 'user', 
                          response_time_ms: int = None, context_chunks_count: int = None, 
                          similarity_threshold: float = None, top_k: int = None) -> int:
        """
        Store a chat message for a specific user.
        
        Args:
            session_id (int): ID of the chat session
            user_id (str): ID of the user
            message (str): The message text
            response (str, optional): The response text
            message_type (str): Type of message ('user' or 'assistant')
            response_time_ms (int, optional): Response time in milliseconds
            context_chunks_count (int, optional): Number of context chunks used
            similarity_threshold (float, optional): Similarity threshold used
            top_k (int, optional): Top-k value used
            
        Returns:
            int: Message ID or -1 if error
        """
        if not self.connection:
            return -1
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO chat_messages 
                (session_id, user_id, message, response, message_type, response_time_ms, 
                 context_chunks_count, similarity_threshold, top_k)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session_id, user_id, message, response, message_type, response_time_ms, 
                  context_chunks_count, similarity_threshold, top_k))
            
            # Update session message count and timestamp (only for the correct user)
            cursor.execute("""
                UPDATE chat_sessions 
                SET message_count = message_count + 1, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """, (session_id, user_id))
            
            self.connection.commit()
            message_id = cursor.lastrowid
            return message_id
            
        except Error as e:
            logger.error(f"Error storing user chat message: {e}")
            return -1

    def delete_user_chat_session(self, session_id: int, user_id: str) -> bool:
        """
        Delete a user's chat session (soft delete).
        
        Args:
            session_id (int): ID of the session to delete
            user_id (str): ID of the user (for security)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE chat_sessions 
                SET is_active = FALSE 
                WHERE id = %s AND user_id = %s
            """, (session_id, user_id))
            
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Error as e:
            logger.error(f"Error deleting user chat session: {e}")
            return False

    def get_user_statistics(self, user_id: str, days: int = 7) -> Dict:
        """
        Get chat statistics for a specific user.
        
        Args:
            user_id (str): ID of the user
            days (int): Number of days to look back
            
        Returns:
            Dict: User chat statistics
        """
        if not self.connection:
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Get user's chat statistics
            cursor.execute("""
                SELECT COUNT(*) as session_count,
                       SUM(message_count) as total_messages
                FROM chat_sessions 
                WHERE user_id = %s AND is_active = TRUE
                  AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (user_id, days))
            
            session_stats = cursor.fetchone()
            
            # Get average response time for user
            cursor.execute("""
                SELECT AVG(response_time_ms)
                FROM chat_messages 
                WHERE user_id = %s AND response_time_ms IS NOT NULL
                  AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (user_id, days))
            
            avg_response_time = cursor.fetchone()[0]
            
            return {
                "user_id": user_id,
                "session_count": session_stats[0] or 0,
                "total_messages": session_stats[1] or 0,
                "avg_response_time_ms": int(avg_response_time) if avg_response_time else 0,
                "period_days": days
            }
            
        except Error as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    def log_search(self, query: str, response: str, chunks_count: int, 
                   similarity_threshold: float, top_k: int, user_id: str = None,
                   response_time_ms: int = None, context_tokens: int = None):
        """
        Log search query and response with user tracking.
        """
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO search_logs 
                (user_id, query, response, relevant_chunks_count, similarity_threshold, 
                 top_k, response_time_ms, context_tokens)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, query, response, chunks_count, similarity_threshold, 
                  top_k, response_time_ms, context_tokens))
            
            self.connection.commit()
            
        except Error as e:
            logger.error(f"Error logging search: {e}")

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close()