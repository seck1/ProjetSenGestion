import os, io, requests
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.user import User
from app.models.client import Client
from app.models.devis import Devis

telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')


def bot_token():
    return current_app.config.get('TELEGRAM_BOT_TOKEN', '')


def send_message(chat_id, text, parse_mode='Markdown'):
    token = bot_token()
    if not token:
        return
    requests.post(
        f'https://api.telegram.org/bot{token}/sendMessage',
        json={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode},
        timeout=10
    )


def download_file(file_id) -> bytes:
    token = bot_token()
    info = requests.get(
        f'https://api.telegram.org/bot{token}/getFile',
        params={'file_id': file_id}, timeout=10
    ).json()
    file_path = info['result']['file_path']
    r = requests.get(
        f'https://api.telegram.org/file/bot{token}/{file_path}',
        timeout=30
    )
    return r.content


@telegram_bp.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    message = data.get('message') or data.get('edited_message')
    if not message:
        return jsonify({'ok': True})

    chat_id  = str(message['chat']['id'])
    text     = message.get('text', '').strip()
    voice    = message.get('voice')

    # ── /start → connexion par email ──────────────────────────
    if text.startswith('/start'):
        send_message(chat_id,
            "👋 Bienvenue sur *SenGestion Bot* !\n\n"
            "Pour connecter votre compte, envoyez votre adresse email SenGestion.\n"
            "Exemple : `a.diop@teranga-conseil.sn`"
        )
        return jsonify({'ok': True})

    # ── /deconnect ────────────────────────────────────────────
    if text.startswith('/deconnect'):
        user = User.query.filter_by(telegram_chat_id=chat_id).first()
        if user:
            user.telegram_chat_id   = None
            user.telegram_connected = False
            db.session.commit()
            send_message(chat_id, "✅ Votre compte a été déconnecté de Telegram.")
        return jsonify({'ok': True})

    # ── Connexion par email ───────────────────────────────────
    user = User.query.filter_by(telegram_chat_id=chat_id).first()
    if not user:
        # Chercher l'utilisateur par email
        email = text.lower().strip()
        candidate = User.query.filter_by(email=email, actif=True).first()
        if candidate:
            candidate.telegram_chat_id   = chat_id
            candidate.telegram_connected = True
            db.session.commit()
            send_message(chat_id,
                f"✅ Compte connecté avec succès !\n\n"
                f"Bonjour *{candidate.nom_complet}* 👋\n"
                f"Entreprise : *{candidate.tenant.nom}*\n\n"
                f"Vous pouvez maintenant :\n"
                f"• Envoyer un *message vocal* pour créer un devis\n"
                f"• Écrire *nouveau devis* + description\n"
                f"• Écrire *aide* pour voir toutes les commandes"
            )
        else:
            send_message(chat_id,
                "❌ Aucun compte trouvé avec cet email.\n"
                "Vérifiez l'adresse et réessayez."
            )
        return jsonify({'ok': True})

    # ── Commandes utilisateur connecté ────────────────────────
    if text.lower() in ('aide', '/aide', '/help'):
        send_message(chat_id,
            f"📋 *Commandes disponibles*\n\n"
            f"🎤 *Message vocal* → Transcription + création devis\n"
            f"✍️ *nouveau devis [description]* → Créer un devis\n"
            f"📊 *mes devis* → Voir vos derniers devis\n"
            f"👥 *mes clients* → Voir vos clients\n"
            f"/deconnect → Déconnecter ce compte"
        )
        return jsonify({'ok': True})

    # ── Message vocal ─────────────────────────────────────────
    if voice:
        send_message(chat_id, "🎤 Message reçu, transcription en cours…")
        try:
            audio_bytes = download_file(voice['file_id'])
            from app.services.whisper_service import transcrire_audio
            transcription = transcrire_audio(audio_bytes)
            send_message(chat_id, f"📝 *Transcription :*\n_{transcription}_\n\nAnalyse en cours…")
            _creer_devis_depuis_texte(user, chat_id, transcription)
        except Exception as e:
            send_message(chat_id, f"❌ Erreur lors de la transcription : {str(e)}")
        return jsonify({'ok': True})

    # ── Nouveau devis par texte ───────────────────────────────
    if text.lower().startswith('nouveau devis'):
        description = text[13:].strip()
        if not description:
            send_message(chat_id, "✍️ Décrivez le devis après \"nouveau devis\"\nEx: _nouveau devis site web pour restaurant 500 000 FCFA_")
            return jsonify({'ok': True})
        send_message(chat_id, "⚙️ Analyse en cours…")
        _creer_devis_depuis_texte(user, chat_id, description)
        return jsonify({'ok': True})

    # ── Mes devis ─────────────────────────────────────────────
    if text.lower() in ('mes devis', '/devis'):
        devis_list = Devis.query.filter_by(tenant_id=user.tenant_id)\
                               .order_by(Devis.created_at.desc()).limit(5).all()
        if not devis_list:
            send_message(chat_id, "📄 Aucun devis pour l'instant.")
        else:
            lines = ["📄 *Vos 5 derniers devis :*\n"]
            for d in devis_list:
                lines.append(f"• *{d.numero}* — {d.statut} — {float(d.montant_ttc or 0):,.0f} FCFA")
            send_message(chat_id, '\n'.join(lines))
        return jsonify({'ok': True})

    # ── Mes clients ───────────────────────────────────────────
    if text.lower() in ('mes clients', '/clients'):
        clients = Client.query.filter_by(tenant_id=user.tenant_id)\
                              .order_by(Client.created_at.desc()).limit(5).all()
        if not clients:
            send_message(chat_id, "👥 Aucun client pour l'instant.")
        else:
            lines = ["👥 *Vos 5 derniers clients :*\n"]
            for c in clients:
                lines.append(f"• *{c.nom_complet}* — {c.entreprise or ''}")
            send_message(chat_id, '\n'.join(lines))
        return jsonify({'ok': True})

    # ── Message non reconnu ───────────────────────────────────
    send_message(chat_id,
        "🤔 Je n'ai pas compris. Envoyez *aide* pour voir les commandes disponibles."
    )
    return jsonify({'ok': True})


