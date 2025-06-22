from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, ActionLog, Item, Status

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
    return render_template('admin/dashboard.html')

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

@bp_admin.route('/logs')
@login_required
@admin_required
def admin_logs():
    logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(200).all()
    return render_template('admin/logs.html', logs=logs)
