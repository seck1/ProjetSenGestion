import anthropic
import json
from flask import current_app

def get_client():
    return anthropic.Anthropic(api_key=current_app.config['ANTHROPIC_API_KEY'])

def scanner_carte_visite(image_b64: str) -> dict:
    """
    Envoie une image base64 à Claude Vision pour extraire les coordonnées
    d'une carte de visite. Retourne un dict avec les champs et scores de confiance.
    """
    client = get_client()

    # Détecter le format de l'image
    if image_b64.startswith('data:'):
        media_type = image_b64.split(';')[0].split(':')[1]
        image_data = image_b64.split(',')[1]
    else:
        media_type = 'image/jpeg'
        image_data = image_b64

    message = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=1024,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': media_type,
                        'data': image_data,
                    }
                },
                {
                    'type': 'text',
                    'text': """Analyse cette carte de visite et extrait les informations.
Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.
Format attendu :
{
  "nom": "",
  "prenom": "",
  "entreprise": "",
  "fonction": "",
  "email": "",
  "telephone": "",
  "adresse": "",
  "site_web": "",
  "confiances": {
    "nom": 95,
    "prenom": 90,
    "entreprise": 98,
    "fonction": 85,
    "email": 99,
    "telephone": 97,
    "adresse": 70,
    "site_web": 95
  }
}
Si un champ n'est pas visible, laisse une chaîne vide. La confiance est un entier entre 0 et 100."""
                }
            ]
        }]
    )

    try:
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        confiance_globale = int(
            sum(data.get('confiances', {}).values()) /
            max(len(data.get('confiances', {1: 1})), 1)
        )
        return {
            'success': True,
            'champs': {
                'nom':        data.get('nom', ''),
                'prenom':     data.get('prenom', ''),
                'entreprise': data.get('entreprise', ''),
                'fonction':   data.get('fonction', ''),
                'email':      data.get('email', ''),
                'telephone':  data.get('telephone', ''),
                'adresse':    data.get('adresse', ''),
                'site_web':   data.get('site_web', ''),
            },
            'confiances':         data.get('confiances', {}),
            'confiance_globale':  confiance_globale,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {'success': False, 'error': str(e)}


def analyser_facture(image_b64: str) -> dict:
    """Analyse une photo de facture/reçu et extrait les informations comptables."""
    client = get_client()

    if image_b64.startswith('data:'):
        media_type = image_b64.split(';')[0].split(':')[1]
        image_data = image_b64.split(',')[1]
    else:
        media_type = 'image/jpeg'
        image_data = image_b64

    message = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=1024,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {'type': 'base64', 'media_type': media_type, 'data': image_data}
                },
                {
                    'type': 'text',
                    'text': """Analyse cette facture ou ce reçu et extrait les informations.
Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.
Format :
{
  "fournisseur": "",
  "libelle": "",
  "montant_ttc": 0,
  "montant_ht": 0,
  "tva": 0,
  "devise": "FCFA",
  "date": "",
  "numero_facture": "",
  "categorie": "",
  "notes": ""
}
Pour "categorie", choisis parmi : transport, repas, fournitures, communication, loyer, salaires, hebergement, divers.
Pour "date", utilise le format YYYY-MM-DD. Si non visible, laisse vide.
Pour les montants, mets 0 si non visible."""
                }
            ]
        }]
    )

    try:
        raw = message.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
        data = json.loads(raw)
        return {'success': True, 'champs': data}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {'success': False, 'error': str(e)}


def analyser_transcription(transcription: str, catalogue: list = None) -> dict:
    """
    Analyse une transcription de réunion pour extraire :
    - client identifié
    - besoins / prestations
    - inquiétudes
    - budget évoqué
    - deadline
    - estimation de prix
    """
    client = get_client()

    catalogue_txt = ''
    if catalogue:
        catalogue_txt = '\n'.join(f'- {item}' for item in catalogue)

    message = client.messages.create(
        model='claude-opus-4-7',
        max_tokens=2048,
        messages=[{
            'role': 'user',
            'content': f"""Tu es un assistant commercial pour une PME sénégalaise.
Analyse cette transcription de réunion client et extrais les informations clés.

Transcription :
{transcription}

{f"Catalogue de services disponibles :{chr(10)}{catalogue_txt}" if catalogue_txt else ""}

Réponds UNIQUEMENT avec un JSON valide :
{{
  "client": {{
    "nom": "",
    "entreprise": "",
    "telephone": "",
    "email": ""
  }},
  "besoins": ["besoin 1", "besoin 2"],
  "inquietudes": ["inquiétude 1", "inquiétude 2"],
  "budget": {{
    "min": 0,
    "max": 0,
    "devise": "FCFA",
    "texte_original": ""
  }},
  "deadline": "",
  "prestations": [
    {{
      "description": "",
      "quantite": 1,
      "prix_estime": 0,
      "confiance": 90
    }}
  ],
  "resume": "",
  "date_reunion": ""
}}"""
        }]
    )

    try:
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        return {'success': True, **data}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {'success': False, 'error': str(e)}
