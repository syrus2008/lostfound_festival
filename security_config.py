import os
import logging
from datetime import timedelta

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityConfig:
    """
    Classe de configuration pour la sécurité de l'application.
    """
    
    # Clé secrète - DOIT être définie dans les variables d'environnement
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        logger.warning("Aucune SECRET_KEY définie. Utilisation d'une valeur par défaut non sécurisée.")
        SECRET_KEY = 'dev-key-insecure-change-in-production'
    
    # Configuration de la base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("La variable d'environnement DATABASE_URL doit être définie")
    
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
    
    # Configuration JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Configuration CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    
    # Configuration du taux de requêtes
    RATE_LIMIT_DEFAULT = "200 per day"
    RATE_LIMIT_AUTH = "10 per minute"
    
    # Configuration des en-têtes de sécurité
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                                 "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                 "font-src 'self' data:; connect-src 'self';"
    }
    
    # Configuration du mot de passe
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_NUMBER = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Configuration des logs
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'security.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    # Configuration du serveur
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    # Configuration SSL/TLS
    SSL_ENABLED = os.environ.get('SSL_ENABLED', 'false').lower() == 'true'
    SSL_CERT = os.environ.get('SSL_CERT')
    SSL_KEY = os.environ.get('SSL_KEY')
    
    # Configuration de l'email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Configuration de l'administrateur
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # Configuration de la base de données
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
    DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 10))
    DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
    DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 1800))
    
    @classmethod
    def init_app(cls, app):
        """Initialise l'application avec la configuration de sécurité."""
        # Configuration de base
        app.config.from_object(cls)
        
        # Configuration spécifique à l'environnement
        env = os.environ.get('FLASK_ENV', 'production')
        if env == 'development':
            cls._configure_development(app)
        elif env == 'testing':
            cls._configure_testing(app)
        else:
            cls._configure_production(app)
        
        # Configuration des dossiers
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        
        # Vérification des permissions des dossiers
        cls._check_folder_permissions()
        
        # Configuration des logs
        cls._configure_logging(app)
        
        logger.info(f"Configuration de sécurité initialisée pour l'environnement: {env}")
    
    @classmethod
    def _configure_development(cls, app):
        """Configuration pour l'environnement de développement."""
        app.config['DEBUG'] = True
        app.config['SQLALCHEMY_ECHO'] = True
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SECRET_KEY'] = 'dev-key-insecure-change-in-production'
        
        # Désactive la protection CSRF en développement pour faciliter les tests
        app.config['WTF_CSRF_ENABLED'] = False
        
        logger.info("Configuration de développement activée")
    
    @classmethod
    def _configure_testing(cls, app):
        """Configuration pour l'environnement de test."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-key-insecure'
        
        logger.info("Configuration de test activée")
    
    @classmethod
    def _configure_production(cls, app):
        """Configuration pour l'environnement de production."""
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        # Force l'utilisation de HTTPS
        app.config['USE_X_SENDFILE'] = True
        
        # Désactive le mode debug
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        logger.info("Configuration de production activée")
    
    @classmethod
    def _check_folder_permissions(cls):
        """Vérifie les permissions des dossiers critiques."""
        folders_to_check = [
            cls.UPLOAD_FOLDER,
            os.path.dirname(os.path.abspath(__file__))
        ]
        
        for folder in folders_to_check:
            if not os.path.exists(folder):
                os.makedirs(folder, mode=0o750, exist_ok=True)
                logger.info(f"Dossier créé: {folder}")
            
            # Vérification des permissions
            if not os.access(folder, os.W_OK):
                logger.error(f"Le dossier {folder} n'est pas accessible en écriture")
            if not os.access(folder, os.R_OK):
                logger.error(f"Le dossier {folder} n'est pas accessible en lecture")
    
    @classmethod
    def _configure_logging(cls, app):
        """Configure la journalisation de l'application."""
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Création du gestionnaire de fichiers
        file_handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT
        )
        
        # Configuration du format des logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Configuration du niveau de log
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Ajout du gestionnaire au logger racine
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Désactivation du log du serveur Werkzeug
        if not app.debug:
            logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        logger.info("Journalisation configurée")

# Instance de configuration pour une utilisation facile
config = SecurityConfig()
