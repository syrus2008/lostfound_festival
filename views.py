import os
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app, send_from_directory, make_response
)
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from rapidfuzz import fuzz
from datetime import datetime

from app import app, db
from models import Item, Category, Status
from forms import ItemForm, ClaimForm, ConfirmReturnForm, MatchForm

bp = Blueprint('main', __name__)

def allowed_file(filename):
    allowed_ext = {'png', 'jpg', 'jpeg'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext

def find_similar_items(titre, category_id, seuil=70):
    similaires = []
    candidats = Item.query.filter(
        Item.category_id == category_id,
        Item.status.in_([Status.LOST, Status.FOUND])
    ).all()
    for obj in candidats:
        score = fuzz.token_sort_ratio(titre, obj.title)
        if score >= seuil:
            similaires.append({'id': obj.id, 'title': obj.title, 'score': score})
    return similaires

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/lost/new', methods=['GET', 'POST'])
def create_lost():
    form = ItemForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        doublons = find_similar_items(form.title.data, form.category.data, 70)
        if doublons:
            flash("Attention : des objets similaires existent déjà !", "warning")

        item = Item(
            status=Status.LOST,
            title=form.title.data,
            comments=form.comments.data,
            location=form.location.data,
            category_id=form.category.data,
            reporter_name=form.reporter_name.data,
            reporter_email=form.reporter_email.data,
            reporter_phone=form.reporter_phone.data
        )
        if form.photo.data:
            f = form.photo.data
            if allowed_file(f.filename):
                filename = secure_filename(f.filename)
                chemin = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                f.save(chemin)
                item.photo_filename = filename

        db.session.add(item)
        db.session.commit()
        flash("Objet perdu enregistré !", "success")
        return redirect(url_for('main.list_items', status='lost'))

    return render_template('lost_form.html', form=form, action='lost')

@bp.route('/found/new', methods=['GET', 'POST'])
def create_found():
    form = ItemForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        doublons = find_similar_items(form.title.data, form.category.data, 70)
        if doublons:
            flash("Attention : des objets similaires existent déjà !", "warning")

        item = Item(
            status=Status.FOUND,
            title=form.title.data,
            comments=form.comments.data,
            location=form.location.data,
            category_id=form.category.data,
            reporter_name=form.reporter_name.data,
            reporter_email=form.reporter_email.data,
            reporter_phone=form.reporter_phone.data
        )
        if form.photo.data:
            f = form.photo.data
            if allowed_file(f.filename):
                filename = secure_filename(f.filename)
                chemin = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                f.save(chemin)
                item.photo_filename = filename

        db.session.add(item)
        db.session.commit()
        flash("Objet trouvé enregistré !", "success")
        return redirect(url_for('main.list_items', status='found'))

    return render_template('found_form.html', form=form, action='found')

@bp.route('/items/<status>')
def list_items(status):
    try:
        st = Status(status)
    except ValueError:
        st = Status.LOST

    q = request.args.get('q', '', type=str)
    cat_filter = request.args.get('category', type=int)
    page = request.args.get('page', 1, type=int)

    query = Item.query.filter_by(status=st)
    if cat_filter:
        query = query.filter_by(category_id=cat_filter)
    if q:
        mot = f"%{q}%"
        query = query.filter(or_(Item.title.ilike(mot), Item.comments.ilike(mot)))

    pagination = query.order_by(Item.date_reported.desc()).paginate(page=page, per_page=12, error_out=False)
    items = pagination.items
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        'list.html',
        items=items,
        status=st.value,
        pagination=pagination,
        categories=categories,
        selected_category=cat_filter,
        search_query=q
    )

