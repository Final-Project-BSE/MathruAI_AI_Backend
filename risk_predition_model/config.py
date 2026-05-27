import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise ValueError(f"{name} is required but not found in environment variables")
    return value


def _get_int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return int(default)


class Config:
    """Base configuration"""

    def __init__(self):
        self.JWT_SECRET_KEY = _get_env("JWT_SECRET_KEY", required=True)

        self.MYSQL_USER = _get_env("MYSQL_USER", "root")
        self.MYSQL_PASSWORD = _get_env("MYSQL_PASSWORD", required=True)
        self.MYSQL_HOST = _get_env("MYSQL_HOST", "localhost")
        self.MYSQL_PORT = _get_int_env("MYSQL_PORT", 3306)
        self.MYSQL_DATABASE = _get_env("MYSQL_DATABASE", "mathruai_database")

        self.MODEL_PATH = _get_env(
            "MODEL_PATH",
            "risk_predition_model/model/maternal_risk_advice_model.pkl"
        )
        self.DATA_DIR = _get_env("DATA_DIR", "data")

        self.MAX_BATCH_SIZE = _get_int_env("MAX_BATCH_SIZE", 100)
        self.REQUEST_TIMEOUT = _get_int_env("REQUEST_TIMEOUT", 30)
        self.LOG_LEVEL = _get_env("LOG_LEVEL", "INFO")

        self.MODEL_CONFIG = {
            "test_size": 0.2,
            "random_state": 42,
            "cv_folds": 5,
            "n_jobs": -1
        }

        self.REQUIRED_FEATURES = {
            "Age": {"type": "numeric", "min": 12, "max": 50, "description": "Age in years"},
            "SystolicBP": {"type": "numeric", "min": 70, "max": 200, "description": "Systolic blood pressure"},
            "DiastolicBP": {"type": "numeric", "min": 40, "max": 120, "description": "Diastolic blood pressure"},
            "BS": {"type": "numeric", "min": 50, "max": 300, "description": "Blood sugar level"},
            "BodyTemp": {"type": "numeric", "min": 95, "max": 105, "description": "Body temperature in Fahrenheit"},
            "BMI": {"type": "numeric", "min": 12, "max": 50, "description": "Body Mass Index"},
            "HeartRate": {"type": "numeric", "min": 40, "max": 150, "description": "Heart rate per minute"}
        }

        self.OPTIONAL_FEATURES = {
            "PreviousComplications": {"type": "binary", "values": [0, 1], "description": "0=No, 1=Yes"},
            "PreexistingDiabetes": {"type": "binary", "values": [0, 1], "description": "0=No, 1=Yes"},
            "GestationalDiabetes": {"type": "binary", "values": [0, 1], "description": "0=No, 1=Yes"},
            "MentalHealth": {"type": "binary", "values": [0, 1], "description": "0=No concerns, 1=Has concerns"}
        }

        self.RISK_LEVEL_COLUMN = "RiskLevel"
        self.HEALTH_ADVICE_COLUMN = "HealthAdvice"


class DevelopmentConfig(Config):
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.FLASK_ENV = "development"
        self.LOG_LEVEL = "DEBUG"
        self.MAX_BATCH_SIZE = 200


class ProductionConfig(Config):
    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.FLASK_ENV = "production"
        self.MAX_BATCH_SIZE = 50
        self.REQUEST_TIMEOUT = 15


class TestingConfig(Config):
    def __init__(self):
        super().__init__()
        self.TESTING = True
        self.DEBUG = True
        self.MYSQL_DATABASE = _get_env("MYSQL_TEST_DATABASE", "maternal_health_test")
        self.MODEL_PATH = "test/test_model.pkl"
        self.DATA_DIR = "test/data"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


def get_config():
    env = os.getenv("FLASK_ENV", "default")
    config_class = config.get(env, config["default"])
    return config_class()