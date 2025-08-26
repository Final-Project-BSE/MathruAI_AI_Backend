"""
Database manager for storing and retrieving RAG system data.
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
    """Manages database connections and operations for the RAG system."""
    
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
        """Create necessary tables with proper field sizes."""
        if not self.connection:
            logger.warning("No connection: Skipping table setup")
            return
        
        try:
            cursor = self.connection.cursor()
            
            # Create document_chunks table
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
            
            # Create search_logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    query TEXT NOT NULL,
                    response LONGTEXT,
                    relevant_chunks_count INT,
                    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    similarity_threshold FLOAT,
                    top_k INT,
                    response_time_ms INT,
                    context_tokens INT,
                    INDEX idx_timestamp (search_timestamp)
                )
            """)

            # Create chat_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    message_count INT DEFAULT 0,
                    INDEX idx_created_at (created_at),
                    INDEX idx_updated_at (updated_at),
                    INDEX idx_is_active (is_active)
                )
            """)
            
            # Create chat_messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id INT NOT NULL,
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
                    INDEX idx_created_at (created_at),
                    INDEX idx_message_type (message_type)
                )
            """)
            
            self.connection.commit()
            logger.info("Database tables setup complete")
            
        except Error as e:
            logger.error(f"Error setting up tables: {e}")

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
    
    def log_search(self, query: str, response: str, chunks_count: int, 
                   similarity_threshold: float, top_k: int, response_time_ms: int = None, 
                   context_tokens: int = None):
        """
        Log search query and response with performance metrics.
        
        Args:
            query (str): Search query
            response (str): Generated response
            chunks_count (int): Number of relevant chunks found
            similarity_threshold (float): Similarity threshold used
            top_k (int): Number of top results retrieved
            response_time_ms (int, optional): Response time in milliseconds
            context_tokens (int, optional): Number of context tokens
        """
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO search_logs 
                (query, response, relevant_chunks_count, similarity_threshold, top_k, response_time_ms, context_tokens)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (query, response, chunks_count, similarity_threshold, top_k, response_time_ms, context_tokens))
            
            self.connection.commit()
            
        except Error as e:
            logger.error(f"Error logging search: {e}")
    
    def get_chunk_stats(self) -> Dict:
        """
        Get comprehensive chunk statistics.
        
        Returns:
            Dict: Statistics about stored chunks
        """
        if not self.connection:
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Basic stats
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            total_chunks = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(chunk_size), MIN(chunk_size), MAX(chunk_size) FROM document_chunks")
            size_stats = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(DISTINCT source_file) FROM document_chunks")
            unique_sources = cursor.fetchone()[0]
            
            return {
                "total_chunks": total_chunks,
                "unique_sources": unique_sources,
                "avg_chunk_size": int(size_stats[0]) if size_stats[0] else 0,
                "min_chunk_size": size_stats[1] or 0,
                "max_chunk_size": size_stats[2] or 0
            }
            
        except Error as e:
            logger.error(f"Error getting chunk stats: {e}")
            return {}
    
    def create_chat_session(self, session_name: str = None) -> int:
        """
        Create a new chat session.
        
        Args:
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
                INSERT INTO chat_sessions (session_name) VALUES (%s)
            """, (session_name,))
            
            self.connection.commit()
            session_id = cursor.lastrowid
            logger.info(f"Created chat session: {session_id} - {session_name}")
            return session_id
            
        except Error as e:
            logger.error(f"Error creating chat session: {e}")
            return -1

    def get_chat_sessions(self, limit: int = 50) -> List[Dict]:
        """
        Get list of chat sessions.
        
        Args:
            limit (int): Maximum number of sessions to return
            
        Returns:
            List[Dict]: List of chat session data
        """
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, session_name, created_at, updated_at, message_count
                FROM chat_sessions 
                WHERE is_active = TRUE
                ORDER BY updated_at DESC 
                LIMIT %s
            """, (limit,))
            
            sessions = cursor.fetchall()
            
            # Convert datetime objects to strings for JSON serialization
            for session in sessions:
                session['created_at'] = session['created_at'].isoformat()
                session['updated_at'] = session['updated_at'].isoformat()
            
            return sessions
            
        except Error as e:
            logger.error(f"Error getting chat sessions: {e}")
            return []

    def get_chat_messages(self, session_id: int) -> List[Dict]:
        """
        Get all messages for a chat session.
        
        Args:
            session_id (int): ID of the chat session
            
        Returns:
            List[Dict]: List of chat messages
        """
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, message, response, message_type, created_at, 
                       response_time_ms, context_chunks_count
                FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = cursor.fetchall()
            
            # Convert datetime objects to strings
            for message in messages:
                message['created_at'] = message['created_at'].isoformat()
            
            return messages
            
        except Error as e:
            logger.error(f"Error getting chat messages: {e}")
            return []

    def store_chat_message(self, session_id: int, message: str, response: str = None, 
                          message_type: str = 'user', response_time_ms: int = None, 
                          context_chunks_count: int = None, similarity_threshold: float = None, 
                          top_k: int = None) -> int:
        """
        Store a chat message.
        
        Args:
            session_id (int): ID of the chat session
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
                (session_id, message, response, message_type, response_time_ms, 
                 context_chunks_count, similarity_threshold, top_k)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (session_id, message, response, message_type, response_time_ms, 
                  context_chunks_count, similarity_threshold, top_k))
            
            # Update session message count and timestamp
            cursor.execute("""
                UPDATE chat_sessions 
                SET message_count = message_count + 1, updated_at = NOW()
                WHERE id = %s
            """, (session_id,))
            
            self.connection.commit()
            message_id = cursor.lastrowid
            return message_id
            
        except Error as e:
            logger.error(f"Error storing chat message: {e}")
            return -1

    def delete_chat_session(self, session_id: int) -> bool:
        """
        Delete a chat session (soft delete).
        
        Args:
            session_id (int): ID of the session to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE chat_sessions SET is_active = FALSE WHERE id = %s
            """, (session_id,))
            
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Error as e:
            logger.error(f"Error deleting chat session: {e}")
            return False

    def get_search_statistics(self, days: int = 7) -> Dict:
        """
        Get search statistics for the last N days.
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            Dict: Search statistics
        """
        if not self.connection:
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Get search count and average response time
            cursor.execute("""
                SELECT COUNT(*), AVG(response_time_ms), AVG(context_tokens)
                FROM search_logs 
                WHERE search_timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,))
            
            stats = cursor.fetchone()
            
            return {
                "search_count": stats[0] or 0,
                "avg_response_time_ms": int(stats[1]) if stats[1] else 0,
                "avg_context_tokens": int(stats[2]) if stats[2] else 0,
                "period_days": days
            }
            
        except Error as e:
            logger.error(f"Error getting search statistics: {e}")
            return {}

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close()