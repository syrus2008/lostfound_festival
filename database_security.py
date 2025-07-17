import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def apply_database_security(db_url):
    """
    Applique les mesures de sécurité de base de données PostgreSQL.
    """
    try:
        # Création d'un moteur SQLAlchemy avec un pool de connexions
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        )

        with engine.connect() as conn:
            # Désactivation des connexions non-SSL (si SSL est configuré)
            if 'sslmode=require' in db_url.lower():
                conn.execute(text("ALTER SYSTEM SET ssl = 'on'"))
                conn.execute(text("ALTER SYSTEM SET ssl_ca_file = '/etc/ssl/certs/ca-certificates.crt'"))
                conn.execute(text("ALTER SYSTEM SET ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'"))
                conn.execute(text("ALTER SYSTEM SET ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key'"))
                conn.execute(text("SELECT pg_reload_conf()"))
                logger.info("Configuration SSL appliquée à PostgreSQL")

            # Configuration de la sécurité
            conn.execute(text("ALTER SYSTEM SET log_statement = 'ddl'"))  # Journalisation des commandes DDL
            conn.execute(text("ALTER SYSTEM SET log_connections = 'on'"))  # Journalisation des connexions
            conn.execute(text("ALTER SYSTEM SET log_disconnections = 'on'"))  # Journalisation des déconnexions
            conn.execute(text("ALTER SYSTEM SET log_lock_waits = 'on'"))  # Journalisation des attentes de verrous
            conn.execute(text("ALTER SYSTEM SET log_min_duration_statement = '1000'"))  # Journalisation des requêtes lentes
            conn.execute(text("ALTER SYSTEM SET log_min_error_statement = 'error'"))  # Niveau de journalisation
            conn.execute(text("ALTER SYSTEM SET log_min_messages = 'warning'"))  # Niveau de journalisation
            
            # Configuration des connexions
            conn.execute(text("ALTER SYSTEM SET max_connections = '100'"))  # Limite de connexions
            conn.execute(text("ALTER SYSTEM SET superuser_reserved_connections = '3'"))  # Connexions réservées
            
            # Configuration des mots de passe
            conn.execute(text("ALTER SYSTEM SET password_encryption = 'scram-sha-256'"))  # Chiffrement des mots de passe
            conn.execute(text("ALTER SYSTEM SET password_encryption = 'scram-sha-256'"))
            
            # Rechargement de la configuration
            conn.execute(text("SELECT pg_reload_conf()"))
            
            logger.info("Configuration de sécurité PostgreSQL appliquée avec succès")
            
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la configuration de la sécurité PostgreSQL: {str(e)}")
        raise

def create_limited_user(db_url, username, password, database):
    """
    Crée un utilisateur avec des privilèges limités pour l'application.
    """
    try:
        # Création d'un moteur avec les droits admin
        admin_engine = create_engine(db_url)
        
        with admin_engine.connect() as conn:
            # Création de l'utilisateur avec mot de passe
            conn.execute(text(f"CREATE USER {username} WITH PASSWORD :password"), 
                       {"password": password})
            
            # Attribution des privilèges
            conn.execute(text(f"GRANT CONNECT ON DATABASE {database} TO {username}"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {username}"))
            
            # Privilèges sur les tables
            tables = ['items', 'categories', 'matches', 'item_photos', 'users', 'action_logs', 'headphone_loans']
            for table in tables:
                conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {username}"))
                conn.execute(text(f"GRANT USAGE, SELECT ON SEQUENCE {table}_id_seq TO {username}"))
            
            logger.info(f"Utilisateur {username} créé avec des privilèges limités")
            
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
        raise
