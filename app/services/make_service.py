import requests
from flask import current_app

def trigger(scenario: str, payload: dict) -> bool:
    """
    Déclenche un scénario Make via webhook.
    scenario : clé dans MAKE_WEBHOOKS ('devis_envoye', 'devis_signe', etc.)
    """
    url = current_app.config['MAKE_WEBHOOKS'].get(scenario)
    if not url:
        return False
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code < 400
    except requests.RequestException:
        return False

def devis_envoye(devis_id, client_nom, client_tel, client_email, montant):
    return trigger('devis_envoye', {
        'devis_id':    devis_id,
        'client_nom':  client_nom,
        'client_tel':  client_tel,
        'client_email': client_email,
        'montant':     str(montant),
    })

def devis_signe(devis_id, client_nom, client_email, montant):
    return trigger('devis_signe', {
        'devis_id':    devis_id,
        'client_nom':  client_nom,
        'client_email': client_email,
        'montant':     str(montant),
    })

def devis_non_ouvert(devis_id, client_nom, client_tel):
    return trigger('devis_non_ouvert', {
        'devis_id':   devis_id,
        'client_nom': client_nom,
        'client_tel': client_tel,
    })

def reunion_planifiee(titre, date_reunion, client_nom, user_email):
    return trigger('reunion_planifiee', {
        'titre':       titre,
        'date':        str(date_reunion),
        'client_nom':  client_nom,
        'user_email':  user_email,
    })

def facture_generee(facture_id, client_nom, client_email, montant, echeance):
    return trigger('facture_generee', {
        'facture_id':  facture_id,
        'client_nom':  client_nom,
        'client_email': client_email,
        'montant':     str(montant),
        'echeance':    str(echeance),
    })

def demander_signature(devis_id, numero, client_nom, client_email, montant, pdf_url, callback_url):
    """Déclenche le scénario Make qui crée la procédure Yousign et envoie le lien au client."""
    return trigger('signature', {
        'devis_id':     devis_id,
        'numero':       numero,
        'client_nom':   client_nom,
        'client_email': client_email,
        'montant':      str(montant),
        'pdf_url':      pdf_url,
        'callback_url': callback_url,
    })
