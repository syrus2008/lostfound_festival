import os
from flask import Flask, jsonify, g, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlalchemy
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=100000, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Création de l'application
app = Flask(__name__)

# Configuration de l'application
app.config.from_object('config.ProductionConfig')
try:
    app.config.from_object('config.DevelopmentConfig')
    logger.info("Configuration de développement chargée")
except:
    logger.info("Configuration de production chargée")

# Configuration du proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

# Configuration de Talisman pour les en-têtes de sécurité
csp = {
    'default-src': ["'self'"],
    'script-src': ["'self'"],
    'style-src': ["'self'"],
    'img-src': ["'self'"],
    'font-src': ["'self'"],
    'connect-src': ["'self'"]
}

talisman = Talisman(
    app,
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    content_security_policy=csp,
    content_security_policy_nonce_in=['script-src']
)

# Configuration du rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration des dossiers
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Vérification des permissions des dossiers
for folder in [app.config['UPLOAD_FOLDER']]:
    if not os.access(folder, os.W_OK):
        logger.error(f"Le dossier {folder} n'est pas accessible en écriture")
        raise PermissionError(f"Le dossier {folder} n'est pas accessible en écriture")

# Initialisation des extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.auth'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"  # Protection contre le vol de session

# Configuration du nombre maximum de tentatives de connexion
MAX_LOGIN_ATTEMPTS = app.config.get('MAX_LOGIN_ATTEMPTS', 5)
LOCKOUT_TIME = app.config.get('LOCKOUT_TIME', 15)  # minutes

# Import models and create tables
import models
from models import User
with app.app_context():
    db.create_all()
    # Création sécurisée de la table headphone_loans si elle n'existe pas déjà
    try:
        engine = db.get_engine()
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text('''
                CREATE TABLE IF NOT EXISTS headphone_loans (
                    id SERIAL PRIMARY KEY,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    deposit_type VARCHAR(20) NOT NULL,
                    deposit_details VARCHAR(200),
                    quantity INTEGER NOT NULL DEFAULT 1,
                    deposit_amount NUMERIC(10,2),
                    loan_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    return_date TIMESTAMP,
                    signature TEXT
                )
            '''))
            # Ajout automatique des colonnes manquantes (Railway, PostgreSQL)
            # Ajoute quantity si manquant
            result = conn.execute(sqlalchemy.text("""
                SELECT column_name FROM information_schema.columns WHERE table_name='headphone_loans' AND column_name='quantity'
            """))
            if result.fetchone() is None:
                conn.execute(sqlalchemy.text("ALTER TABLE headphone_loans ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1;"))
                conn.execute(sqlalchemy.text("COMMIT;"))
            # Ajoute deposit_amount si manquant
            result = conn.execute(sqlalchemy.text("""
                SELECT column_name FROM information_schema.columns WHERE table_name='headphone_loans' AND column_name='deposit_amount'
            """))
            if result.fetchone() is None:
                conn.execute(sqlalchemy.text("ALTER TABLE headphone_loans ADD COLUMN deposit_amount NUMERIC(10,2);"))
                conn.execute(sqlalchemy.text("COMMIT;"))
            # Ajoute status si manquant
            result = conn.execute(sqlalchemy.text("""
                SELECT column_name FROM information_schema.columns WHERE table_name='headphone_loans' AND column_name='status'
            """))
            if result.fetchone() is None:
                conn.execute(sqlalchemy.text("ALTER TABLE headphone_loans ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active';"))
                conn.execute(sqlalchemy.text("COMMIT;"))
            # Ajoute previous_status si manquant
            result = conn.execute(sqlalchemy.text("""
                SELECT column_name FROM information_schema.columns WHERE table_name='headphone_loans' AND column_name='previous_status'
            """))
            if result.fetchone() is None:
                conn.execute(sqlalchemy.text("ALTER TABLE headphone_loans ADD COLUMN previous_status VARCHAR(20);"))
                conn.execute(sqlalchemy.text("COMMIT;"))
    except Exception as e:
        import sys
        print(f"[WARN] Impossible de créer la table headphone_loans automatiquement : {e}", file=sys.stderr)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'utilisateur {user_id}: {str(e)}")
        return None

# Middleware pour ajouter des en-têtes de sécurité
@app.after_request
def add_security_headers(response):
    # Ajout des en-têtes de sécurité
    for header, value in app.config.get('SECURITY_HEADERS', {}).items():
        if header == 'Content-Security-Policy' and 'Content-Security-Policy' in response.headers:
            continue
        response.headers[header] = value
    
    # Protection contre le clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Protection contre le MIME-sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Protection contre XSS
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HSTS
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Suppression des en-têtes sensibles
    sensitive_headers = [
        'Server', 'X-Powered-By', 'X-AspNet-Version', 'X-AspNetMvc-Version'
    ]
    for header in sensitive_headers:
        if header in response.headers:
            del response.headers[header]
    
    return response

# Gestionnaire d'erreurs
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# Enregistrement des blueprints
try:
    import views
    app.register_blueprint(views.bp)
    
    import admin
    app.register_blueprint(admin.bp_admin)
    
    logger.info("Blueprints chargés avec succès")
except Exception as e:
    logger.error(f"Erreur lors du chargement des blueprints: {str(e)}")
    raise

# Protection contre les attaques par force brute
def check_brute_force():
    """Vérifie si l'utilisateur a dépassé le nombre de tentatives de connexion."""
    if 'login_attempts' not in session:
        session['login_attempts'] = 0
        session['first_attempt'] = datetime.utcnow().timestamp()
    
    now = datetime.utcnow().timestamp()
    time_since_first_attempt = now - session.get('first_attempt', now)
    
    # Réinitialiser le compteur après LOCKOUT_TIME minutes
    if time_since_first_attempt > LOCKOUT_TIME * 60:
        session['login_attempts'] = 0
        session['first_attempt'] = now
    
    # Bloquer après MAX_LOGIN_ATTEMPTS tentatives
    if session['login_attempts'] >= MAX_LOGIN_ATTEMPTS:
        remaining_time = int((LOCKOUT_TIME * 60 - time_since_first_attempt) / 60) + 1
        return f"Trop de tentatives de connexion. Veuillez réessayer dans {remaining_time} minutes."
    
    return None

# Décorateur pour limiter les tentatives de connexion
def login_required_with_brute_force(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            error = check_brute_force()
            if error:
                flash(error, 'danger')
                return redirect(url_for('main.auth'))
            session['login_attempts'] = session.get('login_attempts', 0) + 1
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('main.auth'))
        return f(*args, **kwargs)
    return decorated_function

if __name__ == '__main__':
    # Vérification des variables d'environnement critiques
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
    
    # Démarrage du serveur
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        ssl_context='adhoc' if app.config.get('ENV') == 'production' else None,
        debug=app.config.get('DEBUG', False)
    )
