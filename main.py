"""
Combined main application entry point.
Runs both Maternal Risk Prediction API and Enhanced RAG API Server together.
"""
import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# CRITICAL FIX: Add project root to Python path at the very beginning
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging with enhanced format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_maternal_imports():
    """Test maternal system imports before using them"""
    try:
        # Test each import individually
        from risk_predition_model.config import config
        logger.info("✓ Config import successful")
        
        from risk_predition_model.utils.data_preprocessing import DataPreprocessor
        logger.info("✓ DataPreprocessor import successful")
        
        from risk_predition_model.model.predict import RiskAdvicePredictor
        logger.info("✓ RiskAdvicePredictor import successful")
        
        from risk_predition_model.api.health import health_bp
        from risk_predition_model.api.prediction import prediction_bp
        from risk_predition_model.api.model_info import model_info_bp
        logger.info("✓ Blueprint imports successful")
        
        from risk_predition_model.app import get_predictor
        logger.info("✓ App import successful")
        
        return True
        
    except ImportError as e:
        logger.error(f"Import test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in import test: {e}")
        return False


def load_maternal_system(app):
    """Load maternal system with proper error handling"""
    try:
        logger.info("Loading maternal risk prediction system...")
        
        # Test imports first
        if not test_maternal_imports():
            logger.warning("Maternal system imports failed - skipping maternal system")
            return False
        
        # Import after confirming they work
        from risk_predition_model.api.health import health_bp
        from risk_predition_model.api.prediction import prediction_bp
        from risk_predition_model.api.model_info import model_info_bp
        from risk_predition_model.app import get_predictor
        
        # Check if predictor loads
        predictor = get_predictor()
        if predictor is None:
            logger.warning("Predictor is None - model may not be loaded properly")
            
            # Try to create the app and load the model
            try:
                from risk_predition_model.app import create_app
                maternal_app = create_app()
                # Get predictor from the created app
                from risk_predition_model.app import get_predictor
                predictor = get_predictor()
                
                if predictor is None:
                    logger.error("Still couldn't load predictor after creating app")
                    return False
                else:
                    logger.info("✓ Predictor loaded successfully after app creation")
            except Exception as e:
                logger.error(f"Failed to create maternal app: {e}")
                return False
        
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


