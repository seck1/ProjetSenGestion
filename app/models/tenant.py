from app import db
from datetime import datetime

class Tenant(db.Model):
    __tablename__ = 'tenants'

    id         = db.Column(db.Integer, primary_key=True)
    nom        = db.Column(db.String(150), nullable=False)
    ninea      = db.Column(db.String(50))
    email      = db.Column(db.String(150))
    telephone  = db.Column(db.String(20))
    adresse    = db.Column(db.Text)
    logo_url      = db.Column(db.String(255))
    cachet_url    = db.Column(db.String(255))
    signature_url = db.Column(db.String(255))
    plan       = db.Column(db.Enum('starter', 'pro', 'enterprise'), default='starter')
    nb_sieges  = db.Column(db.Integer, default=1)
    actif      = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users    = db.relationship('User',    backref='tenant', lazy=True)
    clients  = db.relationship('Client',  backref='tenant', lazy=True)
    devis    = db.relationship('Devis',   backref='tenant', lazy=True)
    depenses = db.relationship('Depense', backref='tenant', lazy=True)
    tontines = db.relationship('Tontine', backref='tenant', lazy=True)

    def __repr__(self):
        return f'<Tenant {self.nom}>'
