from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from flask_login import login_required, current_user
from app.models.devis   import Devis, LigneDevis
from app.models.client  import Client
from app.models.reunion import Reunion
from app import db
from app.services.pdf_service  import generer_devis_pdf
from app.services.make_service import devis_envoye as make_devis_envoye, devis_signe as make_devis_signe, demander_signature as make_demander_signature
from app.services.whisper_service import transcrire_audio
from app.services.claude_service  import analyser_transcription
from datetime import datetime, date
import io, os

devis_bp = Blueprint('devis', __name__, url_prefix='/devis')

def _gen_numero(tenant_id):
    count = Devis.query.filter_by(tenant_id=tenant_id).count() + 1
    return f"DV-{datetime.utcnow().year}-{count:04d}"

@devis_bp.route('/')
@login_required
def index():
    tid    = current_user.tenant_id
    statut = request.args.get('statut', 'tous')
    q      = Devis.query.filter_by(tenant_id=tid)
    if statut != 'tous':
        q = q.filter_by(statut=statut)
    devis_list = q.order_by(Devis.created_at.desc()).all()

    counts = {}
    for s in ['brouillon', 'envoye', 'ouvert', 'signe', 'refuse']:
        counts[s] = Devis.query.filter_by(tenant_id=tid, statut=s).count()
    counts['tous'] = sum(counts.values())

    return render_template('devis/index.html',
        devis_list=devis_list, statut=statut, counts=counts)

@devis_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    tid     = current_user.tenant_id
    clients = Client.query.filter_by(tenant_id=tid, actif=True).order_by(Client.nom).all()

    if request.method == 'POST':
        client_id = int(request.form.get('client_id'))
        devis = Devis(
            tenant_id    = tid,
            client_id    = client_id,
            user_id      = current_user.id,
            numero       = _gen_numero(tid),
            objet        = request.form.get('objet', '').strip(),
            notes        = request.form.get('notes', '').strip(),
            tva_pct      = float(request.form.get('tva_pct', 18)),
            valide_jusqu = date.fromisoformat(request.form.get('valide_jusqu')) if request.form.get('valide_jusqu') else None,
            statut       = 'brouillon',
        )
        db.session.add(devis)
        db.session.flush()

        descriptions = request.form.getlist('description[]')
        quantites    = request.form.getlist('quantite[]')
        prix         = request.form.getlist('prix_unitaire[]')
        for i, desc in enumerate(descriptions):
            if not desc.strip():
                continue
            qte = float(quantites[i]) if i < len(quantites) else 1
            pu  = float(prix[i])      if i < len(prix)      else 0
            ligne = LigneDevis(devis_id=devis.id, description=desc, quantite=qte, prix_unitaire=pu, ordre=i)
            ligne.calculer()
            db.session.add(ligne)

        db.session.flush()
        devis.calculer_totaux()
        db.session.commit()
        flash(f'Devis {devis.numero} créé.', 'success')
        return redirect(url_for('devis.detail', devis_id=devis.id))

    return render_template('devis/nouveau.html', clients=clients)

@devis_bp.route('/<int:devis_id>')
@login_required
def detail(devis_id):
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()
    return render_template('devis/detail.html', devis=d)

@devis_bp.route('/<int:devis_id>/envoyer', methods=['POST'])
@login_required
def envoyer(devis_id):
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()
    d.statut    = 'envoye'
    d.envoye_at = datetime.utcnow()
    db.session.commit()
    make_devis_envoye(d.id, d.client.nom_complet, d.client.telephone, d.client.email, d.total_ttc)
    flash('Devis envoyé au client.', 'success')
    return redirect(url_for('devis.detail', devis_id=d.id))

@devis_bp.route('/<int:devis_id>/signer', methods=['POST'])
@login_required
def signer(devis_id):
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()
    d.statut        = 'signe'
    d.signe_at      = datetime.utcnow()
    d.signature_nom = request.form.get('nom_signataire', d.client.nom_complet)
    db.session.commit()
    make_devis_signe(d.id, d.client.nom_complet, d.client.email, d.total_ttc)
    flash('Devis signé avec succès.', 'success')
    return redirect(url_for('devis.detail', devis_id=d.id))

