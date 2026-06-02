from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models.client import Client
from app import db
from app.services.claude_service import scanner_carte_visite
import base64

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def index():
    tid = current_user.tenant_id
    contacts = Client.query.filter_by(tenant_id=tid, actif=True)\
                           .order_by(Client.created_at.desc()).all()
    return render_template('clients/index.html', contacts=contacts)

@clients_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    if request.method == 'POST':
        client = Client(
            tenant_id  = current_user.tenant_id,
            nom        = request.form.get('nom', '').strip(),
            prenom     = request.form.get('prenom', '').strip(),
            entreprise = request.form.get('entreprise', '').strip(),
            fonction   = request.form.get('fonction', '').strip(),
            email      = request.form.get('email', '').strip(),
            telephone  = request.form.get('telephone', '').strip(),
            adresse    = request.form.get('adresse', '').strip(),
            source     = 'manuel',
        )
        db.session.add(client)
        db.session.commit()
        flash('Client créé avec succès.', 'success')
        return redirect(url_for('clients.index'))
    return render_template('clients/nouveau.html')

@clients_bp.route('/scan', methods=['GET'])
@login_required
def scan():
    return render_template('clients/scan.html')

@clients_bp.route('/scan/analyser', methods=['POST'])
@login_required
def scan_analyser():
    """Endpoint AJAX : reçoit une image base64, appelle Claude Vision, retourne JSON."""
    data = request.get_json()
    image_b64 = data.get('image')
    if not image_b64:
        return jsonify({'error': 'Aucune image fournie'}), 400

    resultat = scanner_carte_visite(image_b64)
    return jsonify(resultat)

@clients_bp.route('/scan/enregistrer', methods=['POST'])
@login_required
def scan_enregistrer():
    """Enregistre le client extrait par l'IA après validation."""
    client = Client(
        tenant_id    = current_user.tenant_id,
        nom          = request.form.get('nom', '').strip(),
        prenom       = request.form.get('prenom', '').strip(),
        entreprise   = request.form.get('entreprise', '').strip(),
        fonction     = request.form.get('fonction', '').strip(),
        email        = request.form.get('email', '').strip(),
        telephone    = request.form.get('telephone', '').strip(),
        adresse      = request.form.get('adresse', '').strip(),
        source       = request.form.get('source_mode', 'scan_carte'),
        confiance_ia = int(request.form.get('confiance_ia', 0)),
    )
    db.session.add(client)
    db.session.commit()
    source = client.source
    if source == 'qrcode':
        flash('Contact enregistré depuis le QR code.', 'success')
    else:
        flash('Contact enregistré depuis la carte de visite.', 'success')
    return redirect(url_for('clients.index'))

@clients_bp.route('/<int:client_id>')
@login_required
def detail(client_id):
    client = Client.query.filter_by(id=client_id, tenant_id=current_user.tenant_id).first_or_404()
    return render_template('clients/detail.html', client=client)

@clients_bp.route('/<int:client_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(client_id):
    client = Client.query.filter_by(id=client_id, tenant_id=current_user.tenant_id).first_or_404()
    if request.method == 'POST':
        client.nom        = request.form.get('nom', '').strip()
        client.prenom     = request.form.get('prenom', '').strip()
        client.entreprise = request.form.get('entreprise', '').strip()
        client.email      = request.form.get('email', '').strip()
        client.telephone  = request.form.get('telephone', '').strip()
        client.adresse    = request.form.get('adresse', '').strip()
        db.session.commit()
        flash('Client mis à jour.', 'success')
        return redirect(url_for('clients.detail', client_id=client.id))
    return render_template('clients/modifier.html', client=client)
