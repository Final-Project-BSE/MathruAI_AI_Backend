import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.init_database()
    
    def init_database(self):
        """Initialize MySQL database for user preferences and recommendations history"""
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            
            cursor = self.connection.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    pregnancy_week INT,
                    preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create recommendations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    recommendation TEXT,
                    recommendation_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            self.connection.commit()
            logger.info("Database initialized successfully")
            
        except Error as e:
            logger.error(f"Database initialization error: {e}")
            self.connection = None
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.connection is not None
    
    def register_user(self, name: str, pregnancy_week: int, preferences: str = '') -> int:
        """Register a new user"""
        if not self.connection:
            raise Exception("Database connection not available")
        
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO users (name, pregnancy_week, preferences) VALUES (%s, %s, %s)",
            (name, pregnancy_week, preferences)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    
    def update_user(self, user_id: int, name: str = None, pregnancy_week: int = None, preferences: str = None) -> bool:
        """Update user information"""
        if not self.connection:
            return False
        
        # Get current user data
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Update fields
        name = name if name is not None else user['name']
        pregnancy_week = pregnancy_week if pregnancy_week is not None else user['pregnancy_week']
        preferences = preferences if preferences is not None else user['preferences']
        
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE users SET name = %s, pregnancy_week = %s, preferences = %s WHERE id = %s",
            (name, pregnancy_week, preferences, user_id)
        )
        self.connection.commit()
        return True
    
    def save_recommendation(self, user_id: int, recommendation: str, date: datetime.date = None) -> bool:
        """Save a recommendation for a user"""
        if not self.connection:
            return False
        
        if date is None:
            date = datetime.now().date()
        
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO recommendations (user_id, recommendation, recommendation_date) VALUES (%s, %s, %s)",
            (user_id, recommendation, date)
        )
        self.connection.commit()
        return True
    
    def get_recommendation_for_date(self, user_id: int, date: datetime.date) -> Optional[str]:
        """Get recommendation for specific date"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT recommendation FROM recommendations WHERE user_id = %s AND recommendation_date = %s",
            (user_id, date)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_recommendation_history(self, user_id: int, limit: int = 30) -> List[Dict]:
        """Get recommendation history for user"""
        if not self.connection:
            return []
        
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT recommendation, recommendation_date, created_at 
               FROM recommendations 
               WHERE user_id = %s 
               ORDER BY recommendation_date DESC 
               LIMIT %s""",
            (user_id, limit)
        )
        return cursor.fetchall()
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.connection:
            return {}
        
        cursor = self.connection.cursor()
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # Count recommendations
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        # Count today's recommendations
        today = datetime.now().date()
        cursor.execute("SELECT COUNT(*) FROM recommendations WHERE recommendation_date = %s", (today,))
        todays_recommendations = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_recommendations': total_recommendations,
            'todays_recommendations': todays_recommendations
        }
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None