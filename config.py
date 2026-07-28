import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'camphor-system-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///camphor_tree.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    MODEL_UPDATE_INTERVAL = 24 * 60 * 60

    PASSWORD_MIN_LENGTH = 8
    LOGIN_ATTEMPTS_LIMIT = 5
    LOCKOUT_DURATION = 3600

    RANDOM_SEED = 42

    MODEL_BASE_CONFIG = {
        'small_threshold': 20,
        'medium_threshold': 100,
        'cv_min_samples': 6,
        'cv_folds': 3,
        'test_min_samples': 10,
        'test_size': 0.2,
    }

    GROWTH_MODEL = {
        'small_sample_params': {
            'n_estimators': 50,
            'max_depth': 4,
            'min_samples_split': 2,
            'min_samples_leaf': 2,
        },
        'medium_sample_params': {
            'n_estimators': 100,
            'max_depth': 8,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
        },
        'large_sample_params': {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
        },
        **MODEL_BASE_CONFIG,
    }

    CARBON_MODEL = {
        'small_sample_params': {
            'n_estimators': 50,
            'max_depth': 3,
            'learning_rate': 0.1,
            'min_samples_split': 2,
            'min_samples_leaf': 2,
            'subsample': 0.8,
        },
        'medium_sample_params': {
            'n_estimators': 150,
            'max_depth': 5,
            'learning_rate': 0.1,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'subsample': 0.8,
        },
        'large_sample_params': {
            'n_estimators': 300,
            'max_depth': 6,
            'learning_rate': 0.1,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'subsample': 0.8,
        },
        **MODEL_BASE_CONFIG,
    }

    FEATURE_ENGINEERING = {
        'growth_features': [
            'total_precipitation', 'avg_humidity', 'avg_wind_speed',
            'altitude', 'tree_height', 'carbon_per_age',
            'hydro_thermal_index', 'wind_altitude_interaction',
            'basal_area', 'heat_humidity_index',
        ],
        'carbon_features': [
            'tree_age', 'dbh', 'tree_height',
            'soil_compactness_encoded', 'avg_humidity',
            'basal_area', 'slenderness_ratio', 'carbon_age_ratio',
        ],
        'soil_mapping': {'疏松': 0, '中等': 1, '紧密': 2, '较疏松': 0},
    }


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}