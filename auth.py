import logging
from functools import wraps
from flask import request, jsonify, current_app, session
from flask_login import current_user
from datetime import datetime, timedelta
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

class AuthError(Exception):
    """Exception personnalisée pour les erreurs d'authentification."""
    def __init__(self, message, status_code=401, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv

def generate_token(user_id, is_admin=False):
    """
    Génère un jeton JWT pour l'utilisateur.
    """
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': user_id,
            'is_admin': is_admin,
            'jti': str(uuid.uuid4())  # Identifiant unique pour le jeton
        }
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération du jeton: {str(e)}")
        raise AuthError("Impossible de générer un jeton d'authentification")

def verify_token(token):
    """
    Vérifie un jeton JWT et renvoie les informations de l'utilisateur.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config.get('SECRET_KEY'),
            algorithms=['HS256']
        )
        return {
            'user_id': payload['sub'],
            'is_admin': payload.get('is_admin', False)
        }
    except jwt.ExpiredSignatureError:
        raise AuthError('Le jeton a expiré. Veuillez vous reconnecter.', 401)
    except jwt.InvalidTokenError:
        raise AuthError('Jeton invalide. Veuillez vous reconnecter.', 401)
    except Exception as e:
        logger.error(f"Erreur de validation du jeton: {str(e)}")
        raise AuthError('Impossible de valider le jeton d\'authentification', 401)

def token_required(f):
    """
    Décorateur pour protéger les routes nécessitant une authentification par jeton.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Vérifier le jeton dans l'en-tête Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                raise AuthError('Format de jeton invalide. Utilisez: Bearer <token>', 401)
        
        if not token:
            raise AuthError('Jeton d\'authentification manquant', 401)
        
        try:
            data = verify_token(token)
            # Stocker les informations de l'utilisateur dans g pour un accès facile
            g.current_user_id = data['user_id']
            g.is_admin = data['is_admin']
        except AuthError as e:
            return jsonify(e.to_dict()), e.status_code
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Décorateur pour les routes nécessitant des privilèges d'administrateur.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({
                'message': 'Accès refusé. Privilèges administrateur requis.',
                'status_code': 403
            }), 403
        return f(*args, **kwargs)
    return decorated

def track_login_attempts():
    """
    Suit les tentatives de connexion pour prévenir les attaques par force brute.
    """
    if 'login_attempts' not in session:
        session['login_attempts'] = 0
        session['first_attempt'] = datetime.utcnow().isoformat()
    
    session['login_attempts'] += 1
    
    # Vérifier si le nombre maximal de tentatives a été atteint
    max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
    lockout_time = current_app.config.get('LOCKOUT_TIME', 15)  # minutes
    
    if session['login_attempts'] >= max_attempts:
        first_attempt = datetime.fromisoformat(session['first_attempt'])
        time_elapsed = (datetime.utcnow() - first_attempt).total_seconds()
        
        # Vérifier si le temps de verrouillage est écoulé
        if time_elapsed < (lockout_time * 60):
            remaining_time = int((lockout_time * 60 - time_elapsed) / 60) + 1
            raise AuthError(
                f'Trop de tentatives de connexion. Veuillez réessayer dans {remaining_time} minutes.',
                429
            )
        else:
            # Réinitialiser le compteur si le temps de verrouillage est écoulé
            session['login_attempts'] = 1
            session['first_attempt'] = datetime.utcnow().isoformat()
    
    return True

def password_complexity_check(password):
    """
    Vérifie la complexité d'un mot de passe.
    """
    if len(password) < 12:
        return False, "Le mot de passe doit contenir au moins 12 caractères."
    
    if not any(char.isdigit() for char in password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    
    if not any(char.isupper() for char in password):
        return False, "Le mot de passe doit contenir au moins une lettre majuscule."
    
    if not any(char.islower() for char in password):
        return False, "Le mot de passe doit contenir au moins une lettre minuscule."
    
    if not any(not char.isalnum() for char in password):
        return False, "Le mot de passe doit contenir au moins un caractère spécial."
    
    # Vérifier si le mot de passe est dans une liste de mots de passe courants
    common_passwords = ['password', '123456', 'qwerty', 'azerty', 'password123']
    if password.lower() in common_passwords:
        return False, "Ce mot de passe est trop courant. Veuillez en choisir un autre."
    
    return True, ""

def hash_password(password):
    """
    Hache un mot de passe de manière sécurisée.
    """
    return generate_password_hash(
        password,
        method='pbkdf2:sha256',
        salt_length=16
    )

def verify_password(stored_password, provided_password):
    """
    Vérifie si le mot de passe fourni correspond au hachage stocké.
    """
    return check_password_hash(stored_password, provided_password)

def generate_csrf_token():
    """
    Génère un jeton CSRF sécurisé.
    """
    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid.uuid4())
    return session['_csrf_token']

def verify_csrf_token(token):
    """
    Vérifie si le jeton CSRF fourni est valide.
    """
    if '_csrf_token' not in session:
        return False
    return token == session['_csrf_token']
