from app import app, db
from models import Category

def seed_categories():
    noms = [
        "Téléphone",
        "Clés",
        "Portefeuille",
        "Sac à dos",
        "Veste",
        "Lunettes",
        "Casquette",
        "Bijoux",
        "Écouteurs",
        "Papiers d’identité"
    ]
    with app.app_context():
        for n in noms:
            existe = Category.query.filter_by(name=n).first()
            if not existe:
                db.session.add(Category(name=n))
        db.session.commit()
        print("Catégories insérées.")

if __name__ == '__main__':
    seed_categories()
