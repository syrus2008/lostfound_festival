import os
import re
import logging
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

class SecurityUtils:
    """
    Classe utilitaire pour les fonctions de sécurité communes.
    """
    
    # Expressions régulières pour la validation
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$'
    
    @staticmethod
    def generate_secure_token(length=32):
        """
        Génère un jeton sécurisé aléatoire.
        
        Args:
            length (int): Longueur du jeton en octets
            
        Returns:
            str: Jeton sécurisé encodé en hexadécimal
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_salt(length=16):
        """
        Génère un sel aléatoire pour le hachage des mots de passe.
        
        Args:
            length (int): Longueur du sel en octets
            
        Returns:
            str: Sel encodé en hexadécimal
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_password(password, salt=None):
        """
        Hache un mot de passe avec un sel.
        
        Args:
            password (str): Mot de passe en clair
            salt (str, optional): Sel à utiliser. Si None, un nouveau sel est généré.
            
        Returns:
            tuple: (hash, salt)
        """
        if salt is None:
            salt = SecurityUtils.generate_salt()
        
        # Utilisation de PBKDF2 avec SHA-256
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Nombre d'itérations
        )
        
        return dk.hex(), salt
    
    @staticmethod
    def verify_password(stored_hash, provided_password, salt):
        """
        Vérifie si un mot de passe correspond à un hachage stocké.
        
        Args:
            stored_hash (str): Hachage stocké
            provided_password (str): Mot de passe fourni
            salt (str): Sel utilisé pour le hachage
            
        Returns:
            bool: True si le mot de passe est valide, False sinon
        """
        new_hash, _ = SecurityUtils.hash_password(provided_password, salt)
        return hmac.compare_digest(stored_hash, new_hash)
    
    @staticmethod
    def validate_email(email):
        """
        Valide une adresse email.
        
        Args:
            email (str): Adresse email à valider
            
        Returns:
            bool: True si l'email est valide, False sinon
        """
        if not email or not isinstance(email, str):
            return False
        
        return re.match(SecurityUtils.EMAIL_REGEX, email) is not None
    
    @staticmethod
    def validate_password_strength(password):
        """
        Vérifie la force d'un mot de passe.
        
        Args:
            password (str): Mot de passe à vérifier
            
        Returns:
            tuple: (is_valid, message)
        """
        if not password or not isinstance(password, str):
            return False, "Le mot de passe ne peut pas être vide"
        
        if len(password) < 12:
            return False, "Le mot de passe doit contenir au moins 12 caractères"
        
        if not re.search(r'[a-z]', password):
            return False, "Le mot de passe doit contenir au moins une minuscule"
        
        if not re.search(r'[A-Z]', password):
            return False, "Le mot de passe doit contenir au moins une majuscule"
        
        if not re.search(r'\d', password):
            return False, "Le mot de passe doit contenir au moins un chiffre"
        
        if not re.search(r'[^A-Za-z0-9]', password):
            return False, "Le mot de passe doit contenir au moins un caractère spécial"
        
        # Vérification des mots de passe courants
        common_passwords = [
            'password', '123456', 'qwerty', 'azerty', 'password123',
            'admin', 'welcome', '123456789', '12345678', '12345'
        ]
        
        if password.lower() in common_passwords:
            return False, "Ce mot de passe est trop courant"
        
        return True, ""
    
    @staticmethod
    def generate_csrf_token():
        """
        Génère un jeton CSRF sécurisé.
        
        Returns:
            str: Jeton CSRF
        """
        if '_csrf_token' not in g:
            g._csrf_token = secrets.token_urlsafe(32)
        return g._csrf_token
    
    @staticmethod
    def verify_csrf_token(token):
        """
        Vérifie un jeton CSRF.
        
        Args:
            token (str): Jeton à vérifier
            
        Returns:
            bool: True si le jeton est valide, False sinon
        """
        if not token:
            return False
        
        stored_token = g.get('_csrf_token')
        if not stored_token:
            return False
        
        return hmac.compare_digest(token, stored_token)
    
    @staticmethod
    def generate_jwt_token(payload, secret_key=None, expires_in=3600):
        """
        Génère un jeton JWT.
        
        Args:
            payload (dict): Données à inclure dans le jeton
            secret_key (str, optional): Clé secrète pour signer le jeton
            expires_in (int, optional): Durée de validité en secondes
            
        Returns:
            str: Jeton JWT encodé
        """
        if secret_key is None:
            secret_key = current_app.config.get('SECRET_KEY')
        
        # Ajout de la date d'expiration
        payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
        payload['iat'] = datetime.utcnow()
        
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token, secret_key=None):
        """
        Vérifie un jeton JWT.
        
        Args:
            token (str): Jeton à vérifier
            secret_key (str, optional): Clé secrète pour vérifier le jeton
            
        Returns:
            tuple: (is_valid, payload)
        """
        if secret_key is None:
            secret_key = current_app.config.get('SECRET_KEY')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return True, payload
        except jwt.ExpiredSignatureError:
            return False, 'Le jeton a expiré'
        except jwt.InvalidTokenError:
            return False, 'Jeton invalide'
    
    @staticmethod
    def sanitize_input(input_str, max_length=1000):
        """
        Nettoie une chaîne de caractères pour prévenir les injections.
        
        Args:
            input_str (str): Chaîne à nettoyer
            max_length (int): Longueur maximale autorisée
            
        Returns:
            str: Chaîne nettoyée
        """
        if not input_str:
            return ''
        
        # Suppression des espaces en début et fin
        sanitized = input_str.strip()
        
        # Limitation de la longueur
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Échappement des caractères spéciaux
        sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')
        
        return sanitized
    
    @staticmethod
    def is_safe_redirect(target):
        """
        Vérifie si une URL de redirection est sûre.
        
        Args:
            target (str): URL de redestination
            
        Returns:
            bool: True si l'URL est sûre, False sinon
        """
        if not target:
            return False
        
        # Vérification des redirections vers des domaines externes
        from urllib.parse import urlparse, urljoin
        
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        
        return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
    
    @staticmethod
    def rate_limit(key_func, limit="200 per day", error_message=None):
        """
        Décorateur pour limiter le taux de requêtes.
        
        Args:
            key_func: Fonction pour générer une clé unique par requête
            limit (str): Limite de requêtes (ex: '100 per day')
            error_message (str, optional): Message d'erreur personnalisé
            
        Returns:
            function: Décorateur
        """
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        
        limiter = Limiter(
            key_func=key_func or get_remote_address,
            default_limits=[limit]
        )
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    with limiter.limit(
                        limit,
                        key_func=key_func or get_remote_address,
                        error_message=error_message or 'Trop de requêtes. Veuillez réessayer plus tard.'
                    ):
                        return f(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Rate limit dépassé: {str(e)}")
                    return jsonify({
                        'error': 'Trop de requêtes. Veuillez réessayer plus tard.'
                    }), 429
            
            return decorated_function
        return decorator

# Instance globale pour une utilisation facile
security = SecurityUtils()
