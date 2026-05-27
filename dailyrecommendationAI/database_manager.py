import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Dict, List
import logging

from dailyrecommendationAI.config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.init_database()

    def _get_connection(self):
        """Create and return a new MySQL connection."""
        return mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT,
            autocommit=False,
        )

    @contextmanager
    def _cursor(self, dictionary: bool = False):
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=dictionary)
            yield conn, cursor
            conn.commit()
        except Error:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def init_database(self):
        """Initialize MySQL database tables."""
        try:
            with self._cursor() as (_, cursor):
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

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recommendation_checklist (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        recommendation_date DATE NOT NULL,
                        item_id VARCHAR(64) NOT NULL,
                        item_text TEXT NOT NULL,
                        completed BOOLEAN NOT NULL DEFAULT FALSE,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE KEY uniq_user_date_item (user_id, recommendation_date, item_id),
                        INDEX idx_user_date (user_id, recommendation_date)
                    )
                """)
            logger.info('Database initialized successfully')
        except Error as e:
            logger.error('Database initialization error: %s', e)

    def upsert_checklist_items(self, user_id: int, rec_date: date, items: List[Dict]) -> bool:
        """Upsert checklist items for a recommendation date."""
        try:
            values = []
            for item in items:
                item_id = str(item.get('id') or '').strip()
                item_text = str(item.get('text') or '').strip()
                completed = bool(item.get('completed', False))
                if item_id and item_text:
                    values.append((user_id, rec_date, item_id, item_text, completed))

            if not values:
                return True

            with self._cursor() as (_, cursor):
                cursor.executemany(
                    """
                    INSERT INTO recommendation_checklist (user_id, recommendation_date, item_id, item_text, completed)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        item_text = VALUES(item_text),
                        completed = VALUES(completed),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    values,
                )
            return True
        except Error as e:
            logger.error('upsert_checklist_items error: %s', e)
            return False

    def get_checklist_items(self, user_id: int, rec_date: date) -> List[Dict]:
        """Fetch checklist items for a day."""
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute(
                    """
                    SELECT item_id, item_text, completed, updated_at, created_at
                    FROM recommendation_checklist
                    WHERE user_id = %s AND recommendation_date = %s
                    ORDER BY created_at ASC
                    """,
                    (user_id, rec_date),
                )
                return cursor.fetchall() or []
        except Error as e:
            logger.error('get_checklist_items error: %s', e)
            return []

    def get_recommendation_history_with_checklist(self, user_id: int, limit: int = 30) -> List[Dict]:
        """Get recommendation history including checklist items."""
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute(
                    """
                    SELECT recommendation, recommendation_date, created_at
                    FROM recommendations
                    WHERE user_id = %s
                    ORDER BY recommendation_date DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                recommendations = cursor.fetchall() or []

                dates = [rec['recommendation_date'] for rec in recommendations if rec.get('recommendation_date')]
                checklist_by_date = {}

                if dates:
                    placeholders = ','.join(['%s'] * len(dates))
                    cursor.execute(
                        f"""
                        SELECT recommendation_date, item_id, item_text, completed
                        FROM recommendation_checklist
                        WHERE user_id = %s AND recommendation_date IN ({placeholders})
                        ORDER BY recommendation_date DESC, created_at ASC
                        """,
                        tuple([user_id] + dates),
                    )
                    for row in cursor.fetchall() or []:
                        date_key = row['recommendation_date'].isoformat()
                        checklist_by_date.setdefault(date_key, []).append({
                            'id': row['item_id'],
                            'text': row['item_text'],
                            'completed': bool(row['completed']),
                        })

            output = []
            for rec in recommendations:
                date_key = rec['recommendation_date'].isoformat() if rec.get('recommendation_date') else None
                output.append({
                    'date': date_key,
                    'recommendation': rec.get('recommendation'),
                    'created_at': rec.get('created_at').isoformat() if rec.get('created_at') else None,
                    'checklist': checklist_by_date.get(date_key, []),
                })
            return output
        except Error as e:
            logger.error('get_recommendation_history_with_checklist error: %s', e)
            return []

    def delete_checklist_for_date(self, user_id: int, rec_date: date) -> bool:
        try:
            with self._cursor() as (_, cursor):
                cursor.execute(
                    'DELETE FROM recommendation_checklist WHERE user_id = %s AND recommendation_date = %s',
                    (user_id, rec_date),
                )
            return True
        except Error as e:
            logger.error('delete_checklist_for_date error: %s', e)
            return False

    def is_connected(self) -> bool:
        """Check DB connectivity by opening a quick test connection."""
        try:
            conn = self._get_connection()
            conn.close()
            return True
        except Error:
            return False

    def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                return cursor.fetchone()
        except Error as e:
            logger.error('get_user error: %s', e)
            return None

    def create_or_update_user_data(self, user_id: int, pregnancy_week: int = None, preferences: str = None) -> bool:
        try:
            user = self.get_user(user_id)
            if not user:
                logger.error('User %s not found in users table', user_id)
                return False

            with self._cursor() as (_, cursor):
                cursor.execute(
                    'SELECT id FROM user_data WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1',
                    (user_id,),
                )
                existing = cursor.fetchone()

                if existing:
                    update_fields = []
                    update_values = []

                    if pregnancy_week is not None:
                        update_fields.append('pregnancy_week = %s')
                        update_values.append(pregnancy_week)

                    if preferences is not None:
                        update_fields.append('preferences = %s')
                        update_values.append(preferences)

                    if update_fields:
                        update_values.append(user_id)
                        query = f"UPDATE user_data SET {', '.join(update_fields)} WHERE user_id = %s"
                        cursor.execute(query, tuple(update_values))
                else:
                    cursor.execute(
                        'INSERT INTO user_data (user_id, pregnancy_week, preferences) VALUES (%s, %s, %s)',
                        (user_id, pregnancy_week, preferences),
                    )
            return True
        except Error as e:
            logger.error('Error creating/updating user data: %s', e)
            return False

    def get_latest_user_data(self, user_id: int) -> Optional[Dict]:
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute(
                    """
                    SELECT user_id, pregnancy_week, preferences, updated_at, created_at
                    FROM user_data
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user_id,),
                )
                user_data = cursor.fetchone()

            if user_data:
                return user_data

            user = self.get_user(user_id)
            if user:
                return {
                    'user_id': user['id'],
                    'pregnancy_week': user.get('pregnancy_week'),
                    'preferences': user.get('preferences', ''),
                    'updated_at': user.get('created_at'),
                    'created_at': user.get('created_at'),
                }
            return None
        except Error as e:
            logger.error('Error getting latest user data: %s', e)
            return None

    def get_user_data_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute(
                    """
                    SELECT pregnancy_week, preferences, updated_at, created_at
                    FROM user_data
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                return cursor.fetchall() or []
        except Error as e:
            logger.error('get_user_data_history error: %s', e)
            return []

    def save_recommendation(self, user_id: int, recommendation: str, date_value=None) -> bool:
        if date_value is None:
            date_value = datetime.now().date()

        try:
            with self._cursor() as (_, cursor):
                cursor.execute(
                    """
                    INSERT INTO recommendations (user_id, recommendation, recommendation_date)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        recommendation = VALUES(recommendation),
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (user_id, recommendation, date_value),
                )
            return True
        except Error as e:
            logger.error('Error saving recommendation: %s', e)
            return False

    def get_recommendation_for_date(self, user_id: int, date_value) -> Optional[str]:
        try:
            with self._cursor() as (_, cursor):
                cursor.execute(
                    'SELECT recommendation FROM recommendations WHERE user_id = %s AND recommendation_date = %s ORDER BY created_at DESC LIMIT 1',
                    (user_id, date_value),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Error as e:
            logger.error('get_recommendation_for_date error: %s', e)
            return None

    def delete_recommendation_for_date(self, user_id: int, date_value) -> bool:
        try:
            with self._cursor() as (_, cursor):
                cursor.execute(
                    'DELETE FROM recommendations WHERE user_id = %s AND recommendation_date = %s',
                    (user_id, date_value),
                )
            return True
        except Error as e:
            logger.error('Error deleting recommendation: %s', e)
            return False

    def get_recommendation_history(self, user_id: int, limit: int = 30) -> List[Dict]:
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute(
                    """
                    SELECT recommendation, recommendation_date, created_at
                    FROM recommendations
                    WHERE user_id = %s
                    ORDER BY recommendation_date DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                return cursor.fetchall() or []
        except Error as e:
            logger.error('get_recommendation_history error: %s', e)
            return []

    def get_stats(self) -> Dict:
        try:
            with self._cursor() as (_, cursor):
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM user_data')
                total_user_data = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM recommendations')
                total_recommendations = cursor.fetchone()[0]

                today = datetime.now().date()
                cursor.execute('SELECT COUNT(*) FROM recommendations WHERE recommendation_date = %s', (today,))
                todays_recommendations = cursor.fetchone()[0]

            return {
                'total_users': total_users,
                'total_user_data_records': total_user_data,
                'total_recommendations': total_recommendations,
                'todays_recommendations': todays_recommendations,
            }
        except Error as e:
            logger.error('get_stats error: %s', e)
            return {}

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            with self._cursor(dictionary=True) as (_, cursor):
                cursor.execute('SELECT id, first_name, email FROM users WHERE email = %s', (email,))
                return cursor.fetchone()
        except Error as e:
            logger.error('get_user_by_email error: %s', e)
            return None
