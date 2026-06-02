from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    tenant_id  = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nom        = db.Column(db.String(100), nullable=False)
    prenom     = db.Column(db.String(100))
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.Enum('super_admin', 'admin', 'commercial', 'comptable'), default='commercial')
    actif      = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    telegram_chat_id   = db.Column(db.String(50), nullable=True, unique=True)
    telegram_connected = db.Column(db.Boolean, default=False)
    token_validation   = db.Column(db.String(100), nullable=True)
    email_valide       = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @property
    def initiales(self):
        parts = [self.prenom or '', self.nom or '']
        return ''.join(p[0].upper() for p in parts if p)

    @property
    def nom_complet(self):
        return f'{self.prenom or ""} {self.nom}'.strip()

    def __repr__(self):
        return f'<User {self.email}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
