from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user   import User
from app.models.tenant import Tenant
from app import db
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.actif:
            login_user(user, remember=remember)
            from urllib.parse import urlparse
            next_page = request.args.get('next')
            if next_page and (not next_page.startswith('/') or next_page.startswith('//') or urlparse(next_page).netloc):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))
        flash('Email ou mot de passe incorrect.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom_entreprise = request.form.get('nom_entreprise', '').strip()
        ninea          = request.form.get('ninea', '').strip()
        nom            = request.form.get('nom', '').strip()
        prenom         = request.form.get('prenom', '').strip()
        email          = request.form.get('email', '').strip().lower()
        password       = request.form.get('password', '')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'error')
            return render_template('auth/register.html')

        tenant = Tenant(nom=nom_entreprise, ninea=ninea, plan='starter', nb_sieges=1)
        db.session.add(tenant)
        db.session.flush()

        token = secrets.token_urlsafe(32)
        user = User(tenant_id=tenant.id, nom=nom, prenom=prenom, email=email,
                    role='admin', actif=False, token_validation=token, email_valide=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Envoi email de validation
        try:
            from app.services.email_service import envoyer_validation
            lien = url_for('auth.valider_compte', token=token, _external=True)
            envoyer_validation(
                nom_complet = f"{prenom} {nom}".strip(),
                email       = email,
                lien_validation = lien,
            )
            flash('Inscription réussie ! Vérifiez votre email pour valider votre compte.', 'success')
        except Exception as e:
            current_app.logger.warning(f"Email non envoyé : {e}")
            flash('Compte créé. Contactez l\'administrateur pour activer votre compte.', 'warning')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/valider/<token>')
def valider_compte(token):
    user = User.query.filter_by(token_validation=token).first()
    if not user:
        flash('Lien de validation invalide ou expiré.', 'error')
        return redirect(url_for('auth.login'))

    user.actif           = True
    user.email_valide    = True
    user.token_validation = None
    db.session.commit()

    # Email de bienvenue après validation
    try:
        from app.services.email_service import envoyer_bienvenue
        envoyer_bienvenue(
            nom_complet    = user.nom_complet,
            email          = user.email,
            nom_entreprise = user.tenant.nom,
            plan           = user.tenant.plan,
        )
    except Exception:
        pass

    flash('Votre compte est validé ! Vous pouvez maintenant vous connecter.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.token_validation = token
            db.session.commit()
            try:
                from app.services.email_service import envoyer_reset_password
                lien = url_for('auth.reset_password', token=token, _external=True)
                envoyer_reset_password(
                    nom_complet=user.nom_complet,
                    email=email,
                    lien_reset=lien,
                )
            except Exception as e:
                current_app.logger.warning(f"Email reset non envoyé : {e}")
        # Toujours afficher le même message (sécurité)
        flash('Si cet email existe, un lien de réinitialisation vous a été envoyé.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reinitialiser/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(token_validation=token).first()
    if not user:
        flash('Lien invalide ou expiré.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
            return render_template('auth/reset_password.html', token=token)
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('auth/reset_password.html', token=token)

        user.set_password(password)
        user.token_validation = None
        db.session.commit()
        flash('Mot de passe réinitialisé avec succès. Connectez-vous.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
