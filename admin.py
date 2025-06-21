from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, ActionLog

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
