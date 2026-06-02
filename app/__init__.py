from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config.settings import config

db       = SQLAlchemy()
migrate  = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app(env='default'):
    app = Flask(__name__)
    app.config.from_object(config[env])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.clients   import clients_bp
    from app.routes.devis     import devis_bp
    from app.routes.factures  import factures_bp
    from app.routes.depenses  import depenses_bp
    from app.routes.tontines  import tontines_bp
    from app.routes.webhooks  import webhooks_bp
    from app.routes.rapports  import rapports_bp
    from app.routes.settings  import settings_bp
    from app.routes.contacts  import contacts_bp
    from app.routes.fournisseurs import fournisseurs_bp
    from app.routes.telegram  import telegram_bp
    from app.routes.admin     import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(fournisseurs_bp)
    app.register_blueprint(devis_bp)
    app.register_blueprint(factures_bp)
    app.register_blueprint(depenses_bp)
    app.register_blueprint(tontines_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(rapports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(admin_bp)

    return app
