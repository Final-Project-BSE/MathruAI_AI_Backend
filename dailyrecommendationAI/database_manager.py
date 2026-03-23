import mysql.connector
from mysql.connector import Error
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
            autocommit=False
        )

    def init_database(self):
        """Initialize MySQL database tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

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

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database initialized successfully")

        except Error as e:
            logger.error(f"Database initialization error: {e}")

    def upsert_checklist_items(self, user_id: int, rec_date: date, items: List[Dict]) -> bool:
        """
        items: [{id: str, text: str, completed: bool}]
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                INSERT INTO recommendation_checklist (user_id, recommendation_date, item_id, item_text, completed)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    item_text = VALUES(item_text),
                    completed = VALUES(completed),
                    updated_at = CURRENT_TIMESTAMP
            """

            values = []
            for it in items:
                item_id = str(it.get("id") or "").strip()
                item_text = str(it.get("text") or "").strip()
                completed = bool(it.get("completed", False))
                if not item_id or not item_text:
                    continue
                values.append((user_id, rec_date, item_id, item_text, completed))

            if values:
                cursor.executemany(query, values)

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Error as e:
            logger.error(f"upsert_checklist_items error: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    # fetch checklist items for a day
    def get_checklist_items(self, user_id: int, rec_date: date) -> List[Dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT item_id, item_text, completed, updated_at, created_at
                FROM recommendation_checklist
                WHERE user_id = %s AND recommendation_date = %s
                ORDER BY created_at ASC
            """, (user_id, rec_date))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows or []

        except Error as e:
            logger.error(f"get_checklist_items error: {e}")
            return []

    # include checklist in history
    def get_recommendation_history_with_checklist(self, user_id: int, limit: int = 30) -> List[Dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT recommendation, recommendation_date, created_at
                FROM recommendations
                WHERE user_id = %s
                ORDER BY recommendation_date DESC
                LIMIT %s
            """, (user_id, limit))

            recs = cursor.fetchall() or []
            # fetch checklists for those dates
            dates = [r["recommendation_date"] for r in recs if r.get("recommendation_date")]

            checklist_by_date = {}
            if dates:
                placeholders = ",".join(["%s"] * len(dates))
                cursor.execute(f"""
                    SELECT recommendation_date, item_id, item_text, completed
                    FROM recommendation_checklist
                    WHERE user_id = %s AND recommendation_date IN ({placeholders})
                    ORDER BY recommendation_date DESC, created_at ASC
                """, tuple([user_id] + dates))

                rows = cursor.fetchall() or []
                for row in rows:
                    d = row["recommendation_date"].isoformat()
                    checklist_by_date.setdefault(d, []).append({
                        "id": row["item_id"],
                        "text": row["item_text"],
                        "completed": bool(row["completed"]),
                    })

            cursor.close()
            conn.close()

            out = []
            for r in recs:
                d = r["recommendation_date"].isoformat() if r.get("recommendation_date") else None
                out.append({
                    "date": d,
                    "recommendation": r.get("recommendation"),
                    "created_at": r.get("created_at").isoformat() if r.get("created_at") else None,
                    "checklist": checklist_by_date.get(d, [])
                })
            return out

        except Error as e:
            logger.error(f"get_recommendation_history_with_checklist error: {e}")
            return []
        
    def delete_checklist_for_date(self, user_id: int, rec_date: date) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM recommendation_checklist WHERE user_id = %s AND recommendation_date = %s",
                (user_id, rec_date)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            logger.error(f"delete_checklist_for_date error: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
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
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Error as e:
            logger.error(f"get_user error: {e}")
            return None

    def create_or_update_user_data(self, user_id: int, pregnancy_week: int = None, preferences: str = None) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if user exists
            user = self.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found in users table")
                cursor.close()
                conn.close()
                return False

            cursor.execute(
                "SELECT id FROM user_data WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                (user_id,)
            )
            existing = cursor.fetchone()

            if existing:
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
            else:
                cursor.execute(
                    "INSERT INTO user_data (user_id, pregnancy_week, preferences) VALUES (%s, %s, %s)",
                    (user_id, pregnancy_week, preferences)
                )

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Error as e:
            logger.error(f"Error creating/updating user data: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
            return False

    def get_latest_user_data(self, user_id: int) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT user_id, pregnancy_week, preferences, updated_at, created_at
                FROM user_data
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))

            user_data = cursor.fetchone()
            cursor.close()
            conn.close()

            if user_data:
                return user_data

            # fallback to users table
            user = self.get_user(user_id)
            if user:
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
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT pregnancy_week, preferences, updated_at, created_at
                FROM user_data
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user_id, limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        except Error as e:
            logger.error(f"get_user_data_history error: {e}")
            return []

    def save_recommendation(self, user_id: int, recommendation: str, date=None) -> bool:
        if date is None:
            date = datetime.now().date()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO recommendations (user_id, recommendation, recommendation_date)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    recommendation = VALUES(recommendation),
                    created_at = CURRENT_TIMESTAMP
            """, (user_id, recommendation, date))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Error as e:
            logger.error(f"Error saving recommendation: {e}")
            return False

    def get_recommendation_for_date(self, user_id: int, date) -> Optional[str]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT recommendation FROM recommendations WHERE user_id = %s AND recommendation_date = %s ORDER BY created_at DESC LIMIT 1",
                (user_id, date)
            )
            row = cursor.fetchone()

            cursor.close()
            conn.close()
            return row[0] if row else None

        except Error as e:
            logger.error(f"get_recommendation_for_date error: {e}")
            return None

    def delete_recommendation_for_date(self, user_id: int, date) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM recommendations WHERE user_id = %s AND recommendation_date = %s",
                (user_id, date)
            )

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Error as e:
            logger.error(f"Error deleting recommendation: {e}")
            return False

    def get_recommendation_history(self, user_id: int, limit: int = 30) -> List[Dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT recommendation, recommendation_date, created_at
                FROM recommendations
                WHERE user_id = %s
                ORDER BY recommendation_date DESC
                LIMIT %s
            """, (user_id, limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        except Error as e:
            logger.error(f"get_recommendation_history error: {e}")
            return []

    def get_stats(self) -> Dict:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM user_data")
            total_user_data = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM recommendations")
            total_recommendations = cursor.fetchone()[0]

            today = datetime.now().date()
            cursor.execute("SELECT COUNT(*) FROM recommendations WHERE recommendation_date = %s", (today,))
            todays_recommendations = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                'total_users': total_users,
                'total_user_data_records': total_user_data,
                'total_recommendations': total_recommendations,
                'todays_recommendations': todays_recommendations
            }
        except Error as e:
            logger.error(f"get_stats error: {e}")
            return {}
        
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, first_name, email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return user
        except Error as e:
            logger.error(f"get_user_by_email error: {e}")
            return None