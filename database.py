import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from functools import wraps

logger = logging.getLogger(__name__)

class DatabaseConnectionError(Exception):
    """Exception levée en cas d'échec de connexion à la base de données."""
    pass

class DatabaseConfig:
    """
    Classe de configuration pour la connexion à la base de données.
    """
    def __init__(self, app=None):
        self.engine = None
        self.session_factory = None
        self.app = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise la configuration de la base de données."""
        self.app = app
        
        # Configuration par défaut
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.environ.get('DATABASE_URL'))
        app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
            'connect_args': {
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        })
        
        # Création du moteur SQLAlchemy
        self.engine = create_engine(
            app.config['SQLALCHEMY_DATABASE_URI'],
            **app.config['SQLALCHEMY_ENGINE_OPTIONS']
        )
        
        # Configuration de la session
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # Configuration des événements de connexion
        self._register_events()
        
        # Vérification de la connexion
        self._verify_connection()
        
        # Configuration pour l'application
        app.extensions['db'] = self
    
    def _register_events(self):
        """Enregistre les événements de la base de données."""
        @event.listens_for(self.engine, 'before_cursor_execute')
        def before_cursor_execute(conn, cursor, statement, params, context, executemany):
            # Enregistrement des requêtes lentes
            context._query_start_time = time.time()
        
        @event.listens_for(self.engine, 'after_cursor_execute')
        def after_cursor_execute(conn, cursor, statement, params, context, executemany):
            # Journalisation des requêtes lentes
            duration = (time.time() - getattr(context, '_query_start_time', 0)) * 1000
            if duration > 1000:  # 1 seconde
                logger.warning(
                    "Requête lente détectée (%.2f ms): %s",
                    duration,
                    statement.replace('\n', ' ').replace('  ', ' ')
                )
    
    def _verify_connection(self):
        """Vérifie que la connexion à la base de données fonctionne."""
        max_retries = 3
        retry_delay = 2  # secondes
        
        for attempt in range(max_retries):
            try:
                with self.engine.connect() as conn:
                    conn.execute('SELECT 1')
                logger.info("Connexion à la base de données établie avec succès")
                return True
            except OperationalError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Échec de la connexion à la base de données après %d tentatives: %s",
                        max_retries, str(e)
                    )
                    raise DatabaseConnectionError(
                        f"Impossible de se connecter à la base de données: {str(e)}"
                    )
                
                logger.warning(
                    "Tentative de connexion à la base de données échouée (tentative %d/%d): %s",
                    attempt + 1, max_retries, str(e)
                )
                time.sleep(retry_delay * (attempt + 1))
        
        return False
    
    @contextmanager
    def session_scope(self):
        """Fournit une portée transactionnelle pour une série d'opérations."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error("Erreur de base de données: %s", str(e))
            raise
        finally:
            session.close()
    
    def get_connection(self):
        """Retourne une nouvelle connexion à la base de données."""
        return self.engine.connect()
    
    def execute_query(self, query, params=None, fetch=True):
        """
        Exécute une requête SQL et retourne les résultats.
        
        Args:
            query (str): Requête SQL à exécuter
            params (dict, optional): Paramètres de la requête
            fetch (bool): Si True, retourne les résultats de la requête
            
        Returns:
            Résultats de la requête ou None
        """
        with self.get_connection() as conn:
            result = conn.execute(query, params or {})
            if fetch:
                return result.fetchall()
            return None

# Instance globale de la base de données
db = DatabaseConfig()

def get_db_session():
    """
    Fournit une session de base de données pour une requête.
    À utiliser avec les vets Flask.
    """
    if 'db_session' not in g:
        g.db_session = db.session_factory()
    return g.db_session

@app.teardown_appcontext
def close_db_session(error):
    """Ferme la session de base de données à la fin de la requête."""
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.close()

def transactional(func):
    """
    Décorateur pour les méthodes qui nécessitent une transaction de base de données.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_db_session()
        try:
            result = func(*args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error("Erreur de transaction: %s", str(e))
            raise
    return wrapper

def with_retry(max_retries=3, delay=1):
    """
    Décorateur pour réessayer une opération en cas d'échec.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, SQLAlchemyError) as e:
                    last_exception = e
                    logger.warning(
                        "Tentative %d/%d échouée pour %s: %s",
                        attempt + 1, max_retries, func.__name__, str(e)
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            
            logger.error(
                "Échec après %d tentatives pour %s: %s",
                max_retries, func.__name__, str(last_exception)
            )
            raise last_exception
        return wrapper
    return decorator

class DatabaseHealthCheck:
    """
    Classe pour vérifier l'état de santé de la base de données.
    """
    @staticmethod
    def check_connection():
        """Vérifie que la connexion à la base de données est fonctionnelle."""
        try:
            with db.engine.connect() as conn:
                conn.execute('SELECT 1')
            return True, "La connexion à la base de données est fonctionnelle"
        except Exception as e:
            return False, f"Erreur de connexion à la base de données: {str(e)}"
    
    @staticmethod
    def check_permissions():
        """Vérifie les permissions de l'utilisateur de la base de données."""
        try:
            with db.engine.connect() as conn:
                # Vérifie les permissions de lecture
                conn.execute('SELECT * FROM pg_tables LIMIT 1')
                
                # Vérifie les permissions d'écriture
                test_table = 'test_permissions_' + str(int(time.time()))
                conn.execute(f'CREATE TEMP TABLE {test_table} (id SERIAL PRIMARY KEY)')
                conn.execute(f'INSERT INTO {test_table} (id) VALUES (1)')
                conn.execute(f'DROP TABLE {test_table}')
                
            return True, "Les permissions de la base de données sont correctes"
        except Exception as e:
            return False, f"Erreur de permissions de la base de données: {str(e)}"
    
    @classmethod
    def get_status(cls):
        """Retourne l'état de santé complet de la base de données."""
        connection_ok, connection_msg = cls.check_connection()
        permissions_ok, permissions_msg = cls.check_permissions() if connection_ok else (False, "Non testé")
        
        return {
            'database_connection': {
                'status': 'ok' if connection_ok else 'error',
                'message': connection_msg
            },
            'database_permissions': {
                'status': 'ok' if permissions_ok else 'error',
                'message': permissions_msg
            },
            'status': 'healthy' if connection_ok and permissions_ok else 'unhealthy'
        }
