from app import app, db
from models import Item

if __name__ == "__main__":
    with app.app_context():
        print("Suppression et recréation de toutes les tables...")
        db.drop_all()
        db.create_all()
        print("Base de données réinitialisée.")
        # Diagnostic: afficher les colonnes de la table items
        insp = db.inspect(db.engine)
        columns = insp.get_columns('items')
        print("Colonnes de la table items :")
        for col in columns:
            print(f"- {col['name']} ({col['type']})")
        print("(Fin du diagnostic)")