@devis_bp.route('/<int:devis_id>/envoyer-signature', methods=['POST'])
@login_required
def envoyer_signature(devis_id):
    """Génère un lien de signature unique et envoie l'email au client."""
    import secrets as _secrets
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()

    if d.statut not in ('brouillon', 'envoye', 'ouvert'):
        flash('Ce devis ne peut plus être envoyé pour signature.', 'error')
        return redirect(url_for('devis.detail', devis_id=d.id))

    if not d.client or not d.client.email:
        flash('Ce client n\'a pas d\'adresse email renseignée.', 'error')
        return redirect(url_for('devis.detail', devis_id=d.id))

    # Générer un token unique pour ce devis
    if not d.token_signature:
        d.token_signature = _secrets.token_urlsafe(32)

    if d.statut == 'brouillon':
        d.statut    = 'envoye'
        d.envoye_at = datetime.utcnow()

    db.session.commit()

    lien = url_for('devis.page_signature', token=d.token_signature, _external=True)

    try:
        from app.services.email_service import envoyer_demande_signature
        envoyer_demande_signature(
            nom_complet  = d.client.nom_complet,
            email        = d.client.email,
            numero_devis = d.numero,
            montant      = d.total_ttc,
            objet        = d.objet or '',
            lien         = lien,
            nom_entreprise = d.tenant.nom,
        )
        flash(f'Lien de signature envoyé à {d.client.email}.', 'success')
    except Exception as e:
        flash(f'Email non envoyé : {e}', 'error')

    return redirect(url_for('devis.detail', devis_id=d.id))


@devis_bp.route('/signer/<token>', methods=['GET', 'POST'])
def page_signature(token):
    """Page publique — le client signe son devis via ce lien unique."""
    from app.models.facture import Facture, LigneFacture
    from datetime import date, timedelta

    d = Devis.query.filter_by(token_signature=token).first_or_404()

    # Devis déjà signé
    if d.statut == 'signe':
        return render_template('devis/signature_ok.html', devis=d)

    # Devis expiré ou refusé
    if d.statut == 'refuse':
        return render_template('devis/signature_refuse.html', devis=d)

    if request.method == 'POST':
        nom_signataire = request.form.get('nom_signataire', '').strip()
        accepte        = request.form.get('accepte')

        if not nom_signataire:
            flash('Veuillez saisir votre nom complet.', 'error')
            return render_template('devis/signature.html', devis=d)
        if not accepte:
            flash('Vous devez accepter les termes du devis pour signer.', 'error')
            return render_template('devis/signature.html', devis=d)

        # Sauvegarder l'image de signature manuscrite si fournie
        sig_image_url = None
        sig_data = request.form.get('signature_image', '')
        if sig_data and sig_data.startswith('data:image/png;base64,'):
            try:
                import base64
                from flask import current_app
                img_data = base64.b64decode(sig_data.split(',', 1)[1])
                sig_dir  = os.path.join(current_app.root_path, 'static', 'uploads', 'signatures')
                os.makedirs(sig_dir, exist_ok=True)
                sig_filename = f"sig_{d.id}_{int(datetime.utcnow().timestamp())}.png"
                sig_path = os.path.join(sig_dir, sig_filename)
                with open(sig_path, 'wb') as sf:
                    sf.write(img_data)
                sig_image_url = f"uploads/signatures/{sig_filename}"
            except Exception:
                pass

        # Enregistrer la signature
        d.statut          = 'signe'
        d.signe_at        = datetime.utcnow()
        d.signature_nom   = nom_signataire
        d.signature_ip    = request.remote_addr
        d.token_signature = None  # invalider le lien après signature
        if sig_image_url and hasattr(d, 'signature_image_url'):
            d.signature_image_url = sig_image_url
        db.session.flush()

        # Générer la facture automatiquement
        facture = None
        if not Facture.query.filter_by(devis_id=d.id).first():
            count  = Facture.query.filter_by(tenant_id=d.tenant_id).count() + 1
            numero = f"FA-{datetime.utcnow().year}-{count:04d}"
            facture = Facture(
                tenant_id = d.tenant_id,
                client_id = d.client_id,
                devis_id  = d.id,
                numero    = numero,
                objet     = d.objet,
                tva_pct   = d.tva_pct,
                total_ht  = d.total_ht,
                total_tva = d.total_tva,
                total_ttc = d.total_ttc,
                echeance  = date.today() + timedelta(days=30),
                statut    = 'brouillon',
                notes     = f"Générée automatiquement depuis {d.numero} après signature.",
            )
            db.session.add(facture)
            db.session.flush()
            for ligne in d.lignes:
                db.session.add(LigneFacture(
                    facture_id    = facture.id,
                    description   = ligne.description,
                    quantite      = ligne.quantite,
                    prix_unitaire = ligne.prix_unitaire,
                    total         = ligne.total,
                    ordre         = ligne.ordre,
                ))

        db.session.commit()

        # Email de confirmation au client
        try:
            from app.services.email_service import envoyer_confirmation_signature
            envoyer_confirmation_signature(
                nom_complet    = nom_signataire,
                email          = d.client.email,
                numero_devis   = d.numero,
                montant        = d.total_ttc,
                numero_facture = facture.numero if facture else None,
            )
        except Exception:
            pass

        # Notification Make (optionnel)
        try:
            make_devis_signe(d.id, d.client.nom_complet, d.client.email, d.total_ttc)
        except Exception:
            pass

        return render_template('devis/signature_ok.html', devis=d)

    return render_template('devis/signature.html', devis=d)


