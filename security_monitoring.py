import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import os
import sys
from datetime import datetime
from functools import wraps
from flask import request, current_app, g
import json
from werkzeug.security import generate_password_hash
import hashlib

# Configuration du logger
logger = logging.getLogger('security')
logger.setLevel(logging.INFO)

# Création des gestionnaires de logs
file_handler = RotatingFileHandler('security.log', maxBytes=10000, backupCount=5)
file_handler.setLevel(logging.INFO)

# Format des logs
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Gestionnaire pour envoyer des emails en cas d'erreur critique
if os.environ.get('MAIL_SERVER'):
    auth = None
    if os.environ.get('MAIL_USERNAME') or os.environ.get('MAIL_PASSWORD'):
        auth = (os.environ.get('MAIL_USERNAME'), os.environ.get('MAIL_PASSWORD'))
    
    mail_handler = SMTPHandler(
        mailhost=(os.environ.get('MAIL_SERVER'), os.environ.get('MAIL_PORT')),
        fromaddr=os.environ.get('MAIL_FROM'),
        toaddrs=os.environ.get('ADMINS', []).split(','),
        subject='Erreur de sécurité - Application Lost & Found',
        credentials=auth,
        secure=()
    )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter)
    logger.addHandler(mail_handler)

def log_security_event(event_type, details, level='info', user_id=None, request_data=None):
    """
    Enregistre un événement de sécurité dans les logs.
    
    Args:
        event_type (str): Type d'événement (ex: 'login_success', 'login_failed', 'access_denied')
        details (str): Détails de l'événement
        level (str): Niveau de sévérité ('info', 'warning', 'error', 'critical')
        user_id: ID de l'utilisateur concerné (si disponible)
        request_data: Données de la requête (si disponibles)
    """
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'level': level,
        'user_id': user_id,
        'ip': request.remote_addr if request else None,
        'user_agent': request.headers.get('User-Agent') if request else None,
        'details': details,
        'request_data': {
            'method': request.method if request else None,
            'path': request.path if request else None,
            'args': dict(request.args) if request and request.args else None,
            'form': dict(request.form) if request and request.form else None,
            'json': request.get_json(silent=True) if request else None
        } if request_data and request else None
    }
    
    # Masquer les informations sensibles
    if log_data.get('request_data', {}).get('form', {}).get('password'):
        log_data['request_data']['form']['password'] = '***REDACTED***'
    
    if log_data.get('request_data', {}).get('json', {}).get('password'):
        log_data['request_data']['json']['password'] = '***REDACTED***'
    
    # Journaliser l'événement
    log_message = json.dumps(log_data, ensure_ascii=False)
    
    if level == 'warning':
        logger.warning(log_message)
    elif level == 'error':
        logger.error(log_message)
    elif level == 'critical':
        logger.critical(log_message)
    else:
        logger.info(log_message)

def monitor_suspicious_activity():
    """
    Vérifie les activités suspectes basées sur la requête actuelle.
    """
    if not request:
        return
    
    # Détection des attaques par injection SQL
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', 'OR 1=1', ';--']
    request_str = str(request.data or '') + str(request.args or '') + str(request.form or '')
    
    for keyword in sql_keywords:
        if keyword.lower() in request_str.lower():
            log_security_event(
                'sql_injection_attempt',
                f"Tentative d'injection SQL détectée: {keyword}",
                'warning',
                user_id=getattr(g, 'user_id', None)
            )
    
    # Détection des attaques XSS
    xss_patterns = ['<script>', 'javascript:', 'onerror=', 'onload=']
    for pattern in xss_patterns:
        if pattern.lower() in request_str.lower():
            log_security_event(
                'xss_attempt',
                f"Tentative de XSS détectée: {pattern}",
                'warning',
                user_id=getattr(g, 'user_id', None)
            )

def log_authentication_attempt(username, success, ip_address=None, user_agent=None):
    """
    Enregistre une tentative d'authentification.
    """
    event_type = 'login_success' if success else 'login_failed'
    log_security_event(
        event_type,
        f"Tentative de connexion {'réussie' if success else 'échouée'} pour l'utilisateur: {username}",
        'info' if success else 'warning',
        request_data=True
    )

def log_sensitive_action(action, user_id=None, details=None):
    """
    Enregistre une action sensible effectuée par un utilisateur.
    """
    log_security_event(
        'sensitive_action',
        f"Action sensible effectuée: {action}" + (f" - {details}" if details else ""),
        'info',
        user_id=user_id,
        request_data=True
    )

def log_security_alert(alert_type, message, severity='medium'):
    """
    Enregistre une alerte de sécurité.
    """
    log_security_event(
        f'security_alert_{alert_type}',
        message,
        'warning' if severity == 'low' else 'error' if severity == 'high' else 'critical',
        request_data=True
    )

def hash_sensitive_data(data):
    """
    Hache des données sensibles avant de les logger.
    """
    if not data:
        return None
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()

class SecurityMonitor:
    """
    Classe pour surveiller et enregistrer les événements de sécurité.
    """
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialisation de l'extension."""
        # Configuration par défaut
        app.config.setdefault('SECURITY_LOG_ENABLED', True)
        
        # Enregistrement des gestionnaires de requêtes
        if not app.debug and not app.testing:
            @app.before_request
            def before_request():
                g.request_start_time = datetime.utcnow()
                g.request_id = hashlib.md5(
                    f"{datetime.utcnow()}-{request.remote_addr}-{request.path}".encode('utf-8')
                ).hexdigest()
                
                # Enregistrement de la requête
                if app.config['SECURITY_LOG_ENABLED']:
                    log_security_event(
                        'request_started',
                        f"Requête reçue: {request.method} {request.path}",
                        'info',
                        request_data=True
                    )
            
            @app.after_request
            def after_request(response):
                # Calcul du temps de traitement
                duration = (datetime.utcnow() - getattr(g, 'request_start_time', datetime.utcnow())).total_seconds()
                
                # Détection des temps de réponse anormalement longs
                if duration > 5:  # plus de 5 secondes
                    log_security_event(
                        'slow_request',
                        f"Requête lente détectée: {request.method} {request.path} a pris {duration:.2f} secondes",
                        'warning',
                        request_data=True
                    )
                
                # Détection des erreurs serveur
                if 500 <= response.status_code < 600:
                    log_security_event(
                        'server_error',
                        f"Erreur serveur {response.status_code} sur {request.method} {request.path}",
                        'error',
                        request_data=True
                    )
                
                # Enregistrement de la réponse
                if app.config['SECURITY_LOG_ENABLED']:
                    log_security_event(
                        'request_completed',
                        f"Réponse envoyée: {response.status_code} en {duration:.4f} secondes",
                        'info',
                        request_data=False
                    )
                
                return response
            
            # Gestion des erreurs
            @app.errorhandler(404)
            def page_not_found(e):
                log_security_event(
                    'page_not_found',
                    f"Page non trouvée: {request.path}",
                    'warning',
                    request_data=True
                )
                return e
            
            @app.errorhandler(403)
            def forbidden(e):
                log_security_event(
                    'access_denied',
                    f"Accès refusé à {request.path}",
                    'warning',
                    user_id=getattr(g, 'user_id', None),
                    request_data=True
                )
                return e
            
            @app.errorhandler(500)
            def internal_server_error(e):
                log_security_event(
                    'server_error',
                    f"Erreur serveur sur {request.path}: {str(e)}",
                    'error',
                    request_data=True
                )
                return e
