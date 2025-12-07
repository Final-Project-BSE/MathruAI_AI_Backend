# from app import create_app
# import os
# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def main():
#     """Main entry point for the application"""
#     app = create_app()
    
#     print("="*60)
#     print("MATERNAL RISK & ADVICE PREDICTION API")
#     print("="*60)
#     print("Available endpoints:")
#     print("  POST /predict - Full risk and advice prediction")
#     print("  POST /predict-risk-only - Risk prediction only")
#     print("  GET  /model-info - Model information")
#     print("  POST /batch-predict - Batch predictions")
#     print("  GET  /health - Health check")
#     print("="*60)
    
#     # Get configuration from environment
#     host = os.environ.get('HOST', '0.0.0.0')
#     port = int(os.environ.get('PORT', 5000))
#     debug = os.environ.get('FLASK_ENV', 'default') == 'development'
    
#     app.run(debug=debug, host=host, port=port)

# if __name__ == '__main__':
#     main()