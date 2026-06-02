from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.tenant import Tenant
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super_admin':
            flash('Accès réservé aux super administrateurs.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@login_required
@super_admin_required
def index():
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()
    users   = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/index.html', tenants=tenants, users=users)

@admin_bp.route('/user/<int:user_id>/toggle')
@login_required
@super_admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.actif = not user.actif
    db.session.commit()
    etat = 'activé' if user.actif else 'désactivé'
    flash(f'Utilisateur {user.nom_complet} {etat}.', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/user/<int:user_id>/role', methods=['POST'])
@login_required
@super_admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role in ('super_admin', 'admin', 'commercial', 'comptable'):
        user.role = new_role
        db.session.commit()
        flash(f'Rôle de {user.nom_complet} mis à jour.', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/tenant/<int:tenant_id>/toggle')
@login_required
@super_admin_required
def toggle_tenant(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.actif = not tenant.actif
    db.session.commit()
    etat = 'activé' if tenant.actif else 'désactivé'
    flash(f'Compte {tenant.nom} {etat}.', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/tenant/<int:tenant_id>/plan', methods=['POST'])
@login_required
@super_admin_required
def change_plan(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    new_plan = request.form.get('plan')
    if new_plan in ('starter', 'pro', 'enterprise'):
        tenant.plan = new_plan
        db.session.commit()
        flash(f'Plan de {tenant.nom} mis à jour.', 'success')
    return redirect(url_for('admin.index'))
