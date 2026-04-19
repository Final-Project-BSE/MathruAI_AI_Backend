import json
import logging
from contextlib import closing
from typing import Dict, Any, List, Optional

import mysql.connector
from mysql.connector import Error

from risk_predition_model.config import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MySQL database connections and operations"""

    def __init__(self):
        self.connection = None
        cfg = get_config()
        self.db_name = cfg.MYSQL_DATABASE
        self.connect()
        self.setup_tables()

    def connect(self):
        """Connect to MySQL and create database if needed"""
        cfg = get_config()

        if not cfg.MYSQL_PASSWORD:
            raise ValueError("MYSQL_PASSWORD is empty or not loaded")

        try:
            with closing(mysql.connector.connect(
                host=cfg.MYSQL_HOST,
                user=cfg.MYSQL_USER,
                password=cfg.MYSQL_PASSWORD,
                port=cfg.MYSQL_PORT
            )) as temp_connection:
                with closing(temp_connection.cursor()) as cursor:
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                    logger.info(f"Database `{self.db_name}` ensured")

            self.connection = mysql.connector.connect(
                host=cfg.MYSQL_HOST,
                database=self.db_name,
                user=cfg.MYSQL_USER,
                password=cfg.MYSQL_PASSWORD,
                port=cfg.MYSQL_PORT,
                autocommit=False
            )
            logger.info(f"Connected to database `{self.db_name}`")

        except Error as e:
            logger.error(f"MySQL connection error: {e}")
            self.connection = None

    def _ensure_connection(self):
        if self.connection is None or not self.connection.is_connected():
            self.connect()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        self._ensure_connection()
        if not self.connection:
            return False

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                """, (self.db_name, table_name, column_name))
                result = cursor.fetchone()
                return bool(result and result[0] > 0)
        except Error as e:
            logger.error(f"Error checking column existence for {table_name}.{column_name}: {e}")
            return False

    def _ensure_predictions_midwife_column(self):
        if self._column_exists("predictions", "updated_by_midwife_id"):
            return

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    ALTER TABLE predictions
                    ADD COLUMN updated_by_midwife_id BIGINT NULL AFTER user_id
                """)
                cursor.execute("""
                    CREATE INDEX idx_predictions_updated_by_midwife
                    ON predictions (updated_by_midwife_id)
                """)
            self.connection.commit()
            logger.info("Added updated_by_midwife_id column to predictions table")
        except Error as e:
            logger.error(f"Error altering predictions table: {e}")
            self.connection.rollback()

    def setup_tables(self):
        """Create necessary tables"""
        self._ensure_connection()
        if not self.connection:
            logger.warning("No connection: Skipping table setup")
            return

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_email (email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        age FLOAT NOT NULL,
                        systolic_bp FLOAT NOT NULL,
                        diastolic_bp FLOAT NOT NULL,
                        blood_sugar FLOAT NOT NULL,
                        body_temp FLOAT NOT NULL,
                        bmi FLOAT NOT NULL,
                        heart_rate FLOAT NOT NULL,
                        previous_complications INT DEFAULT 0,
                        preexisting_diabetes INT DEFAULT 0,
                        gestational_diabetes INT DEFAULT 0,
                        mental_health INT DEFAULT 0,
                        risk_level VARCHAR(50),
                        risk_confidence FLOAT,
                        health_advice TEXT,
                        advice_confidence FLOAT,
                        risk_probabilities TEXT,
                        patient_profile TEXT,
                        alternative_advice TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_user_id (user_id),
                        INDEX idx_user_created (user_id, created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)

            self.connection.commit()
            self._ensure_predictions_midwife_column()
            logger.info("Database tables setup complete")
        except Error as e:
            logger.error(f"Error setting up tables: {e}")
            self.connection.rollback()

    def create_user(self, email: str) -> Optional[int]:
        """Create or get user by email"""
        self._ensure_connection()
        if not self.connection:
            return None

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                result = cursor.fetchone()

                if result:
                    return result[0]

                cursor.execute("INSERT INTO users (email) VALUES (%s)", (email,))
                self.connection.commit()
                user_id = cursor.lastrowid
                logger.info(f"Created user {user_id} with email {email}")
                return user_id
        except Error as e:
            logger.error(f"Error creating user: {e}")
            self.connection.rollback()
            return None

    def store_prediction(self, user_id: int, input_data: Dict[str, Any], prediction_result: Dict[str, Any]) -> Optional[int]:
        self._ensure_connection()
        if not self.connection:
            return None

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    INSERT INTO predictions
                    (user_id, updated_by_midwife_id, age, systolic_bp, diastolic_bp, blood_sugar, body_temp,
                     bmi, heart_rate, previous_complications, preexisting_diabetes,
                     gestational_diabetes, mental_health, risk_level, risk_confidence,
                     health_advice, advice_confidence, risk_probabilities, patient_profile,
                     alternative_advice)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    None,
                    float(input_data.get("Age", 0)),
                    float(input_data.get("SystolicBP", 0)),
                    float(input_data.get("DiastolicBP", 0)),
                    float(input_data.get("BS", 0)),
                    float(input_data.get("BodyTemp", 0)),
                    float(input_data.get("BMI", 0)),
                    float(input_data.get("HeartRate", 0)),
                    int(input_data.get("PreviousComplications", 0)),
                    int(input_data.get("PreexistingDiabetes", 0)),
                    int(input_data.get("GestationalDiabetes", 0)),
                    int(input_data.get("MentalHealth", 0)),
                    prediction_result.get("risk_level"),
                    float(prediction_result.get("risk_confidence", 0.0)),
                    prediction_result.get("health_advice"),
                    float(prediction_result.get("advice_confidence", 0.0)),
                    json.dumps(prediction_result.get("risk_probabilities", {})),
                    json.dumps(prediction_result.get("input_summary", {})),
                    json.dumps(prediction_result.get("alternative_advice", []))
                ))
                self.connection.commit()
                prediction_id = cursor.lastrowid
                logger.info(f"Stored prediction {prediction_id} for user {user_id}")
                return prediction_id
        except Error as e:
            logger.error(f"Error storing prediction: {e}")
            self.connection.rollback()
            return None

    def update_prediction(
        self,
        user_id: int,
        prediction_id: int,
        input_data: Dict[str, Any],
        prediction_result: Dict[str, Any],
        updated_by_midwife_id: Optional[int] = None
    ) -> bool:
        self._ensure_connection()
        if not self.connection:
            return False

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    UPDATE predictions
                    SET age = %s,
                        updated_by_midwife_id = %s,
                        systolic_bp = %s,
                        diastolic_bp = %s,
                        blood_sugar = %s,
                        body_temp = %s,
                        bmi = %s,
                        heart_rate = %s,
                        previous_complications = %s,
                        preexisting_diabetes = %s,
                        gestational_diabetes = %s,
                        mental_health = %s,
                        risk_level = %s,
                        risk_confidence = %s,
                        health_advice = %s,
                        advice_confidence = %s,
                        risk_probabilities = %s,
                        patient_profile = %s,
                        alternative_advice = %s
                    WHERE id = %s AND user_id = %s
                """, (
                    float(input_data.get("Age", 0)),
                    updated_by_midwife_id,
                    float(input_data.get("SystolicBP", 0)),
                    float(input_data.get("DiastolicBP", 0)),
                    float(input_data.get("BS", 0)),
                    float(input_data.get("BodyTemp", 0)),
                    float(input_data.get("BMI", 0)),
                    float(input_data.get("HeartRate", 0)),
                    int(input_data.get("PreviousComplications", 0)),
                    int(input_data.get("PreexistingDiabetes", 0)),
                    int(input_data.get("GestationalDiabetes", 0)),
                    int(input_data.get("MentalHealth", 0)),
                    prediction_result.get("risk_level"),
                    float(prediction_result.get("risk_confidence", 0.0)),
                    prediction_result.get("health_advice"),
                    float(prediction_result.get("advice_confidence", 0.0)),
                    json.dumps(prediction_result.get("risk_probabilities", {})),
                    json.dumps(prediction_result.get("input_summary", {})),
                    json.dumps(prediction_result.get("alternative_advice", [])),
                    prediction_id,
                    user_id
                ))
                self.connection.commit()
                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"Updated prediction {prediction_id}")
                return updated
        except Error as e:
            logger.error(f"Error updating prediction: {e}")
            self.connection.rollback()
            return False

    def get_prediction(self, prediction_id: int, user_id: int) -> Optional[Dict]:
        self._ensure_connection()
        if not self.connection:
            return None

        try:
            with closing(self.connection.cursor(dictionary=True)) as cursor:
                cursor.execute(
                    "SELECT * FROM predictions WHERE id = %s AND user_id = %s",
                    (prediction_id, user_id)
                )
                result = cursor.fetchone()
                return self._format_prediction(result) if result else None
        except Error as e:
            logger.error(f"Error getting prediction: {e}")
            return None

    def get_latest_prediction(self, user_id: int) -> Optional[Dict]:
        self._ensure_connection()
        if not self.connection:
            return None

        try:
            with closing(self.connection.cursor(dictionary=True)) as cursor:
                cursor.execute("""
                    SELECT * FROM predictions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT 1
                """, (user_id,))
                result = cursor.fetchone()
                return self._format_prediction(result) if result else None
        except Error as e:
            logger.error(f"Error getting latest prediction: {e}")
            return None

    def get_user_predictions(self, user_id: int, limit: int = 10) -> List[Dict]:
        self._ensure_connection()
        if not self.connection:
            return []

        try:
            with closing(self.connection.cursor(dictionary=True)) as cursor:
                cursor.execute("""
                    SELECT * FROM predictions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                results = cursor.fetchall()
                return [self._format_prediction(r) for r in results]
        except Error as e:
            logger.error(f"Error getting predictions: {e}")
            return []

    def has_patient_prediction(self, patient_id: int) -> bool:
        self._ensure_connection()
        if not self.connection:
            return False

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute(
                    "SELECT 1 FROM predictions WHERE user_id = %s LIMIT 1",
                    (patient_id,)
                )
                return cursor.fetchone() is not None
        except Error as e:
            logger.error(f"Error checking patient predictions: {e}")
            return False

    def is_patient_managed_by_midwife(self, patient_id: int, midwife_id: int) -> bool:
        self._ensure_connection()
        if not self.connection:
            return False

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute("""
                    SELECT 1
                    FROM predictions
                    WHERE user_id = %s
                      AND updated_by_midwife_id = %s
                    LIMIT 1
                """, (patient_id, midwife_id))
                return cursor.fetchone() is not None
        except Error as e:
            logger.error(f"Error checking patient-midwife management relationship: {e}")
            return False

    def delete_prediction(self, prediction_id: int, user_id: int) -> bool:
        self._ensure_connection()
        if not self.connection:
            return False

        try:
            with closing(self.connection.cursor()) as cursor:
                cursor.execute(
                    "DELETE FROM predictions WHERE id = %s AND user_id = %s",
                    (prediction_id, user_id)
                )
                self.connection.commit()
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted prediction {prediction_id}")
                return deleted
        except Error as e:
            logger.error(f"Error deleting prediction: {e}")
            self.connection.rollback()
            return False

    @staticmethod
    def _safe_json_loads(value, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return default

    def _format_prediction(self, raw_data: Dict) -> Dict:
        return {
            "id": raw_data["id"],
            "user_id": raw_data["user_id"],
            "updated_by_midwife_id": raw_data.get("updated_by_midwife_id"),
            "vitals": {
                "Age": raw_data["age"],
                "SystolicBP": raw_data["systolic_bp"],
                "DiastolicBP": raw_data["diastolic_bp"],
                "BS": raw_data["blood_sugar"],
                "BodyTemp": raw_data["body_temp"],
                "BMI": raw_data["bmi"],
                "HeartRate": raw_data["heart_rate"],
                "PreviousComplications": raw_data["previous_complications"],
                "PreexistingDiabetes": raw_data["preexisting_diabetes"],
                "GestationalDiabetes": raw_data["gestational_diabetes"],
                "MentalHealth": raw_data["mental_health"]
            },
            "prediction": {
                "risk_level": raw_data["risk_level"],
                "risk_confidence": raw_data["risk_confidence"],
                "health_advice": raw_data["health_advice"],
                "advice_confidence": raw_data["advice_confidence"],
                "risk_probabilities": self._safe_json_loads(raw_data.get("risk_probabilities"), {}),
                "patient_profile": self._safe_json_loads(raw_data.get("patient_profile"), {}),
                "alternative_advice": self._safe_json_loads(raw_data.get("alternative_advice"), [])
            },
            "created_at": raw_data["created_at"].isoformat() if raw_data.get("created_at") else None,
            "updated_at": raw_data["updated_at"].isoformat() if raw_data.get("updated_at") else None
        }

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")

    def __del__(self):
        self.close()


_db_manager = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
