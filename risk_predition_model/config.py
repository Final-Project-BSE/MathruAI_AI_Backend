"""
Simplified configuration for maternal risk prediction system.
Direct MySQL connection - No SQLAlchemy.
"""
import os


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd'
    
    # MySQL Configuration
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '20000624')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'mathruai_database')
    
    # Model paths
    MODEL_PATH = os.environ.get('MODEL_PATH') or 'model/maternal_risk_advice_model.pkl'
    
    # Data paths
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    
    # API configuration
    MAX_BATCH_SIZE = int(os.environ.get('MAX_BATCH_SIZE', 100))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Model training parameters
    MODEL_CONFIG = {
        'test_size': 0.2,
        'random_state': 42,
        'cv_folds': 5,
        'n_jobs': -1
    }
    
    # Expected input features and their types
    REQUIRED_FEATURES = {
        'Age': {'type': 'numeric', 'min': 12, 'max': 50, 'description': 'Age in years'},
        'SystolicBP': {'type': 'numeric', 'min': 70, 'max': 200, 'description': 'Systolic blood pressure'},
        'DiastolicBP': {'type': 'numeric', 'min': 40, 'max': 120, 'description': 'Diastolic blood pressure'},
        'BS': {'type': 'numeric', 'min': 50, 'max': 300, 'description': 'Blood sugar level'},
        'BodyTemp': {'type': 'numeric', 'min': 95, 'max': 105, 'description': 'Body temperature in Fahrenheit'},
        'BMI': {'type': 'numeric', 'min': 12, 'max': 50, 'description': 'Body Mass Index'},
        'HeartRate': {'type': 'numeric', 'min': 40, 'max': 150, 'description': 'Heart rate per minute'}
    }
    
    OPTIONAL_FEATURES = {
        'PreviousComplications': {'type': 'binary', 'values': [0, 1], 'description': '0=No, 1=Yes'},
        'PreexistingDiabetes': {'type': 'binary', 'values': [0, 1], 'description': '0=No, 1=Yes'},
        'GestationalDiabetes': {'type': 'binary', 'values': [0, 1], 'description': '0=No, 1=Yes'},
        'MentalHealth': {'type': 'binary', 'values': [0, 1], 'description': '0=No concerns, 1=Has concerns'}
    }
    
    # Target columns in dataset
    RISK_LEVEL_COLUMN = 'RiskLevel'
    HEALTH_ADVICE_COLUMN = 'HealthAdvice'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'
    MAX_BATCH_SIZE = 200


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    MAX_BATCH_SIZE = 50
    REQUEST_TIMEOUT = 15


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    MYSQL_DATABASE = os.environ.get('MYSQL_TEST_DATABASE', 'maternal_health_test')
    MODEL_PATH = 'test/test_model.pkl'
    DATA_DIR = 'test/data'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get the current configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])