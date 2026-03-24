"""
Combined main application entry point - MySQL with Auto Setup.
Refactored to remove duplication and keep existing functionality/route behavior.
"""

import logging
import os
import sys
import traceback
from contextlib import closing

from flask import Blueprint, Flask, jsonify
from flask_cors import CORS

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CHATBOT_LOG_DIR = os.path.join(PROJECT_ROOT, "chatbot", "logs")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging once."""
    os.makedirs(CHATBOT_LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Prevent duplicate handlers during reloads
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(os.path.join(CHATBOT_LOG_DIR, "app.log"))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


def get_env(name: str, default=None):
    return os.getenv(name, default)


def get_bool_env(name: str, default: str = "False") -> bool:
    return str(os.getenv(name, default)).strip().lower() == "true"


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def auto_setup_mysql() -> bool:
    """Automatically setup MySQL database."""
    try:
        import pymysql

        mysql_user = get_env("MYSQL_USER", "root")
        mysql_password = get_env("MYSQL_PASSWORD", "")
        mysql_host = get_env("MYSQL_HOST", "localhost")
        mysql_port = get_int_env("MYSQL_PORT", 3306)
        mysql_database = get_env("MYSQL_DATABASE", "mathruai_database")

        logger.info("Starting MySQL Database Setup")
        logger.info(
            "Host: %s:%s, Database: %s, User: %s",
            mysql_host,
            mysql_port,
            mysql_database,
            mysql_user,
        )

        # Connect to MySQL server and create database
        with closing(
            pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
            )
        ) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                logger.info("Connected to MySQL %s", version[0])

                cursor.execute(
                    f"""
                    CREATE DATABASE IF NOT EXISTS `{mysql_database}`
                    CHARACTER SET utf8mb4
                    COLLATE utf8mb4_unicode_ci
                    """
                )
                logger.info("Database '%s' ready", mysql_database)

        # Validate DB connectivity
        with closing(
            pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                database=mysql_database,
            )
        ) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT 1")

        return True

    except Exception as exc:
        logger.error("MySQL Error: %s", exc)
        logger.error(
            "Please check: MySQL server is running, credentials are correct, user has privileges"
        )
        return False


def configure_common_app_settings(app: Flask) -> None:
    """Apply common Flask config without changing external behavior."""
    app.config["SECRET_KEY"] = get_env("SECRET_KEY", "dev-key-change-in-production")
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    CORS(
        app,
        origins="*",
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


def register_rag_health_blueprint(app: Flask) -> None:
    """Register extra RAG health endpoint."""
    rag_extra_bp = Blueprint("rag_extra", __name__)

    @rag_extra_bp.route("/health", methods=["GET"])
    def rag_health():
        health_info = {
            "status": "healthy",
            "system": "rag",
            "database_type": "MySQL",
            "database_connected": False,
            "auth_configured": hasattr(app, "auth_utils"),
            "rag_system_loaded": hasattr(app, "rag_system") and app.rag_system is not None,
        }

        if hasattr(app, "rag_system") and app.rag_system:
            try:
                stats = app.rag_system.get_system_stats()
                health_info.update(
                    {
                        "database_connected": stats.get("database_connected", False),
                        "total_chunks": stats.get("total_chunks", 0),
                        "embedding_model": stats.get("embedding_model", "unknown"),
                    }
                )
            except Exception as exc:
                health_info["error"] = str(exc)

        return jsonify(health_info)

    app.register_blueprint(rag_extra_bp, url_prefix="/api")


def load_rag_system(app: Flask) -> bool:
    """Load RAG system with proper error handling."""
    try:
        logger.info("Loading RAG system...")

        from chatbot.api.chat_api import chat_bp
        from chatbot.api.upload_api import upload_bp
        from chatbot.config.settings import RAGConfig
        from chatbot.database.manager import DatabaseManager
        from chatbot.utils.AuthUtils import AuthUtils

        # Keep same behavior: auth configured here for chatbot routes
        app.config["JWT_SECRET_KEY"] = get_env("JWT_SECRET_KEY", "")
        logger.info("JWT Secret configured")
        app.auth_utils = AuthUtils(app.config["JWT_SECRET_KEY"])

        # Keep same upload behavior
        app.config["ALLOWED_EXTENSIONS"] = {"pdf"}
        app.config["UPLOAD_FOLDER"] = RAGConfig.UPLOAD_DIR
        app.config["MAX_FILE_SIZE"] = MAX_CONTENT_LENGTH
        app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

        logger.info("Upload folder configured: %s", app.config["UPLOAD_FOLDER"])
        logger.info("Data folder: %s", RAGConfig.DATA_DIR)
        logger.info("Cache folder: %s", RAGConfig.CACHE_DIR)

        db_manager = None
        try:
            db_manager = DatabaseManager()
            app.db_manager = db_manager
            logger.info("RAG Database manager initialized")
        except Exception as exc:
            logger.error("Failed to initialize RAG database manager: %s", exc)
            app.db_manager = None

        try:
            from chatbot.core.rag_system import VectorRAGSystem

            rag_system = VectorRAGSystem(
                embedding_model="all-MiniLM-L6-v2",
                chunk_size=1000,
                chunk_overlap=200,
            )
            rag_system.db_manager = db_manager
            app.rag_system = rag_system
            logger.info("RAG system initialized")
        except ImportError:
            logger.warning("VectorRAGSystem not found, using mock system")

            class MockRAGSystem:
                def __init__(self, database_manager):
                    self.db_manager = database_manager

                def generate_response(self, query):
                    return f"RAG Mock response for: {query}"

                def find_relevant_context(self, query, top_k=3, similarity_threshold=0.1):
                    return []

                def get_system_stats(self):
                    return {
                        "total_chunks": 0,
                        "faiss_index_size": 0,
                        "database_connected": bool(
                            self.db_manager and self.db_manager.connection is not None
                        ),
                        "embedding_model": "mock",
                    }

            app.rag_system = MockRAGSystem(db_manager)
            logger.info("Mock RAG system initialized")
        except Exception as exc:
            logger.error("Failed to initialize RAG system: %s", exc)
            app.rag_system = None

        app.register_blueprint(chat_bp, url_prefix="/api")
        logger.info("RAG chat blueprint registered")

        app.register_blueprint(upload_bp, url_prefix="/api")
        logger.info("RAG upload blueprint registered")

        register_rag_health_blueprint(app)

        logger.info("RAG system loaded successfully")
        return True

    except ImportError as exc:
        logger.warning("RAG system not available - missing import: %s", exc)
        return False
    except Exception as exc:
        logger.error("Error loading RAG system: %s", exc)
        traceback.print_exc()
        return False


def load_maternal_system(app: Flask) -> bool:
    """Load maternal system with MySQL support."""
    try:
        logger.info("Loading maternal risk prediction system...")
        logger.info("Python path includes: %s", sys.path[0])

        try:
            logger.info("Attempting to import prediction blueprint...")
            from risk_predition_model.api.prediction import prediction_bp

            logger.info("Prediction blueprint imported: %s", prediction_bp.name)
        except ImportError as exc:
            logger.error("Failed to import prediction blueprint: %s", exc)
            raise

        try:
            logger.info("Attempting to import health blueprint...")
            from risk_predition_model.api.health import health_bp

            logger.info("Health blueprint imported: %s", health_bp.name)
        except ImportError as exc:
            logger.error("Failed to import health blueprint: %s", exc)
            health_bp = None

        app.register_blueprint(prediction_bp, url_prefix="/api/predict")
        logger.info("Maternal prediction blueprint registered at /api/predict")

        if health_bp:
            app.register_blueprint(health_bp, url_prefix="/maternal")
            logger.info("Maternal health blueprint registered at /maternal")

        maternal_routes = [
            str(rule) for rule in app.url_map.iter_rules() if "/api/predict" in str(rule)
        ]
        logger.info("Registered %s prediction routes:", len(maternal_routes))
        for route in maternal_routes[:5]:
            logger.info("  - %s", route)

        try:
            from risk_predition_model.model.database import get_db_manager

            get_db_manager()
            logger.info("Maternal database manager initialized")
        except Exception as exc:
            logger.warning("Could not initialize maternal database manager: %s", exc)

        logger.info("Maternal Risk Prediction system loaded successfully")
        return True

    except ImportError as exc:
        logger.error("Maternal Risk Prediction system not available - Import Error: %s", exc)
        logger.error("Check that risk_predition_model/api/prediction.py exists")
        logger.error("Check that auth/JWTauth.py or risk_predition_model/auth/JWTauth.py exists")
        traceback.print_exc()
        return False
    except Exception as exc:
        logger.error("Error loading Maternal Risk Prediction system: %s", exc)
        traceback.print_exc()
        return False


def load_pregnancy_rag_system(app: Flask) -> bool:
    """Load Pregnancy RAG system with proper error handling."""
    try:
        logger.info("Loading Pregnancy RAG system...")

        from dailyrecommendationAI.api_routes import api as pregnancy_api_blueprint
        from dailyrecommendationAI.api_routes import rag_system

        app.register_blueprint(
            pregnancy_api_blueprint,
            url_prefix="/pregnancy",
            name="pregnancy_api_routes",
        )
        logger.info("Registered Pregnancy API blueprint")

        app.pregnancy_rag_system = rag_system
        logger.info("Pregnancy RAG system loaded successfully")
        return True

    except ImportError as exc:
        logger.warning("Pregnancy RAG system not available: %s", exc)
        return False
    except Exception as exc:
        logger.error("Error loading Pregnancy RAG system: %s", exc)
        traceback.print_exc()
        return False


def register_combined_routes(
    app: Flask,
    maternal_available: bool,
    rag_available: bool,
    pregnancy_available: bool,
) -> None:
    """Register shared app-level routes."""

    @app.route("/health", methods=["GET"])
    def combined_health():
        health_status = {
            "status": "healthy",
            "database_type": "MySQL",
            "auto_setup": "enabled",
            "systems": {},
        }

        if maternal_available:
            health_status["systems"]["maternal"] = {
                "status": "healthy",
                "endpoints": [
                    "/maternal/health",
                    "/api/predict/store",
                    "/api/predict/latest",
                    "/api/predict/history",
                    "/api/predict/user/<id>/latest",
                ],
            }

        if rag_available:
            health_status["systems"]["rag"] = {"status": "healthy"}

        if pregnancy_available:
            health_status["systems"]["pregnancy"] = {"status": "healthy"}

        return jsonify(health_status)

    @app.route("/debug/routes", methods=["GET"])
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(
                {
                    "endpoint": rule.endpoint,
                    "methods": sorted(list(rule.methods)),
                    "rule": str(rule),
                }
            )

        return jsonify(
            {
                "total_routes": len(routes),
                "routes": sorted(routes, key=lambda x: x["rule"]),
            }
        )


def create_combined_app():
    """Create combined Flask app with automatic MySQL setup."""
    logger.info("Creating combined app with MySQL support")
    logger.info("Working directory: %s", os.getcwd())

    logger.info("Setting up MySQL Database")
    if not auto_setup_mysql():
        logger.warning("MySQL setup had issues - proceeding anyway")

    logger.info("Creating Flask Application")
    app = Flask(__name__)
    configure_common_app_settings(app)

    logger.info("Loading Application Systems")
    maternal_available = load_maternal_system(app)
    rag_available = load_rag_system(app)
    pregnancy_available = load_pregnancy_rag_system(app)

    if not maternal_available and not rag_available and not pregnancy_available:
        raise RuntimeError("None of the systems could be loaded")

    register_combined_routes(
        app,
        maternal_available=maternal_available,
        rag_available=rag_available,
        pregnancy_available=pregnancy_available,
    )

    return app, "combined"


def main():
    """Main application entry point with automatic MySQL setup."""
    host = get_env("HOST", "0.0.0.0")
    port = get_int_env("PORT", 5000)
    debug = get_bool_env("DEBUG", "False")

    try:
        logger.info("Combined Maternal Risk & RAG API Server - MySQL Edition with Auto Setup")

        app, app_type = create_combined_app()

        logger.info("Starting Flask Server")
        logger.info("Host: %s, Port: %s, Debug: %s, Database: MySQL", host, port, debug)
        logger.info("Main API: http://%s:%s/", host, port)
        logger.info("Health: http://%s:%s/health", host, port)
        logger.info("Maternal API: http://%s:%s/maternal/", host, port)
        logger.info("Prediction API: http://%s:%s/api/predict/", host, port)

        app.run(
            debug=debug,
            host=host,
            port=port,
            threaded=True,
            use_reloader=debug,
        )

    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as exc:
        logger.error("Failed to start application: %s", exc)
        traceback.print_exc()
    finally:
        logger.info("API Server stopped")


if __name__ == "__main__":
    setup_logging()
    logger.info("Project root: %s", PROJECT_ROOT)
    logger.info("Chatbot logs: %s", CHATBOT_LOG_DIR)
    main()