import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
import sqlalchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_this_in_prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/lostfound')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30 MB

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

from flask_login import LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'main.auth'
login_manager.login_message_category = 'info'

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
    return User.query.get(int(user_id))

# Register blueprints
import views
app.register_blueprint(views.bp)
import admin
app.register_blueprint(admin.bp_admin)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
