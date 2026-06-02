import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}/"
        f"{os.getenv('DB_NAME', 'sengestion_flask')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    OPENAI_API_KEY    = os.getenv('OPENAI_API_KEY')

    MAKE_WEBHOOKS = {
        'devis_envoye':      os.getenv('MAKE_WEBHOOK_DEVIS_ENVOYE'),
        'devis_signe':       os.getenv('MAKE_WEBHOOK_DEVIS_SIGNE'),
        'devis_non_ouvert':  os.getenv('MAKE_WEBHOOK_DEVIS_NON_OUVERT'),
        'reunion_planifiee': os.getenv('MAKE_WEBHOOK_REUNION_PLANIFIEE'),
        'facture_generee':   os.getenv('MAKE_WEBHOOK_FACTURE_GENEREE'),
        'signature':         os.getenv('MAKE_WEBHOOK_SIGNATURE'),
    }

    TALLY_WEBHOOK_SECRET   = os.getenv('TALLY_WEBHOOK_SECRET')
    TELEGRAM_BOT_TOKEN     = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_BOT_USERNAME  = os.getenv('TELEGRAM_BOT_USERNAME', 'SenGestion_bot')

    MAIL_SERVER         = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT           = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME       = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD       = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'sengestion1@gmail.com')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
