from app import app, db

if __name__ == "__main__":
    with app.app_context():
        print("Suppression et recréation de toutes les tables...")
        db.drop_all()
        db.create_all()
        print("Base de données réinitialisée.")