@bp.route('/item/<int:item_id>', methods=['GET', 'POST'])
def detail_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ClaimForm()
    match_form = None

    # Si l'objet est déjà rendu, pas de correspondance ni réclamation
    if item.status == Status.RETURNED:
        return render_template('detail.html', item=item, can_claim=False, Status=Status)

    # Préparer le formulaire de correspondance pour LOST ↔ FOUND, même catégorie
    if item.status in (Status.LOST, Status.FOUND):
        opposite_status = Status.FOUND if item.status == Status.LOST else Status.LOST
        candidats = Item.query.filter_by(
            status=opposite_status,
            category_id=item.category_id
        ).all()
        if candidats:
            choices = [(0, "— Sélectionner —")]
            for c in candidats:
                choices.append((c.id, f"[{c.id}] {c.title} ({c.location or '—'})"))
            match_form = MatchForm()
            match_form.match_with.choices = choices

    # POST : correspondance prioritaire
    if match_form and match_form.validate_on_submit() and 'submit_match' in request.form:
        other_id = match_form.match_with.data
        if other_id and other_id != 0:
            other = Item.query.get_or_404(other_id)

            # Mettre les deux objets en RETURNED
            now = datetime.utcnow()
            item.status = Status.RETURNED
            other.status = Status.RETURNED

            # Copier les coordonnées réporter de l'un vers claimant de l'autre
            item.claimant_name = other.reporter_name
            item.claimant_email = other.reporter_email
            item.claimant_phone = other.reporter_phone
            item.return_date = now
            item.return_comment = f"Correspondance validée avec l'objet #{other.id}"

            other.claimant_name = item.reporter_name
            other.claimant_email = item.reporter_email
            other.claimant_phone = item.reporter_phone
            other.return_date = now
            other.return_comment = f"Correspondance validée avec l'objet #{item.id}"

            db.session.commit()
            flash(f"Objets #{item.id} et #{other.id} marqués comme rendus.", "success")
            return redirect(url_for('main.list_items', status='returned'))
        else:
            flash("Veuillez sélectionner un objet valide pour la correspondance.", "warning")

    # POST : réclamation classique
    if form.validate_on_submit() and 'submit' in request.form:
        item.status = Status.RETURNED
        item.claimant_name = form.claimant_name.data
        item.claimant_email = form.claimant_email.data
        item.claimant_phone = form.claimant_phone.data
        item.return_date = datetime.utcnow()
        db.session.commit()
        flash("Réclamation enregistrée et objet marqué comme rendu !", "success")
        return redirect(url_for('main.list_items', status='returned'))

    return render_template(
        'detail.html',
        item=item,
        form=form,
        can_claim=True,
        Status=Status,
        match_form=match_form
    )

@bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ItemForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]

    if request.method == 'GET':
        form.title.data = item.title
        form.comments.data = item.comments
        form.location.data = item.location
        form.category.data = item.category_id
        form.reporter_name.data = item.reporter_name
        form.reporter_email.data = item.reporter_email
        form.reporter_phone.data = item.reporter_phone

    if form.validate_on_submit():
        item.title = form.title.data
        item.comments = form.comments.data
        item.location = form.location.data
        item.category_id = form.category.data
        item.reporter_name = form.reporter_name.data
        item.reporter_email = form.reporter_email.data
        item.reporter_phone = form.reporter_phone.data
        if form.photo.data:
            f = form.photo.data
            if allowed_file(f.filename):
                filename = secure_filename(f.filename)
                chemin = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                f.save(chemin)
                item.photo_filename = filename

        db.session.commit()
        flash("Objet mis à jour !", "success")
        return redirect(url_for('main.detail_item', item_id=item.id))

    return render_template('edit_item.html', form=form, item=item)

@bp.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Objet supprimé définitivement !", "danger")
    return redirect(url_for('main.list_items', status=item.status.value))

@bp.route('/export/<status>')
def export_items(status):
    try:
        st = Status(status)
    except ValueError:
        st = Status.LOST

    items = Item.query.filter_by(status=st).order_by(Item.date_reported.desc()).all()
    html = render_template('export_template.html', items=items, status=st.value)
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=export_{st.value}.html'
    return response

@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@bp.route('/api/check_similar', methods=['POST'])
def api_check_similar():
    titre = request.form.get('title', '')
    cat_id = request.form.get('category_id', type=int)
    if not titre or not cat_id:
        return {'similars': []}
    similars = find_similar_items(titre, cat_id, seuil=70)
    return {'similars': similars}
