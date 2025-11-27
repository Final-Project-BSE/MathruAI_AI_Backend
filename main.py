"""
Combined main application entry point - MySQL VERSION with Auto-Setup.
"""
import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Add project root to Python path at the very beginning
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging with enhanced format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def auto_setup_mysql():
    """Automatically setup MySQL database and tables"""
    try:
        import pymysql
        
        # Get MySQL configuration from environment
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', '20000624')
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = int(os.getenv('MYSQL_PORT', 3306))
        mysql_database = os.getenv('MYSQL_DATABASE', 'mathruai_database')
        
        logger.info("=" * 70)
        logger.info("Automatic MySQL Database Setup")
        logger.info("=" * 70)
        logger.info(f"Host: {mysql_host}:{mysql_port}")
        logger.info(f"Database: {mysql_database}")
        logger.info(f"User: {mysql_user}")
        
        # Step 1: Connect to MySQL server and create database
        logger.info("\nConnecting to MySQL server...")
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password
        )
        
        cursor = connection.cursor()
        
        # Get MySQL version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        logger.info(f"✓ Connected to MySQL {version[0]}")
        
        # Create database if it doesn't exist
        logger.info(f"Creating database '{mysql_database}' if not exists...")
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS `{mysql_database}` 
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_unicode_ci
        """)
        logger.info(f"✓ Database '{mysql_database}' ready")
        
        cursor.close()
        connection.close()
        
        # Step 2: Connect to the specific database
        logger.info(f"Connecting to database '{mysql_database}'...")
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
        
        cursor = connection.cursor()
        
        # Create user_predictions table if not exists
        logger.info("Creating table 'user_predictions' if not exists...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
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
                INDEX idx_user_id (user_id),
                INDEX idx_user_created (user_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        logger.info("✓ Table 'user_predictions' ready")
        
        # Check existing records
        cursor.execute("SELECT COUNT(*) as count FROM user_predictions")
        result = cursor.fetchone()
        logger.info(f"✓ Current records in database: {result[0]}")
        
        cursor.close()
        connection.close()
        
        logger.info("=" * 70)
        logger.info("✓ MySQL Database Setup Completed Successfully!")
        logger.info("=" * 70)
        
        return True
        
    except pymysql.Error as e:
        logger.error(f"MySQL Error: {e}")
        logger.error("Please check:")
        logger.error("  1. MySQL server is running")
        logger.error("  2. Credentials in .env file are correct")
        logger.error("  3. User has sufficient privileges")
        return False
        
    except Exception as e:
        logger.error(f"Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_rag_system(app):
    """Load RAG system with proper error handling"""
    try:
        logger.info("Loading RAG system...")
        
        # Import the correct chat blueprint from chat_api.py
        from chatbot.api.chat_api import chat_bp
        from chatbot.database.manager import DatabaseManager
        from chatbot.utils.AuthUtils import AuthUtils
        from chatbot.api.upload_api import upload_bp

        
        # Initialize authentication for RAG system
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd')
        logger.info(f"JWT Secret configured")
        auth_utils = AuthUtils(app.config['JWT_SECRET_KEY'])
        app.auth_utils = auth_utils
        
        # Initialize database manager
        try:
            db_manager = DatabaseManager()
            app.db_manager = db_manager
            logger.info("✓ RAG Database manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG database manager: {e}")
            app.db_manager = None
        
        # Initialize proper RAG system
        try:
            from chatbot.core.rag_system import VectorRAGSystem
            
            rag_system = VectorRAGSystem(
                embedding_model='all-MiniLM-L6-v2',
                chunk_size=1000,
                chunk_overlap=200
            )
            rag_system.db_manager = db_manager
            app.rag_system = rag_system
            logger.info("✓ RAG system initialized")
        except ImportError:
            logger.warning("VectorRAGSystem not found, using mock system")
            class MockRAGSystem:
                def __init__(self, db_manager):
                    self.db_manager = db_manager
                
                def generate_response(self, query):
                    return f"RAG Mock response for: {query}"
                
                def find_relevant_context(self, query, top_k=3, similarity_threshold=0.1):
                    return []
                
                def get_system_stats(self):
                    return {
                        'total_chunks': 0,
                        'faiss_index_size': 0,
                        'database_connected': self.db_manager and self.db_manager.connection is not None,
                        'embedding_model': 'mock'
                    }
            
            app.rag_system = MockRAGSystem(db_manager)
            logger.info("✓ Mock RAG system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            app.rag_system = None
        
        # Register RAG chat blueprint
        app.register_blueprint(chat_bp, url_prefix='/api')
        logger.info("✓ RAG chat blueprint registered")

        app.register_blueprint(upload_bp, url_prefix='/api')
        logger.info("✓ RAG upload blueprint registered")
        
        # Add additional RAG endpoints
        from flask import Blueprint
        rag_extra_bp = Blueprint('rag_extra', __name__)
        
        @rag_extra_bp.route('/')
        def rag_documentation():
            return jsonify({
                "service": "Enhanced RAG API",
                "version": "2.0",
                "database": "MySQL",
                "endpoints": [
                    "GET  /rag/ - This documentation",
                    "GET  /rag/health - RAG system health check",
                    "GET  /rag/stats - RAG system statistics",
                    "POST /rag/chat - Interactive chat with authentication",
                    "GET  /rag/chats - List user's chat sessions",
                    "POST /rag/chats - Create new chat session",
                    "GET  /rag/chats/<id> - Get chat history",
                    "DELETE /rag/chats/<id> - Delete chat session",
                    "GET  /rag/user/stats - User statistics"
                ]
            })
        
        @rag_extra_bp.route('/health')
        def rag_health():
            health_info = {
                "status": "healthy",
                "system": "rag",
                "database_type": "MySQL",
                "database_connected": False,
                "auth_configured": hasattr(app, 'auth_utils'),
                "rag_system_loaded": hasattr(app, 'rag_system') and app.rag_system is not None
            }
            
            if hasattr(app, 'rag_system') and app.rag_system:
                try:
                    stats = app.rag_system.get_system_stats()
                    health_info.update({
                        "database_connected": stats.get('database_connected', False),
                        "total_chunks": stats.get('total_chunks', 0),
                        "embedding_model": stats.get('embedding_model', 'unknown')
                    })
                except Exception as e:
                    health_info["error"] = str(e)
            
            return jsonify(health_info)
        
        @rag_extra_bp.route('/stats')
        def rag_stats():
            if not hasattr(app, 'rag_system') or not app.rag_system:
                return jsonify({"error": "RAG system not available"}), 503
            
            try:
                stats = app.rag_system.get_system_stats()
                return jsonify(stats)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        app.register_blueprint(rag_extra_bp, url_prefix='/api')
        
        logger.info("✓ RAG system loaded successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"RAG system not available - missing import: {e}")
        return False
    except Exception as e:
        logger.error(f"Error loading RAG system: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_maternal_system(app):
    """Load maternal system with MySQL support"""
    try:
        logger.info("Loading maternal risk prediction system...")
        
        from risk_predition_model.api.health import health_bp
        from risk_predition_model.api.prediction import prediction_bp
        from risk_predition_model.api.model_info import model_info_bp
        from risk_predition_model.app import create_app, get_predictor
        
        # Create the maternal app context to initialize database and load model
        try:
            maternal_app = create_app()
            logger.info("✓ Maternal app created with MySQL database initialized")
        except Exception as e:
            logger.error(f"Failed to create maternal app: {e}")
            return False
        
        # Check if predictor loads
        predictor = get_predictor()
        if predictor is None:
            logger.error("Predictor could not be loaded")
            return False
        
        logger.info("✓ Predictor loaded successfully")
        
        # Register maternal blueprints with prefix
        app.register_blueprint(health_bp, url_prefix='/maternal')
        app.register_blueprint(prediction_bp, url_prefix='/maternal')
        app.register_blueprint(model_info_bp, url_prefix='/maternal')
        
        logger.info("✓ Maternal Risk Prediction system loaded successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"Maternal Risk Prediction system not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error loading Maternal Risk Prediction system: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_pregnancy_rag_system(app):
    """Load Pregnancy RAG system with proper error handling"""
    try:
        logger.info("Loading Pregnancy RAG system...")
        
        from dailyrecommendationAI.api_routes import api as pregnancy_api_blueprint, rag_system
        
        app.register_blueprint(
            pregnancy_api_blueprint, 
            url_prefix='/pregnancy', 
            name='pregnancy_api_routes'
        )
        logger.info("✓ Registered Pregnancy API blueprint")
        
        app.pregnancy_rag_system = rag_system
        logger.info("✓ Pregnancy RAG system loaded successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"Pregnancy RAG system not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error loading Pregnancy RAG system: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_combined_app():
    """Create combined Flask app with automatic MySQL setup."""
    logger.info(f"Creating combined app with MySQL support")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # AUTOMATICALLY SETUP MySQL database and tables
    logger.info("\n" + "=" * 70)
    logger.info("STEP 1: Setting up MySQL Database")
    logger.info("=" * 70)
    
    if not auto_setup_mysql():
        logger.warning("MySQL setup had issues - proceeding anyway")
        logger.warning("The application may not work correctly without proper database setup")
    
    logger.info("\n" + "=" * 70)
    logger.info("STEP 2: Creating Flask Application")
    logger.info("=" * 70)
    
    # Create main Flask app
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, 
         origins="*",
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])
    
    # Set up configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # RAG system configuration
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_FILE_SIZE'] = 16 * 1024 * 1024
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize maternal database with MySQL using SQLAlchemy
    try:
        logger.info("Initializing SQLAlchemy with MySQL...")
        from risk_predition_model.model.database import db
        
        # Get MySQL configuration
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', 'your_password')
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = os.getenv('MYSQL_PORT', '3306')
        mysql_database = os.getenv('MYSQL_DATABASE', 'maternal_health')
        
        # Configure SQLAlchemy with MySQL
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'max_overflow': 20
        }
        
        logger.info(f"MySQL URI: mysql+pymysql://{mysql_user}:****@{mysql_host}:{mysql_port}/{mysql_database}")

        db.init_app(app)
        
        # Create tables in app context (this will use existing tables created by auto_setup_mysql)
        with app.app_context():
            db.create_all()
            logger.info("✓ SQLAlchemy synchronized with MySQL tables")
    except Exception as e:
        logger.warning(f"Could not initialize SQLAlchemy: {e}")

    # Load systems
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: Loading Application Systems")
    logger.info("=" * 70)
    
    maternal_available = load_maternal_system(app)
    rag_available = load_rag_system(app)
    pregnancy_available = load_pregnancy_rag_system(app)
    
    if not maternal_available and not rag_available and not pregnancy_available:
        raise RuntimeError("None of the systems could be loaded")
    
    # Root endpoint
    @app.route('/')
    def api_documentation():
        available_systems = {}
        endpoints = {}
        
        if maternal_available:
            available_systems["maternal"] = "Available at /maternal/*"
            endpoints["maternal_endpoints"] = [
                "POST /maternal/predict - Full risk and advice prediction",
                "GET /maternal/get-latest/<user_id> - Get latest prediction",
                "DELETE /maternal/delete/<user_id> - Delete prediction",
                "GET /maternal/model-info - Model information",
                "GET /maternal/health - Health check"
            ]
            
        if rag_available:
            available_systems["rag"] = "Available at /rag/*"
            endpoints["rag_endpoints"] = [
                "POST /rag/chat - Interactive chat",
                "GET /rag/health - Health check",
                "GET /rag/stats - Statistics"
            ]
            
        if pregnancy_available:
            available_systems["pregnancy"] = "Available at /pregnancy/*"
            endpoints["pregnancy_endpoints"] = [
                "GET /pregnancy/health - Health check",
                "POST /pregnancy/register - Register user",
                "POST /pregnancy/search - Search knowledge"
            ]
            
        return jsonify({
            "message": "Combined Maternal Risk & RAG API Server",
            "version": "2.1 - MySQL Edition (Auto-Setup)",
            "database": "MySQL",
            "systems": available_systems,
            **endpoints
        })

    # Combined health check
    @app.route('/health')
    def combined_health():
        health_status = {
            "status": "healthy",
            "database_type": "MySQL",
            "auto_setup": "enabled",
            "systems": {}
        }
        
        if maternal_available:
            try:
                from risk_predition_model.app import get_predictor
                predictor = get_predictor()
                health_status["systems"]["maternal"] = {
                    "status": "healthy",
                    "model_loaded": predictor is not None,
                    "database": "MySQL"
                }
            except Exception as e:
                health_status["systems"]["maternal"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        if rag_available:
            health_status["systems"]["rag"] = {"status": "healthy"}
            
        if pregnancy_available:
            health_status["systems"]["pregnancy"] = {"status": "healthy"}
        
        return jsonify(health_status)
    
    # Debug endpoint
    @app.route('/debug/routes')
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule)
            })
        
        return jsonify({
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['rule'])
        })
    
    return app, 'combined'


def main():
    """Main application entry point with automatic MySQL setup."""
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    try:
        logger.info("=" * 70)
        logger.info("Combined Maternal Risk & RAG API Server")
        logger.info("MySQL Edition with Automatic Database Setup")
        logger.info("=" * 70)
        
        app, app_type = create_combined_app()
        
        logger.info("\n" + "=" * 70)
        logger.info("STEP 4: Starting Flask Server")
        logger.info("=" * 70)
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Debug: {debug}")
        logger.info(f"Database: MySQL (auto-configured)")
        logger.info("=" * 70)
        logger.info("\n🚀 Server is ready!")
        logger.info(f"   Main API: http://{host}:{port}/")
        logger.info(f"   Health: http://{host}:{port}/health")
        logger.info(f"   Maternal API: http://{host}:{port}/maternal/")
        logger.info("=" * 70 + "\n")
        
        app.run(
            debug=debug,
            host=host,
            port=port,
            threaded=True,
            use_reloader=debug
        )
        
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 70)
        logger.info("Server shutdown requested by user")
        logger.info("=" * 70)
    except Exception as e:
        logger.error("\n" + "=" * 70)
        logger.error(f"Failed to start application: {e}")
        logger.error("=" * 70)
        import traceback
        traceback.print_exc()
    finally:
        logger.info("API Server stopped")


if __name__ == '__main__':
    main()