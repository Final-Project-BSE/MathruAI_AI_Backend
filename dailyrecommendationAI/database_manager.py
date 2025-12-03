import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.init_database()
    
    def init_database(self):
        """Initialize MySQL database for user data updates and recommendations history"""
        try:
            self.connection = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            
            cursor = self.connection.cursor()
            
            # Create user_data table (for updates) - users table already exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    pregnancy_week INT,
                    preferences TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_updated_at (updated_at)
                )
            """)
            
            # Create recommendations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    recommendation TEXT,
                    recommendation_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_date (user_id, recommendation_date)
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
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information from users table"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    
    def create_or_update_user_data(self, user_id: int, pregnancy_week: int = None, preferences: str = None) -> bool:
        """Create or update user data in user_data table"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Check if user exists in users table
            user = self.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found in users table")
                return False
            
            # Check if user_data record exists
            cursor.execute("SELECT id FROM user_data WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                update_fields = []
                update_values = []
                
                if pregnancy_week is not None:
                    update_fields.append("pregnancy_week = %s")
                    update_values.append(pregnancy_week)
                
                if preferences is not None:
                    update_fields.append("preferences = %s")
                    update_values.append(preferences)
                
                if update_fields:
                    update_values.append(user_id)
                    query = f"UPDATE user_data SET {', '.join(update_fields)} WHERE user_id = %s"
                    cursor.execute(query, tuple(update_values))
                    logger.info(f"Updated user_data for user_id {user_id}")
            else:
                # Insert new record
                cursor.execute(
                    "INSERT INTO user_data (user_id, pregnancy_week, preferences) VALUES (%s, %s, %s)",
                    (user_id, pregnancy_week, preferences)
                )
                logger.info(f"Created new user_data for user_id {user_id}")
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error creating/updating user data: {e}")
            self.connection.rollback()
            return False
    
    def get_latest_user_data(self, user_id: int) -> Optional[Dict]:
        """Get latest user data from user_data table, fallback to users table if not found"""
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Try to get from user_data table first
            cursor.execute("""
                SELECT user_id, pregnancy_week, preferences, updated_at, created_at 
                FROM user_data 
                WHERE user_id = %s 
                ORDER BY updated_at DESC 
                LIMIT 1
            """, (user_id,))
            
            user_data = cursor.fetchone()
            
            if user_data:
                logger.info(f"Retrieved user data from user_data table for user_id {user_id}")
                return user_data
            
            # Fallback to users table
            user = self.get_user(user_id)
            if user:
                logger.info(f"No user_data found, using data from users table for user_id {user_id}")
                return {
                    'user_id': user['id'],
                    'pregnancy_week': user.get('pregnancy_week'),
                    'preferences': user.get('preferences', ''),
                    'updated_at': user.get('created_at'),
                    'created_at': user.get('created_at')
                }
            
            return None
            
        except Error as e:
            logger.error(f"Error getting latest user data: {e}")
            return None
    
    def get_user_data_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get update history for user from user_data table"""
        if not self.connection:
            return []
        
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT pregnancy_week, preferences, updated_at, created_at 
            FROM user_data 
            WHERE user_id = %s 
            ORDER BY updated_at DESC 
            LIMIT %s
        """, (user_id, limit))
        
        return cursor.fetchall()
    
    def save_recommendation(self, user_id: int, recommendation: str, date: datetime.date = None) -> bool:
        """Save a recommendation for a user"""
        if not self.connection:
            return False
        
        if date is None:
            date = datetime.now().date()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO recommendations (user_id, recommendation, recommendation_date) VALUES (%s, %s, %s)",
                (user_id, recommendation, date)
            )
            self.connection.commit()
            logger.info(f"Saved recommendation for user_id {user_id}")
            return True
        except Error as e:
            logger.error(f"Error saving recommendation: {e}")
            return False
    
    def get_recommendation_for_date(self, user_id: int, date: datetime.date) -> Optional[str]:
        """Get recommendation for specific date"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT recommendation FROM recommendations WHERE user_id = %s AND recommendation_date = %s ORDER BY created_at DESC LIMIT 1",
            (user_id, date)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    def delete_recommendation_for_date(self, user_id: int, date: datetime.date) -> bool:
        """Delete recommendations for specific date (to allow regeneration)"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "DELETE FROM recommendations WHERE user_id = %s AND recommendation_date = %s",
                (user_id, date)
            )
            self.connection.commit()
            logger.info(f"Deleted recommendations for user_id {user_id} on date {date}")
            return True
        except Error as e:
            logger.error(f"Error deleting recommendation: {e}")
            return False
    
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
        
        # Count user data records
        cursor.execute("SELECT COUNT(*) FROM user_data")
        total_user_data = cursor.fetchone()[0]
        
        # Count recommendations
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        # Count today's recommendations
        today = datetime.now().date()
        cursor.execute("SELECT COUNT(*) FROM recommendations WHERE recommendation_date = %s", (today,))
        todays_recommendations = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_user_data_records': total_user_data,
            'total_recommendations': total_recommendations,
            'todays_recommendations': todays_recommendations
        }
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")