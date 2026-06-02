import os
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db

settings_bp = Blueprint('settings', __name__, url_prefix='/parametres')

ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _save_upload(file, subfolder):
    if not file or file.filename == '':
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        return None
    filename = secure_filename(f"tenant_{current_user.tenant_id}_{subfolder}.{ext}")
    path = os.path.join(current_app.root_path, 'static', 'uploads', subfolder, filename)
    file.save(path)
    return f"uploads/{subfolder}/{filename}"

@settings_bp.route('/')
@login_required
def index():
    bot_username = current_app.config.get('TELEGRAM_BOT_USERNAME', 'SenGestionBot')
    return render_template('settings/index.html', bot_username=bot_username)

@settings_bp.route('/entreprise', methods=['POST'])
@login_required
def update_entreprise():
    t = current_user.tenant
    t.nom       = request.form.get('nom', t.nom).strip()
    t.ninea     = request.form.get('ninea', '').strip()
    t.email     = request.form.get('email', '').strip()
    t.telephone = request.form.get('telephone', '').strip()
    t.adresse   = request.form.get('adresse', '').strip()

    logo = _save_upload(request.files.get('logo'), 'logos')
    if logo:
        t.logo_url = logo

    cachet = _save_upload(request.files.get('cachet'), 'cachets')
    if cachet:
        t.cachet_url = cachet

    db.session.commit()
    flash('Informations de l\'entreprise mises à jour.', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/telegram/deconnecter', methods=['POST'])
@login_required
def deconnecter_telegram():
    current_user.telegram_chat_id   = None
    current_user.telegram_connected = False
    db.session.commit()
    flash('Telegram déconnecté.', 'success')
    return redirect(url_for('settings.index'))
