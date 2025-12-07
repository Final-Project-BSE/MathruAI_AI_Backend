"""
Combined main application entry point - MySQL with Auto Setup.
"""
import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def auto_setup_mysql():
    """Automatically setup MySQL database and tables"""
    try:
        import pymysql
        
        mysql_user = os.getenv('MYSQL_USER', 'root')
        mysql_password = os.getenv('MYSQL_PASSWORD', '20000624')
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = int(os.getenv('MYSQL_PORT', 3306))
        mysql_database = os.getenv('MYSQL_DATABASE', 'mathruai_database')
        
        logger.info("Starting MySQL Database Setup")
        logger.info(f"Host: {mysql_host}:{mysql_port}, Database: {mysql_database}, User: {mysql_user}")
        
        # Connect to MySQL server and create database
        logger.info("Connecting to MySQL server...")
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password
        )
        
        cursor = connection.cursor()
        
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        logger.info(f"Connected to MySQL {version[0]}")
        
        logger.info(f"Creating database '{mysql_database}' if not exists...")
        cursor.execute(f"""
            CREATE DATABASE IF NOT EXISTS `{mysql_database}` 
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_unicode_ci
        """)
        logger.info(f"Database '{mysql_database}' ready")
        
        cursor.close()
        connection.close()
        
        # Connect to the specific database
        logger.info(f"Connecting to database '{mysql_database}'...")
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )
        
        cursor = connection.cursor()
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        logger.error(f"MySQL Error: {e}")
        logger.error("Please check: MySQL server is running, credentials are correct, user has privileges")
        return False


def load_rag_system(app):
    """Load RAG system with proper error handling"""
    try:
        logger.info("Loading RAG system...")
        
        from chatbot.api.chat_api import chat_bp
        from chatbot.database.manager import DatabaseManager
        from chatbot.utils.AuthUtils import AuthUtils
        from chatbot.api.upload_api import upload_bp
        
        # Initialize authentication
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd')
        logger.info("JWT Secret configured")
        auth_utils = AuthUtils(app.config['JWT_SECRET_KEY'])
        app.auth_utils = auth_utils
        
        # Initialize database manager
        try:
            db_manager = DatabaseManager()
            app.db_manager = db_manager
            logger.info("RAG Database manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG database manager: {e}")
            app.db_manager = None
        
        # Initialize RAG system
        try:
            from chatbot.core.rag_system import VectorRAGSystem
            
            rag_system = VectorRAGSystem(
                embedding_model='all-MiniLM-L6-v2',
                chunk_size=1000,
                chunk_overlap=200
            )
            rag_system.db_manager = db_manager
            app.rag_system = rag_system
            logger.info("RAG system initialized")
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
            logger.info("Mock RAG system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            app.rag_system = None
        
        # Register blueprints
        app.register_blueprint(chat_bp, url_prefix='/api')
        logger.info("RAG chat blueprint registered")

        app.register_blueprint(upload_bp, url_prefix='/api')
        logger.info("RAG upload blueprint registered")
        
        # Add additional RAG endpoints
        from flask import Blueprint
        rag_extra_bp = Blueprint('rag_extra', __name__)
        
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
        
        app.register_blueprint(rag_extra_bp, url_prefix='/api')
        
        logger.info("RAG system loaded successfully")
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
    """Load maternal system with MySQL support - FIXED VERSION"""
    try:
        logger.info("Loading maternal risk prediction system...")
        logger.info(f"Python path includes: {sys.path[0]}")
        
        # Try to import blueprints with detailed error handling
        try:
            logger.info("Attempting to import prediction blueprint...")
            from risk_predition_model.api.prediction import prediction_bp
            logger.info(f"✓ Prediction blueprint imported: {prediction_bp.name}")
        except ImportError as e:
            logger.error(f"✗ Failed to import prediction blueprint: {e}")
            raise
        
        try:
            logger.info("Attempting to import health blueprint...")
            from risk_predition_model.api.health import health_bp
            logger.info(f"✓ Health blueprint imported: {health_bp.name}")
        except ImportError as e:
            logger.error(f"✗ Failed to import health blueprint: {e}")
            # Continue without health blueprint
            health_bp = None
        
        # Register prediction blueprint
        app.register_blueprint(prediction_bp, url_prefix='/api/predict')
        logger.info("✓ Maternal prediction blueprint registered at /api/predict")
        
        # Register health blueprint if available
        if health_bp:
            app.register_blueprint(health_bp, url_prefix='/maternal')
            logger.info("✓ Maternal health blueprint registered at /maternal")
        
        # Verify routes were registered
        maternal_routes = [str(rule) for rule in app.url_map.iter_rules() if '/api/predict' in str(rule)]
        logger.info(f"✓ Registered {len(maternal_routes)} prediction routes:")
        for route in maternal_routes[:5]:  # Show first 5
            logger.info(f"  - {route}")
        
        # Try to initialize database (optional)
        try:
            from risk_predition_model.model.database import get_db_manager
            db_manager = get_db_manager()
            logger.info("✓ Maternal database manager initialized")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize maternal database manager: {e}")
        
        logger.info("✓✓✓ Maternal Risk Prediction system loaded successfully ✓✓✓")
        return True
        
    except ImportError as e:
        logger.error(f"✗ Maternal Risk Prediction system not available - Import Error: {e}")
        logger.error("Check that risk_predition_model/api/prediction.py exists")
        logger.error("Check that auth/JWTauth.py or risk_predition_model/auth/JWTauth.py exists")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"✗ Error loading Maternal Risk Prediction system: {e}")
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
        logger.info("Registered Pregnancy API blueprint")
        
        app.pregnancy_rag_system = rag_system
        logger.info("Pregnancy RAG system loaded successfully")
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
    
    logger.info("Setting up MySQL Database")
    if not auto_setup_mysql():
        logger.warning("MySQL setup had issues - proceeding anyway")
    
    logger.info("Creating Flask Application")
    
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

    # Load systems
    logger.info("Loading Application Systems")
    
    maternal_available = load_maternal_system(app)
    rag_available = load_rag_system(app)
    pregnancy_available = load_pregnancy_rag_system(app)
    
    if not maternal_available and not rag_available and not pregnancy_available:
        raise RuntimeError("None of the systems could be loaded")
    
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
            health_status["systems"]["maternal"] = {
                "status": "healthy",
                "endpoints": [
                    "/maternal/health",
                    "/api/predict/store",
                    "/api/predict/latest",
                    "/api/predict/history",
                    "/api/predict/user/<id>/latest"
                ]
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
        logger.info("Combined Maternal Risk & RAG API Server - MySQL Edition with Auto Setup")
        
        app, app_type = create_combined_app()
        
        logger.info("Starting Flask Server")
        logger.info(f"Host: {host}, Port: {port}, Debug: {debug}, Database: MySQL")
        logger.info(f"Main API: http://{host}:{port}/")
        logger.info(f"Health: http://{host}:{port}/health")
        logger.info(f"Maternal API: http://{host}:{port}/maternal/")
        logger.info(f"Prediction API: http://{host}:{port}/api/predict/")
        
        app.run(
            debug=debug,
            host=host,
            port=port,
            threaded=True,
            use_reloader=debug
        )
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("API Server stopped")


if __name__ == '__main__':
    main()