import os
from datetime import timedelta

class Config:
    # Clé secrète - DOIT être définie dans les variables d'environnement
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY doit être définie dans les variables d'environnement")
        
    # Configuration de la base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL doit être définie dans les variables d'environnement")
        
    # Désactive le suivi des modifications SQLAlchemy pour améliorer les performances
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuration de la sécurité
    SESSION_COOKIE_SECURE = True  # Cookies uniquement sur HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protection contre CSRF
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Durée de session de 2 heures
    
    # Protection contre les attaques par force brute
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 15  # minutes
    
    # Configuration des uploads
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # 30 MB
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Headers de sécurité HTTP
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                                 "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                 "font-src 'self' data:; connect-src 'self';"
    }

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Désactivé en développement pour faciliter les tests

class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
