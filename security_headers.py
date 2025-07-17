from flask import request, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def add_security_headers(response):
    """
    Ajoute des en-têtes de sécurité HTTP à la réponse.
    """
    security_headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': "camera=(), microphone=(), geolocation=()",
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-site',
        'Cross-Origin-Embedder-Policy': 'require-corp',
    }
    
    # Ajout de Content-Security-Policy
    csp = """
        default-src 'self';
        script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;
        style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
        img-src 'self' data: https:;
        font-src 'self' https://fonts.gstatic.com;
        connect-src 'self';
        frame-ancestors 'self';
        form-action 'self';
        base-uri 'self';
    """
    
    # Remplace les sauts de ligne et les espaces multiples
    csp = ' '.join(csp.split())
    security_headers['Content-Security-Policy'] = csp
    
    # Ajout de Feature-Policy
    security_headers['Feature-Policy'] = "\n".join([
        "accelerometer 'none'",
        "camera 'none'",
        "geolocation 'none'",
        "gyroscope 'none'",
        "magnetometer 'none'",
        "microphone 'none'",
        "payment 'none'",
        "usb 'none'"
    ])
    
    # Ajout des en-têtes à la réponse
    for header, value in security_headers.items():
        response.headers[header] = value
    
    # HSTS - Strict-Transport-Security (uniquement en HTTPS)
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    return response

def rate_limit(limit="200 per day", key_func=None):
    """
    Décorateur pour limiter le taux de requêtes.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(current_app, 'limiter'):
                return f(*args, **kwargs)
            
            # Vérification du rate limiting
            try:
                with current_app.limiter.limit(
                    limit,
                    key_func=key_func,
                    error_message='Trop de requêtes. Veuillez réessayer plus tard.'
                ):
                    return f(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Rate limit dépassé: {str(e)}")
                return {"error": "Trop de requêtes. Veuillez réessayer plus tard."}, 429
        
        return decorated_function
    return decorator

def csrf_protect():
    """
    Vérifie le jeton CSRF pour les requêtes non-GET.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
                csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
                if not csrf_token or not current_app.extensions.get('csrf').verify(csrf_token):
                    logger.warning("Échec de la validation CSRF")
                    return {"error": "Jeton CSRF invalide ou manquant"}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def secure_headers(f):
    """
    Décorateur pour ajouter des en-têtes de sécurité aux réponses.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        return add_security_headers(response)
    return decorated_function

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
