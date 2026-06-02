from flask import Blueprint, request, jsonify, current_app
from app.models.client import Client
from app.models.user import User
from app.models.tenant import Tenant
from app import db
from werkzeug.security import generate_password_hash
import hmac, hashlib, secrets

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')

@webhooks_bp.route('/tally', methods=['POST'])
def tally():
    """
    Reçoit les réponses d'un formulaire Tally via Make.
    Make formate les données et les envoie ici.
    """
    secret = current_app.config.get('TALLY_WEBHOOK_SECRET')
    if secret:
        sig = request.headers.get('X-Tally-Signature', '')
        expected = hmac.new(secret.encode(), request.data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return jsonify({'error': 'Signature invalide'}), 401

    data = request.get_json(silent=True) or {}

    # Structure attendue de Make après mapping Tally :
    # { tenant_id, nom, prenom, entreprise, email, telephone, adresse, besoins, budget }
    tenant_id = data.get('tenant_id')
    if not tenant_id:
        return jsonify({'error': 'tenant_id requis'}), 400

    client = Client(
        tenant_id  = tenant_id,
        nom        = data.get('nom', ''),
        prenom     = data.get('prenom', ''),
        entreprise = data.get('entreprise', ''),
        email      = data.get('email', ''),
        telephone  = data.get('telephone', ''),
        adresse    = data.get('adresse', ''),
        notes      = f"Besoins (Tally) : {data.get('besoins', '')}\nBudget : {data.get('budget', '')}",
        source     = 'tally',
    )
    db.session.add(client)
    db.session.commit()

    return jsonify({'success': True, 'client_id': client.id})

@webhooks_bp.route('/tally/inscription', methods=['POST'])
def tally_inscription():
    """
    Webhook appelé par Tally quand un utilisateur remplit le formulaire d'inscription.
    Tally envoie: { data: { fields: [ {key, label, value}, ... ] } }
    """
    payload = request.get_json(silent=True) or {}
    current_app.logger.info(f"Tally inscription payload: {payload}")

    # Parser le format natif Tally
    fields_list = []
    tally_data = payload.get('data', payload)
    if isinstance(tally_data, dict):
        fields_list = tally_data.get('fields', [])

    # Construire un dict key->value depuis les fields Tally
    fields = {}
    for f in fields_list:
        key   = (f.get('key') or f.get('label', '')).lower().replace(' ', '_')
        label = f.get('label', '').lower().replace(' ', '_')
        value = f.get('value', '')
        if isinstance(value, list):
            value = ', '.join(str(v) for v in value)
        fields[key]   = str(value).strip() if value else ''
        fields[label] = str(value).strip() if value else ''

    # Extraction — essaie plusieurs variantes de clé
    def get_field(*keys):
        for k in keys:
            v = fields.get(k, '')
            if v:
                return v
        return ''

    nom_entreprise = get_field('entreprise', 'nom_entreprise', 'nom_de_l\'entreprise', 'company')
    email          = get_field('email', 'email_professionnel')
    mot_de_passe   = get_field('mot_de_passe', 'password', 'mot_de_passe_*')
    nom            = get_field('nom')
    prenom         = get_field('prénom', 'prenom')
    plan           = get_field('plan') or 'starter'
    ninea     = get_field('ninea')
    telephone = get_field('telephone', 'téléphone', 'phone')

    if not all([nom_entreprise, email, mot_de_passe, nom]):
        return jsonify({'error': 'Champs obligatoires manquants : nom_entreprise, email, mot_de_passe, nom'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Un compte existe déjà avec cet email'}), 409

    if plan not in ('starter', 'pro', 'enterprise'):
        plan = 'starter'

    # Créer le tenant
    tenant = Tenant(
        nom       = nom_entreprise,
        ninea     = ninea or None,
        email     = email,
        telephone = telephone or None,
        plan      = plan,
        nb_sieges = 1,
        actif     = True,
    )
    db.session.add(tenant)
    db.session.flush()

    # Créer l'utilisateur admin du tenant (inactif jusqu'à validation)
    token = secrets.token_urlsafe(32)
    user = User(
        tenant_id        = tenant.id,
        nom              = nom,
        prenom           = prenom or None,
        email            = email,
        role             = 'admin',
        actif            = False,
        token_validation = token,
        email_valide     = False,
    )
    user.set_password(mot_de_passe)
    db.session.add(user)
    db.session.commit()

    # Envoyer email de validation
    try:
        from app.services.email_service import envoyer_validation
        from flask import url_for
        lien = url_for('auth.valider_compte', token=token, _external=True)
        envoyer_validation(
            nom_complet     = f"{prenom} {nom}".strip(),
            email           = email,
            lien_validation = lien,
        )
    except Exception as e:
        current_app.logger.warning(f"Email de validation non envoyé : {e}")

    return jsonify({
        'success'   : True,
        'tenant_id' : tenant.id,
        'user_id'   : user.id,
        'message'   : f'Compte {nom_entreprise} créé avec succès'
    }), 201


@webhooks_bp.route('/make/devis-ouvert/<int:devis_id>', methods=['POST'])
def devis_ouvert(devis_id):
    """Make appelle cet endpoint quand le client ouvre le lien du devis."""
    from app.models.devis import Devis
    from datetime import datetime
    devis = Devis.query.get_or_404(devis_id)
    if devis.statut == 'envoye':
        devis.statut    = 'ouvert'
        devis.ouvert_at = datetime.utcnow()
        db.session.commit()
    return jsonify({'success': True})


@webhooks_bp.route('/signature', methods=['POST'])
def signature_callback():
    """
    Make appelle cet endpoint quand Yousign confirme la signature.
    Payload attendu : { devis_id, signature_nom, statut }
    """
    from app.models.devis import Devis, LigneDevis
    from app.models.facture import Facture, LigneFacture
    from datetime import datetime, date, timedelta

    data = request.get_json(silent=True) or {}
    current_app.logger.info(f"Webhook signature reçu : {data}")

    devis_id      = data.get('devis_id')
    signature_nom = data.get('signature_nom', '')
    statut        = data.get('statut', 'signe')

    if not devis_id:
        return jsonify({'error': 'devis_id requis'}), 400

    devis = Devis.query.get(int(devis_id))
    if not devis:
        return jsonify({'error': 'Devis introuvable'}), 404

    # Mettre à jour le statut du devis
    devis.statut        = statut
    devis.signe_at      = datetime.utcnow()
    devis.signature_nom = signature_nom or devis.client.nom_complet
    db.session.flush()

    # Générer la facture automatiquement si pas déjà créée
    facture_existante = Facture.query.filter_by(devis_id=devis.id).first()
    facture = None
    if not facture_existante:
        count   = Facture.query.filter_by(tenant_id=devis.tenant_id).count() + 1
        numero  = f"FA-{datetime.utcnow().year}-{count:04d}"
        facture = Facture(
            tenant_id = devis.tenant_id,
            client_id = devis.client_id,
            devis_id  = devis.id,
            numero    = numero,
            objet     = devis.objet,
            tva_pct   = devis.tva_pct,
            total_ht  = devis.total_ht,
            total_tva = devis.total_tva,
            total_ttc = devis.total_ttc,
            echeance  = date.today() + timedelta(days=30),
            statut    = 'brouillon',
            notes     = f"Facture générée automatiquement depuis {devis.numero} après signature.",
        )
        db.session.add(facture)
        db.session.flush()

        for ligne in devis.lignes:
            lf = LigneFacture(
                facture_id    = facture.id,
                description   = ligne.description,
                quantite      = ligne.quantite,
                prix_unitaire = ligne.prix_unitaire,
                total         = ligne.total,
                ordre         = ligne.ordre,
            )
            db.session.add(lf)

    db.session.commit()

    # Email de confirmation au client
    try:
        from app.services.email_service import envoyer_confirmation_signature
        envoyer_confirmation_signature(
            nom_complet    = devis.client.nom_complet,
            email          = devis.client.email,
            numero_devis   = devis.numero,
            montant        = devis.total_ttc,
            numero_facture = facture.numero if facture else None,
        )
    except Exception as e:
        current_app.logger.warning(f"Email confirmation signature non envoyé : {e}")

    return jsonify({
        'success'        : True,
        'devis_statut'   : devis.statut,
        'facture_creee'  : facture is not None,
        'facture_numero' : facture.numero if facture else None,
    })
