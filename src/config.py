"""
Configurazione per GitHub App deployment
"""
import os

class Config:
    """Configurazione base"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')
    APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:3000')

    # Database (opzionale)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class ProductionConfig(Config):
    """Configurazione produzione"""
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    """Configurazione sviluppo"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Configurazione test"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'

# Selezione configurazione basata su ambiente
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
