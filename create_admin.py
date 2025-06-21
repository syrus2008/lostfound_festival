import os
from app import app, db
from models import User

ADMIN_EMAIL = "thib's"
ADMIN_PASSWORD = "71207120"

with app.app_context():
    if User.query.filter_by(email=ADMIN_EMAIL).first():
        print(f"Un utilisateur admin existe déjà avec l'email : {ADMIN_EMAIL}")
    else:
        admin = User(email=ADMIN_EMAIL, is_admin=True)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"Administrateur créé : {ADMIN_EMAIL}")
