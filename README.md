# Lost & Found Festival

## Description

Application Flask pour gérer les objets perdus, trouvés et rendus lors d'un festival.

## Structure

- **app.py** : configuration Flask et initialisation SQLAlchemy.
- **models.py** : définition des tables `Category` et `Item`.
- **forms.py** : WTForms pour création/édition, réclamation et confirmation.
- **views.py** : routes Flask (CRUD, listing, matching, export).
- **categories_seed.py** : script pour peupler la table `categories`.
- **templates/** : vues Jinja2.
- **static/css/** : fichiers CSS (style.css).
- **static/js/** : fichiers JS (main.js).
- **static/uploads/** : stockage des photos (volume persistant sur Railway).
- **requirements.txt** : dépendances Python.
- **Procfile** : pour déploiement sur Railway.

## Installation locale

1. Cloner ce dépôt.
2. Créer un environnement virtuel Python 3.10+ :
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Installer les dépendances :
   ```
   pip install -r requirements.txt
   ```
4. Configurer `.env` (facultatif) ou définir les variables d'environnement :
   - `SECRET_KEY` : clé secrète Flask.
   - `DATABASE_URL` : URI PostgreSQL (ex. `postgresql://user:pass@localhost:5432/lostfound`).
5. Exécuter le script de seed des catégories :
   ```
   python categories_seed.py
   ```
6. Lancer l'application :
   ```
   python app.py
   ```
7. Ouvrir `http://127.0.0.1:5000` dans le navigateur.

## Déploiement sur Railway

1. Créer un projet Railway.
2. Ajouter le plugin PostgreSQL → récupérer `DATABASE_URL`.
3. Définir les variables d'environnement : `SECRET_KEY`, `DATABASE_URL`.
4. Configurer le volume persistant pour `./static/uploads`.
5. Connecter votre dépôt GitHub à Railway.
6. Lancer le script `categories_seed.py` via la commande “Run” sur Railway.
7. Railway détecte automatiquement le `Procfile` et déploie :
   ```
   web: gunicorn app:app
   ```
8. Tester l'application en production.

## Fonctionnalités

- **Signalement Lost/Found** : formulaires avec upload photo, catégorie, description, coordonnées.
- **Matching interne** : détection de titres similaires avant validation (Ajax + RapidFuzz).
- **Listing en cartes** : interface responsives avec Bootstrap, pagination.
- **Détail & Réclamation** : passer un objet au statut “returned” via formulaire.
- **Modification & Suppression** : éditer les informations ou supprimer l'objet.
- **Export HTML** : télécharger un fichier `.html` brut contenant toutes les informations hors ligne.

---
