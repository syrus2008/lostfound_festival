from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, ActionLog, Item, Status, HeadphoneLoan

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès réservé à l'administrateur.", "danger")
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

bp_admin = Blueprint('admin', __name__, url_prefix='/admin')

@bp_admin.route('/')
@login_required
@admin_required
def admin_dashboard():
    nb_found = Item.query.filter_by(status=Status.FOUND).count()
    nb_lost = Item.query.filter_by(status=Status.LOST).count()
    nb_users = User.query.count()
    nb_deletions = Item.query.filter_by(status=Status.PENDING_DELETION).count()
    return render_template(
        'admin/dashboard.html',
        nb_found=nb_found,
        nb_lost=nb_lost,
        nb_users=nb_users,
        nb_deletions=nb_deletions
    )

from forms import SimpleCsrfForm

@bp_admin.route('/deletion-requests')
@login_required
@admin_required
def deletion_requests():
    items = Item.query.filter_by(status=Status.PENDING_DELETION).order_by(Item.date_reported.desc()).all()
    csrf_form = SimpleCsrfForm()
    return render_template('admin/deletion_requests.html', items=items, csrf_form=csrf_form)

@bp_admin.route('/deletion-requests/<int:item_id>/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_deletion(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    ActionLog.query.session.add(ActionLog(user_id=current_user.id, action_type='confirm_deletion', details=f'Suppression validée pour objet {item_id}'))
    db.session.commit()
    flash("Suppression définitive effectuée.", "success")
    return redirect(url_for('admin.deletion_requests'))

@bp_admin.route('/deletion-requests/<int:item_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_deletion(item_id):
    item = Item.query.get_or_404(item_id)
    # Restaure le statut original si connu, sinon LOST par défaut
    if item.previous_status:
        item.status = item.previous_status
        item.previous_status = None
    else:
        item.status = Status.LOST
    db.session.commit()
    ActionLog.query.session.add(ActionLog(user_id=current_user.id, action_type='reject_deletion', details=f'Rejet suppression objet {item_id}'))
    db.session.commit()
    flash("Demande de suppression rejetée. L'objet est de nouveau visible.", "info")
    return redirect(url_for('admin.deletion_requests'))

@bp_admin.route('/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp_admin.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    from forms import SimpleCsrfForm
    user = User.query.get_or_404(user_id)
    csrf_form = SimpleCsrfForm()
    return render_template('admin/user_detail.html', user=user, csrf_form=csrf_form)

@bp_admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    from forms import SimpleCsrfForm
    form = SimpleCsrfForm()
    user = User.query.get_or_404(user_id)
    if form.validate_on_submit():
        if user.id == current_user.id:
            flash("Vous ne pouvez pas modifier votre propre statut admin.", "danger")
        else:
            user.is_admin = not user.is_admin
            db.session.commit()
            flash("Statut administrateur modifié.", "success")
    else:
        flash("Erreur de validation du formulaire.", "danger")
    return redirect(url_for('admin.user_detail', user_id=user_id))

@bp_admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    from forms import SimpleCsrfForm
    form = SimpleCsrfForm()
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user_id))
    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        flash("Utilisateur supprimé.", "success")
        return redirect(url_for('admin.admin_users'))
    else:
        flash("Erreur de validation du formulaire.", "danger")
        return redirect(url_for('admin.user_detail', user_id=user_id))

@bp_admin.route('/loans', methods=['GET', 'POST'])
@login_required
@admin_required
def headphone_loans():
    form = HeadphoneLoanForm()
    search = request.args.get('q', '', type=str).strip()
    query = HeadphoneLoan.query
    if search:
        query = query.filter((HeadphoneLoan.first_name.ilike(f'%{search}%')) | (HeadphoneLoan.last_name.ilike(f'%{search}%')))
    loans = query.order_by(HeadphoneLoan.loan_date.desc()).all()
    if form.validate_on_submit():
        loan = HeadphoneLoan(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            deposit_type=form.deposit_type.data,
            deposit_details=form.deposit_details.data
        )
        db.session.add(loan)
        db.session.commit()
        flash("Prêt enregistré !", "success")
        return redirect(url_for('admin.headphone_loans'))
    return render_template('admin/loans.html', form=form, loans=loans, search=search)

@bp_admin.route('/loans/<int:loan_id>/return', methods=['POST'])
@login_required
@admin_required
def return_headphone_loan(loan_id):
    import json
    loan = HeadphoneLoan.query.get_or_404(loan_id)
    data = request.get_json()
    signature = data.get('signature')
    if not signature:
        return {'success': False, 'error': 'Signature manquante'}, 400
    from datetime import datetime
    loan.signature = signature
    loan.return_date = datetime.utcnow()
    db.session.commit()
    return {'success': True}

@bp_admin.route('/logs')
@login_required
@admin_required
def admin_logs():
    # Recherche, filtre et pagination
    from sqlalchemy import or_
    page = request.args.get('page', 1, type=int)
    per_page = 25
    search = request.args.get('search', '', type=str).strip()
    action_type = request.args.get('action_type', '', type=str).strip()
    query = ActionLog.query
    if search:
        query = query.filter(or_(ActionLog.details.ilike(f'%{search}%'), ActionLog.action_type.ilike(f'%{search}%')))
    if action_type:
        query = query.filter(ActionLog.action_type == action_type)
    logs = query.order_by(ActionLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    # Pour le filtre, récupérer tous les types d'actions distincts
    action_types = [row[0] for row in db.session.query(ActionLog.action_type).distinct().all()]
    return render_template('admin/logs.html', logs=logs, search=search, action_type=action_type, action_types=action_types)
