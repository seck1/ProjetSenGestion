from openai import OpenAI
from flask import current_app
import tempfile, os

def transcrire_audio(audio_bytes: bytes, filename: str = 'audio.webm') -> dict:
    """
    Envoie un fichier audio à OpenAI Whisper pour transcription.
    Retourne {'success': True, 'texte': '...'} ou {'success': False, 'error': '...'}
    """
    client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])

    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model='whisper-1',
                file=f,
                language='fr',
                response_format='text',
            )
        return {'success': True, 'texte': response}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        os.unlink(tmp_path)