def _creer_devis_depuis_texte(user, chat_id, texte):
    """Analyse le texte avec Claude et crée un devis brouillon."""
    try:
        from app.services.claude_service import analyser_transcription
        analyse = analyser_transcription(texte)

        if not analyse.get('success'):
            send_message(chat_id, f"❌ Erreur analyse : {analyse.get('error')}")
            return

        # Trouver ou créer le client
        client_data = analyse.get('client', {})
        client = None
        if client_data.get('email'):
            client = Client.query.filter_by(
                tenant_id=user.tenant_id,
                email=client_data['email']
            ).first()
        if not client and client_data.get('nom'):
            client = Client.query.filter_by(
                tenant_id=user.tenant_id,
                nom=client_data['nom']
            ).first()

        # Construire les lignes du devis
        prestations = analyse.get('prestations', [])
        lignes = []
        for p in prestations:
            lignes.append({
                'description': p.get('description', ''),
                'quantite': p.get('quantite', 1),
                'prix_unitaire': p.get('prix_estime', 0),
            })
        if not lignes:
            lignes = [{'description': texte[:200], 'quantite': 1, 'prix_unitaire': 0}]

        montant_ht  = sum(l['quantite'] * l['prix_unitaire'] for l in lignes)
        montant_ttc = montant_ht * 1.18  # TVA 18%

        # Générer numéro devis
        from datetime import date
        import random
        numero = f"DEV-TG-{date.today().strftime('%Y%m')}-{random.randint(100,999)}"

        devis = Devis(
            tenant_id   = user.tenant_id,
            client_id   = client.id if client else None,
            numero      = numero,
            statut      = 'brouillon',
            montant_ht  = montant_ht,
            montant_ttc = montant_ttc,
            notes       = analyse.get('resume', ''),
        )
        db.session.add(devis)
        db.session.commit()

        client_nom = client.nom_complet if client else (client_data.get('nom') or 'Client à définir')
        nb_lignes  = len(lignes)

        send_message(chat_id,
            f"✅ *Devis créé avec succès !*\n\n"
            f"📋 Numéro : *{numero}*\n"
            f"👤 Client : *{client_nom}*\n"
            f"📦 {nb_lignes} prestation(s)\n"
            f"💰 Montant TTC : *{montant_ttc:,.0f} FCFA*\n\n"
            f"Connectez-vous sur SenGestion pour finaliser et envoyer le devis."
        )

    except Exception as e:
        send_message(chat_id, f"❌ Erreur création devis : {str(e)}")
