import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

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
