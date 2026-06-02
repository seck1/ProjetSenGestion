from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, Response
from flask_login import login_required, current_user
from app.models.contact import Contact
from app.models.client  import Client
from app import db
from app.services.claude_service import scanner_carte_visite
import base64, io
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

contacts_bp = Blueprint('contacts', __name__, url_prefix='/contacts')

@contacts_bp.route('/')
@login_required
def index():
    tid      = current_user.tenant_id
    contacts = Contact.query.filter_by(tenant_id=tid)\
                            .order_by(Contact.created_at.desc()).all()
    return render_template('contacts/index.html', contacts=contacts)

@contacts_bp.route('/scan/analyser', methods=['POST'])
@login_required
def scan_analyser():
    """Appel AJAX : envoie l'image à Claude Vision, retourne JSON.
    Accepte soit un fichier multipart (file), soit un JSON base64 (image).
    Convertit systématiquement en JPEG via Pillow pour normaliser le format."""
    try:
        image_b64 = None

        if 'file' in request.files:
            # Upload fichier direct (HEIC, PNG, JPG…)
            f = request.files['file']
            img = Image.open(f.stream).convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=92)
            image_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

        else:
            # JSON base64 depuis le browser
            payload   = request.get_json(silent=True) or {}
            raw_b64   = payload.get('image', '')
            if not raw_b64:
                return jsonify({'success': False, 'error': 'Aucune image fournie'}), 400

            # Décoder, repasser par Pillow pour normaliser
            if ',' in raw_b64:
                raw_b64 = raw_b64.split(',', 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=92)
            image_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

        resultat = scanner_carte_visite(image_b64)
        return jsonify(resultat)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@contacts_bp.route('/enregistrer', methods=['POST'])
@login_required
def enregistrer():
    """Enregistre un contact scanné ou saisi manuellement."""
    source = request.form.get('source_mode', 'manuel')
    contact = Contact(
        tenant_id    = current_user.tenant_id,
        nom          = request.form.get('nom', '').strip(),
        prenom       = request.form.get('prenom', '').strip(),
        entreprise   = request.form.get('entreprise', '').strip(),
        fonction     = request.form.get('fonction', '').strip(),
        email        = request.form.get('email', '').strip(),
        telephone    = request.form.get('telephone', '').strip(),
        adresse      = request.form.get('adresse', '').strip(),
        site_web     = request.form.get('site_web', '').strip(),
        notes        = request.form.get('notes', '').strip(),
        evenement    = request.form.get('evenement', '').strip(),
        source       = source,
        confiance_ia = int(request.form.get('confiance_ia', 0)),
    )
    db.session.add(contact)
    db.session.commit()

    labels = {'scan_carte': 'Contact enregistré depuis la carte de visite.',
              'qrcode':     'Contact enregistré depuis le QR code.',
              'manuel':     'Contact ajouté manuellement.'}
    flash(labels.get(source, 'Contact enregistré.'), 'success')
    return redirect(url_for('contacts.index'))

@contacts_bp.route('/<int:contact_id>/convertir-en-client', methods=['POST'])
@login_required
def convertir_en_client(contact_id):
    """Convertit un contact en client (copie les données)."""
    contact = Contact.query.filter_by(
        id=contact_id, tenant_id=current_user.tenant_id
    ).first_or_404()

    if contact.est_converti:
        flash('Ce contact est déjà un client.', 'info')
        return redirect(url_for('contacts.index'))

    client = Client(
        tenant_id  = current_user.tenant_id,
        nom        = contact.nom,
        prenom     = contact.prenom,
        entreprise = contact.entreprise,
        fonction   = contact.fonction,
        email      = contact.email,
        telephone  = contact.telephone,
        adresse    = contact.adresse,
        source     = 'scan_carte' if contact.source == 'scan_carte' else 'manuel',
        notes      = contact.notes,
    )
    db.session.add(client)
    db.session.flush()

    contact.converti_client_id = client.id
    db.session.commit()

    flash(f'{contact.nom_complet} converti en client avec succès.', 'success')
    return redirect(url_for('clients.index'))

@contacts_bp.route('/<int:contact_id>/vcard')
@login_required
def vcard(contact_id):
    """Génère et télécharge un fichier vCard (.vcf) pour le contact."""
    c = Contact.query.filter_by(id=contact_id, tenant_id=current_user.tenant_id).first_or_404()
    lines = [
        'BEGIN:VCARD',
        'VERSION:3.0',
        f'N:{c.nom};{c.prenom};;;',
        f'FN:{c.nom_complet}',
    ]
    if c.entreprise: lines.append(f'ORG:{c.entreprise}')
    if c.fonction:   lines.append(f'TITLE:{c.fonction}')
    if c.email:      lines.append(f'EMAIL:{c.email}')
    if c.telephone:  lines.append(f'TEL:{c.telephone}')
    if c.adresse:    lines.append(f'ADR:;;{c.adresse};;;;')
    if c.site_web:   lines.append(f'URL:{c.site_web}')
    lines.append('END:VCARD')
    vcf = '\r\n'.join(lines) + '\r\n'
    filename = f"{c.nom_complet.replace(' ', '_')}.vcf"
    return Response(
        vcf,
        mimetype='text/vcard',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@contacts_bp.route('/<int:contact_id>')
@login_required
def detail(contact_id):
    c = Contact.query.filter_by(id=contact_id, tenant_id=current_user.tenant_id).first_or_404()
    return render_template('contacts/detail.html', c=c)

@contacts_bp.route('/<int:contact_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(contact_id):
    c = Contact.query.filter_by(id=contact_id, tenant_id=current_user.tenant_id).first_or_404()
    if request.method == 'POST':
        c.nom        = request.form.get('nom', '').strip()
        c.prenom     = request.form.get('prenom', '').strip()
        c.entreprise = request.form.get('entreprise', '').strip()
        c.fonction   = request.form.get('fonction', '').strip()
        c.email      = request.form.get('email', '').strip()
        c.telephone  = request.form.get('telephone', '').strip()
        c.adresse    = request.form.get('adresse', '').strip()
        c.site_web   = request.form.get('site_web', '').strip()
        c.notes      = request.form.get('notes', '').strip()
        c.evenement  = request.form.get('evenement', '').strip()
        db.session.commit()
        flash('Contact mis à jour.', 'success')
        return redirect(url_for('contacts.detail', contact_id=c.id))
    return render_template('contacts/modifier.html', c=c)

@contacts_bp.route('/<int:contact_id>/supprimer', methods=['POST'])
@login_required
def supprimer(contact_id):
    contact = Contact.query.filter_by(
        id=contact_id, tenant_id=current_user.tenant_id
    ).first_or_404()
    db.session.delete(contact)
    db.session.commit()
    flash('Contact supprimé.', 'success')
    return redirect(url_for('contacts.index'))
