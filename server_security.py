import os
import logging
from functools import wraps
from flask import request, jsonify, current_app, g
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_talisman import Talisman
import ssl
from datetime import timedelta

logger = logging.getLogger(__name__)

class SecurityHeaders:
    """
    Classe pour gérer les en-têtes de sécurité HTTP.
    """
    def __init__(self, app=None):
        self.app = app
        self.talisman = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise la configuration de sécurité."""
        self.app = app
        
        # Configuration par défaut
        app.config.setdefault('SECURE_HEADERS', {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': "camera=(), microphone=(), geolocation=()",
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-site',
            'Cross-Origin-Embedder-Policy': 'require-corp',
        })
        
        # Configuration CSP
        app.config.setdefault('CSP_POLICY', {
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'"  # Nécessaire pour certaines bibliothèques
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'"
            ],
            'img-src': [
                "'self'",
                'data:',
                'https:'
            ],
            'font-src': [
                "'self'",
                'data:'
            ],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'self'"],
            'form-action': ["'self'"],
            'base-uri': ["'self'"],
        })
        
        # Configuration de Talisman
        self._configure_talisman()
        
        # Configuration du proxy
        self._configure_proxy()
        
        # Configuration SSL/TLS
        self._configure_ssl()
        
        # Enregistrement des gestionnaires
        self._register_handlers()
    
    def _configure_talisman(self):
        """Configure Talisman pour les en-têtes de sécurité."""
        self.talisman = Talisman(
            self.app,
            force_https=True,
            strict_transport_security=True,
            session_cookie_secure=True,
            content_security_policy=self.app.config['CSP_POLICY'],
            content_security_policy_nonce_in=['script-src']
        )
    
    def _configure_proxy(self):
        """Configure le support des proxies inversés."""
        if self.app.config.get('BEHIND_PROXY', False):
            self.app.wsgi_app = ProxyFix(
                self.app.wsgi_app,
                x_for=1,
                x_proto=1,
                x_host=1,
                x_prefix=1
            )
    
    def _configure_ssl(self):
        """Configure les paramètres SSL/TLS."""
        if self.app.config.get('ENABLE_SSL', False):
            self.app.config['SESSION_COOKIE_SECURE'] = True
            self.app.config['REMEMBER_COOKIE_SECURE'] = True
            self.app.config['SESSION_COOKIE_HTTPONLY'] = True
            self.app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
            
            # Configuration HSTS
            self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
    
    def _register_handlers(self):
        """Enregistre les gestionnaires de requêtes."""
        @self.app.after_request
        def add_security_headers(response):
            """Ajoute les en-têtes de sécurité à chaque réponse."""
            # Ajout des en-têtes personnalisés
            for header, value in self.app.config['SECURE_HEADERS'].items():
                if header not in response.headers:
                    response.headers[header] = value
            
            # Suppression des en-têtes sensibles
            sensitive_headers = [
                'Server', 'X-Powered-By', 'X-AspNet-Version', 'X-AspNetMvc-Version'
            ]
            for header in sensitive_headers:
                if header in response.headers:
                    del response.headers[header]
            
            return response
        
        @self.app.before_request
        def check_https():
            """Vérifie que la connexion est sécurisée en production."""
            if self.app.config.get('ENV') == 'production' and not request.is_secure:
                if request.headers.get('X-Forwarded-Proto') != 'https':
                    return jsonify({
                        'error': 'HTTPS est requis pour cette application.'
                    }), 400

def ssl_required(f):
    """
    Décorateur pour forcer l'utilisation de HTTPS.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.scheme != 'https' and current_app.config.get('ENV') == 'production':
            return jsonify({
                'error': 'HTTPS est requis pour cette ressource.'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def cors_headers(origin=None, methods=None, headers=None, max_age=21600):
    """
    Décorateur pour gérer les en-têtes CORS.
    """
    if methods is None:
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    if headers is None:
        headers = ['Content-Type', 'Authorization']
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method == 'OPTIONS':
                response = current_app.make_default_options_response()
            else:
                response = f(*args, **kwargs)
            
            # Ajout des en-têtes CORS
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = ', '.join(methods)
            response.headers['Access-Control-Allow-Headers'] = ', '.join(headers)
            response.headers['Access-Control-Max-Age'] = str(max_age)
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            return response
        return wrapped
    return decorator

def rate_limit(limit="200 per day", key_func=None, error_message=None):
    """
    Décorateur pour limiter le taux de requêtes.
    """
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    if key_func is None:
        key_func = get_remote_address
    
    limiter = Limiter(
        key_func=key_func,
        default_limits=[limit],
        storage_uri="memory://"
    )
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                with limiter.limit(
                    limit,
                    key_func=key_func,
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

def content_security_policy(policy=None):
    """
    Décorateur pour définir une politique de sécurité du contenu personnalisée.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            if policy:
                response.headers['Content-Security-Policy'] = policy
            return response
        return decorated_function
    return decorator

def security_headers(f):
    """
    Décorateur pour ajouter des en-têtes de sécurité aux réponses.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # En-têtes de sécurité de base
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        # Ajout des en-têtes à la réponse
        for header, value in headers.items():
            if header not in response.headers:
                response.headers[header] = value
        
        return response
    return decorated_function