def load_rag_system(app):
    """Load RAG system with proper error handling"""
    try:
        # Import RAG app factory
        from chatbot.core.app import create_app as create_rag_app
        
        # Create RAG app to get its blueprints
        rag_app = create_rag_app()
        
        # Copy RAG system reference
        if hasattr(rag_app, 'rag_system'):
            app.rag_system = rag_app.rag_system
            
        # Register RAG blueprints with prefix
        for blueprint_name, blueprint in rag_app.blueprints.items():
            # Create a new blueprint with prefix
            if not blueprint_name.startswith('rag_'):
                new_blueprint_name = f"rag_{blueprint_name}"
            else:
                new_blueprint_name = blueprint_name
                
            # Register with /rag prefix
            app.register_blueprint(blueprint, url_prefix='/rag', name=new_blueprint_name)
            
        logger.info("✓ RAG system loaded successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"RAG system not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error loading RAG system: {e}")
        return False


def load_pregnancy_rag_system(app):
    """Load Pregnancy RAG system with proper error handling"""
    try:
        logger.info("Loading Pregnancy RAG system...")
        
        # Import the pregnancy RAG system directly
        from dailyrecommendationAI.api_routes import api as pregnancy_api_blueprint, rag_system
        
        # Register the pregnancy API blueprint with /pregnancy prefix
        # Use a unique name to avoid conflicts
        app.register_blueprint(
            pregnancy_api_blueprint, 
            url_prefix='/pregnancy', 
            name='pregnancy_api_routes'
        )
        logger.info("✓ Registered Pregnancy API blueprint with prefix /pregnancy")
        
        # Attach the RAG system instance to the app for health checks
        app.pregnancy_rag_system = rag_system
        logger.info("✓ Pregnancy RAG system instance attached to app")
        
        logger.info("✓ Pregnancy RAG system loaded successfully")
        return True
        
    except ImportError as e:
        logger.warning(f"Pregnancy RAG system not available: {e}")
        logger.warning("Make sure api_routes.py exists and contains the 'api' blueprint and 'rag_system'")
        return False
    except Exception as e:
        logger.error(f"Error loading Pregnancy RAG system: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_combined_app():
    """Create combined Flask app with both maternal and RAG systems."""
    logger.info(f"Creating combined app from directory: {os.getcwd()}")
    logger.info(f"Python path includes: {project_root}")
    
    # Create main Flask app
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, 
         origins="*",
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])
    
    # Set up configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # ADD THESE MISSING CONFIGURATION SETTINGS FOR RAG SYSTEM
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_FILE_SIZE'] = 16 * 1024 * 1024  # 16MB
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Load systems
    maternal_available = load_maternal_system(app)
    rag_available = load_rag_system(app)
    pregnancy_available = load_pregnancy_rag_system(app)
    
    if not maternal_available and not rag_available and not pregnancy_available:
        raise RuntimeError("None of the systems (maternal, RAG, or pregnancy) could be loaded")
    
    # Root endpoint for API documentation
    @app.route('/')
    def api_documentation():
        available_systems = {}
        endpoints = {}
        
        if maternal_available:
            available_systems["maternal"] = "Available at /maternal/*"
            endpoints["maternal_endpoints"] = [
                "POST /maternal/predict - Full risk and advice prediction",
                "POST /maternal/predict-risk-only - Risk prediction only", 
                "GET /maternal/model-info - Model information",
                "POST /maternal/batch-predict - Batch predictions",
                "GET /maternal/health - Health check"
            ]
            
        if rag_available:
            available_systems["rag"] = "Available at /rag/*"
            endpoints["rag_endpoints"] = [
                "GET /rag/ - RAG API documentation",
                "GET /rag/health - System health check",
                "GET /rag/stats - System statistics", 
                "POST /rag/chat - Interactive chat",
                "GET /rag/chats - List chat sessions",
                "POST /rag/chats - Create chat session",
                "GET /rag/chats/<id> - Get chat history",
                "DELETE /rag/chats/<id> - Delete chat session",
                "POST /rag/search - Semantic search",
                "POST /rag/upload - Upload PDF documents",
                "POST /rag/reinitialize - Reinitialize system"
            ]
            
        if pregnancy_available:
            available_systems["pregnancy"] = "Available at /pregnancy/*"
            endpoints["pregnancy_endpoints"] = [
                "GET /pregnancy/health - Health check",
                "POST /pregnancy/register - Register new user",
                "GET /pregnancy/user/<user_id> - Get user info",
                "PUT /pregnancy/user/<user_id> - Update user",
                "GET /pregnancy/recommendation/<user_id> - Get recommendation",
                "POST /pregnancy/search - Search knowledge base",
                "GET /pregnancy/recommendations/history/<user_id> - Get history",
                "POST /pregnancy/upload-pdf - Upload PDF",
                "GET /pregnancy/stats - System statistics",
                "GET /pregnancy/debug/recommendation/<user_id> - Debug endpoint"
            ]
            
        return jsonify({
            "message": "Combined Maternal Risk & RAG API Server",
            "version": "2.1",
            "systems": available_systems,
            **endpoints
        })

    # Combined health check
    @app.route('/health')
    def combined_health():
        health_status = {
            "status": "healthy",
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                "", 0, "", 0, "", (), None)),
            "systems": {}
        }
        
        if maternal_available:
            try:
                from risk_predition_model.app import get_predictor
                predictor = get_predictor()
                health_status["systems"]["maternal"] = {
                    "status": "healthy",
                    "model_loaded": predictor is not None,
                    "api_version": "2.0"
                }
            except Exception as e:
                health_status["systems"]["maternal"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["systems"]["maternal"] = {
                "status": "unavailable",
                "model_loaded": False
            }
        
        if rag_available and hasattr(app, 'rag_system') and app.rag_system:
            try:
                stats = app.rag_system.get_system_stats()
                health_status["systems"]["rag"] = {
                    "status": "healthy",
                    "knowledge_base_chunks": stats.get('total_chunks', 0),
                    "database_connected": stats.get('database_connected', False),
                    "embedding_model": stats.get('embedding_model', 'unknown')
                }
            except Exception as e:
                health_status["systems"]["rag"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["systems"]["rag"] = {
                "status": "unavailable"
            }
            
        if pregnancy_available:
            try:
                if hasattr(app, 'pregnancy_rag_system') and app.pregnancy_rag_system:
                    # Get basic info from pregnancy RAG system
                    health_status["systems"]["pregnancy"] = {
                        "status": "healthy",
                        "system": "pregnancy_rag_loaded",
                        "vector_db_size": len(app.pregnancy_rag_system.vector_database.document_chunks) if hasattr(app.pregnancy_rag_system, 'vector_database') else 0,
                        "database_connected": app.pregnancy_rag_system.database_manager.is_connected() if hasattr(app.pregnancy_rag_system, 'database_manager') else False,
                        "groq_available": getattr(app.pregnancy_rag_system.ai_service, 'groq_available', False) if hasattr(app.pregnancy_rag_system, 'ai_service') else False
                    }
                else:
                    health_status["systems"]["pregnancy"] = {
                        "status": "healthy",
                        "system": "pregnancy_blueprint_loaded"
                    }
            except Exception as e:
                health_status["systems"]["pregnancy"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_status["systems"]["pregnancy"] = {
                "status": "unavailable"
            }
        
        return jsonify(health_status)
    
    # Debug endpoint to list all routes
    @app.route('/debug/routes')
    def list_routes():
        """List all registered routes for debugging"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'rule': str(rule),
                'subdomain': rule.subdomain
            })
        
        return jsonify({
            'total_routes': len(routes),
            'routes': sorted(routes, key=lambda x: x['rule'])
        })
    
    # Determine app type
    systems = []
    if maternal_available:
        systems.append('maternal')
    if rag_available:
        systems.append('rag')
    if pregnancy_available:
        systems.append('pregnancy')
    
    if len(systems) > 1:
        app_type = 'combined'
    elif systems:
        app_type = systems[0]
    else:
        app_type = 'unknown'
    
    return app, app_type


def print_startup_info(app_type, app):
    """Print startup information based on app type."""
    logger.info("=" * 70)
    
    if app_type == 'combined':
        logger.info("Combined Maternal Risk & RAG API Server v2.1")
        logger.info("=" * 70)
        logger.info("Multiple systems are active and running together!")
        
        # Print RAG stats if available
        if hasattr(app, 'rag_system') and app.rag_system:
            try:
                stats = app.rag_system.get_system_stats()
                logger.info(f"Knowledge Base: {stats['total_chunks']} chunks")
                logger.info(f"FAISS Index: {stats['faiss_index_size']} vectors")
                logger.info(f"Database: {'Connected' if stats['database_connected'] else 'Disconnected'}")
            except Exception as e:
                logger.warning(f"Could not retrieve RAG system stats: {e}")
        
        # Print pregnancy system stats if available
        if hasattr(app, 'pregnancy_rag_system') and app.pregnancy_rag_system:
            try:
                if hasattr(app.pregnancy_rag_system, 'vector_database'):
                    vector_size = len(app.pregnancy_rag_system.vector_database.document_chunks)
                    logger.info(f"Pregnancy Knowledge Base: {vector_size} chunks")
                if hasattr(app.pregnancy_rag_system, 'database_manager'):
                    db_status = "Connected" if app.pregnancy_rag_system.database_manager.is_connected() else "Disconnected"
                    logger.info(f"Pregnancy Database: {db_status}")
            except Exception as e:
                logger.warning(f"Could not retrieve pregnancy system stats: {e}")
        
        logger.info("Combined System Endpoints:")
        logger.info("  GET  /                     - API documentation")
        logger.info("  GET  /health               - Combined health check")
        logger.info("  GET  /debug/routes         - List all routes (debug)")
        logger.info("")
        logger.info("Maternal Risk Prediction (prefixed with /maternal):")
        logger.info("  POST /maternal/predict           - Full risk and advice prediction")
        logger.info("  POST /maternal/predict-risk-only - Risk prediction only")
        logger.info("  GET  /maternal/model-info        - Model information")
        logger.info("  GET  /maternal/health            - Health check")
        logger.info("")
        logger.info("Enhanced RAG API (prefixed with /rag):")
        logger.info("  GET  /rag/                 - RAG API documentation")
        logger.info("  GET  /rag/health           - System health check")
        logger.info("  GET  /rag/stats            - System statistics")
        logger.info("  POST /rag/chat             - Interactive chat")
        logger.info("  POST /rag/search           - Semantic search")
        logger.info("  POST /rag/upload           - Upload PDF documents")
        logger.info("")
        logger.info("Pregnancy RAG API (prefixed with /pregnancy):")
        logger.info("  GET  /pregnancy/health                        - Health check")
        logger.info("  POST /pregnancy/register                      - Register new user")
        logger.info("  GET  /pregnancy/user/<user_id>                - Get user info")
        logger.info("  PUT  /pregnancy/user/<user_id>                - Update user")
        logger.info("  GET  /pregnancy/recommendation/<user_id>      - Get recommendation")
        logger.info("  POST /pregnancy/search                        - Search knowledge base")
        logger.info("  GET  /pregnancy/recommendations/history/<user_id> - Get history")
        logger.info("  POST /pregnancy/upload-pdf                    - Upload PDF")
        logger.info("  GET  /pregnancy/stats                         - System statistics")
        logger.info("  GET  /pregnancy/debug/recommendation/<user_id> - Debug endpoint")
        
    elif app_type == 'maternal':
        logger.info("Maternal Risk & Advice Prediction API")
        logger.info("=" * 70)
        logger.info("Maternal Risk Prediction Endpoints:")
        logger.info("  POST /maternal/predict           - Full risk and advice prediction")
        logger.info("  POST /maternal/predict-risk-only - Risk prediction only")
        logger.info("  GET  /maternal/model-info        - Model information")
        logger.info("  GET  /maternal/health            - Health check")
        
    elif app_type == 'rag':
        logger.info("Enhanced RAG API Server")
        logger.info("=" * 70)
        logger.info(f"RAG System Status: {'Ready' if hasattr(app, 'rag_system') and app.rag_system else 'Not Ready'}")
        
        # Print RAG stats if available
        if hasattr(app, 'rag_system') and app.rag_system:
            try:
                stats = app.rag_system.get_system_stats()
                logger.info(f"Knowledge Base: {stats['total_chunks']} chunks")
                logger.info(f"FAISS Index: {stats['faiss_index_size']} vectors")
                logger.info(f"Database: {'Connected' if stats['database_connected'] else 'Disconnected'}")
            except Exception as e:
                logger.warning(f"Could not retrieve RAG system stats: {e}")
        
        logger.info("Enhanced RAG API Endpoints:")
        logger.info("  GET  /rag/                  - API documentation")
        logger.info("  GET  /rag/health            - System health check")
        logger.info("  GET  /rag/stats             - System statistics")
        logger.info("  POST /rag/chat              - Interactive chat")
        logger.info("  POST /rag/search            - Semantic search")
        logger.info("  POST /rag/upload            - Upload PDF documents")
        
    elif app_type == 'pregnancy':
        logger.info("Pregnancy RAG API Server")
        logger.info("=" * 70)
        logger.info("Pregnancy RAG System Status: Ready")
        logger.info("Pregnancy RAG API Endpoints:")
        logger.info("  GET  /pregnancy/health                        - Health check")
        logger.info("  POST /pregnancy/register                      - Register new user")
        logger.info("  GET  /pregnancy/user/<user_id>                - Get user info")
        logger.info("  PUT  /pregnancy/user/<user_id>                - Update user")
        logger.info("  GET  /pregnancy/recommendation/<user_id>      - Get recommendation")
        logger.info("  POST /pregnancy/search                        - Search knowledge base")
        logger.info("  GET  /pregnancy/recommendations/history/<user_id> - Get history")
        logger.info("  POST /pregnancy/upload-pdf                    - Upload PDF")
        logger.info("  GET  /pregnancy/stats                         - System statistics")
        logger.info("  GET  /pregnancy/debug/recommendation/<user_id> - Debug endpoint")


def main():
    """Main application entry point."""
    # Get configuration from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Support legacy FLASK_ENV for debug mode
    if os.environ.get('FLASK_ENV') == 'development':
        debug = True
    
    try:
        # Create combined application
        app, app_type = create_combined_app()
        
        # Print startup information
        print_startup_info(app_type, app)
        
        logger.info("=" * 70)
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Debug Mode: {debug}")
        logger.info(f"Application Type: {app_type}")
        logger.info("=" * 70)
        logger.info("TIP: Visit /debug/routes to see all registered routes")
        logger.info("=" * 70)
        
        # Start the Flask development server
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
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("API Server stopped")


if __name__ == '__main__':
    main()