@devis_bp.route('/<int:devis_id>/pdf')
@login_required
def telecharger_pdf(devis_id):
    import secrets as _secrets
    d      = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()
    tenant = current_user.tenant

    # Générer le token de signature si pas encore fait (pour le QR code)
    if not d.token_signature and d.statut not in ('signe', 'refuse'):
        d.token_signature = _secrets.token_urlsafe(32)
        db.session.commit()

    pdf    = generer_devis_pdf(d, tenant)
    return send_file(io.BytesIO(pdf), mimetype='application/pdf',
                     as_attachment=True, download_name=f'{d.numero}.pdf')

@devis_bp.route('/<int:devis_id>/supprimer', methods=['POST'])
@login_required
def supprimer(devis_id):
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()
    for ligne in d.lignes:
        db.session.delete(ligne)
    db.session.delete(d)
    db.session.commit()
    flash(f'Devis {d.numero} supprimé.', 'success')
    return redirect(url_for('devis.index'))

# ── Réunion audio ──────────────────────────────────────────────────────────────

@devis_bp.route('/reunion', methods=['GET'])
@login_required
def reunion():
    clients = Client.query.filter_by(tenant_id=current_user.tenant_id, actif=True)\
                          .order_by(Client.nom).all()
    return render_template('devis/reunion.html', clients=clients)

@devis_bp.route('/reunion/transcrire', methods=['POST'])
@login_required
def reunion_transcrire():
    """Reçoit l'audio en multipart, transcrit via Whisper."""
    audio = request.files.get('audio')
    if not audio:
        return jsonify({'error': 'Aucun fichier audio'}), 400

    audio_bytes = audio.read()
    resultat    = transcrire_audio(audio_bytes, audio.filename)
    return jsonify(resultat)

@devis_bp.route('/reunion/analyser', methods=['POST'])
@login_required
def reunion_analyser():
    """Analyse la transcription avec Claude."""
    data        = request.get_json()
    transcription = data.get('transcription', '')
    if not transcription:
        return jsonify({'error': 'Transcription vide'}), 400

    resultat = analyser_transcription(transcription)
    return jsonify(resultat)

@devis_bp.route('/reunion/generer', methods=['POST'])
@login_required
def reunion_generer():
    """Crée un devis pré-rempli depuis l'analyse IA."""
    data      = request.get_json()
    client_id = data.get('client_id')
    analyse   = data.get('analyse', {})
    tid       = current_user.tenant_id

    if not client_id:
        return jsonify({'error': 'client_id requis'}), 400

    reunion = Reunion(
        tenant_id     = tid,
        client_id     = client_id,
        user_id       = current_user.id,
        transcription = data.get('transcription', ''),
        analyse_ia    = analyse,
        besoins       = ', '.join(analyse.get('besoins', [])),
        inquietudes   = ', '.join(analyse.get('inquietudes', [])),
        budget_estime = str(analyse.get('budget', {}).get('texte_original', '')),
        deadline      = analyse.get('deadline', ''),
        prestations_ia = analyse.get('prestations', []),
        statut        = 'analyse',
    )
    db.session.add(reunion)
    db.session.flush()

    devis = Devis(
        tenant_id  = tid,
        client_id  = client_id,
        user_id    = current_user.id,
        reunion_id = reunion.id,
        numero     = _gen_numero(tid),
        objet      = f"Devis suite réunion — {analyse.get('resume', '')[:80]}",
        notes      = f"Besoins : {reunion.besoins}\nInquiétudes : {reunion.inquietudes}\nBudget : {reunion.budget_estime}",
        statut     = 'brouillon',
    )
    db.session.add(devis)
    db.session.flush()

    for p in analyse.get('prestations', []):
        ligne = LigneDevis(
            devis_id      = devis.id,
            description   = p.get('description', ''),
            quantite      = p.get('quantite', 1),
            prix_unitaire = p.get('prix_estime', 0),
            source_ia     = True,
        )
        ligne.calculer()
        db.session.add(ligne)

    db.session.flush()
    devis.calculer_totaux()
    reunion.statut = 'devis_genere'
    db.session.commit()

    return jsonify({'success': True, 'devis_id': devis.id, 'numero': devis.numero})
