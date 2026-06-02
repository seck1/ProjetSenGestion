from app import db
from datetime import datetime

class Client(db.Model):
    __tablename__ = 'clients'

    id          = db.Column(db.Integer, primary_key=True)
    tenant_id   = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nom         = db.Column(db.String(100), nullable=False)
    prenom      = db.Column(db.String(100))
    entreprise  = db.Column(db.String(150))
    fonction    = db.Column(db.String(100))
    email       = db.Column(db.String(150))
    telephone   = db.Column(db.String(20))
    adresse     = db.Column(db.Text)
    source      = db.Column(db.Enum('scan_carte', 'qrcode', 'tally', 'manuel'), default='manuel')
    confiance_ia = db.Column(db.Integer)  # % confiance extraction Claude
    notes       = db.Column(db.Text)
    actif       = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    devis    = db.relationship('Devis',   backref='client', lazy=True)
    factures = db.relationship('Facture', backref='client', lazy=True)

    @property
    def nom_complet(self):
        return f'{self.prenom or ""} {self.nom}'.strip()

    @property
    def initiales(self):
        parts = [self.prenom or '', self.nom or '']
        return ''.join(p[0].upper() for p in parts if p)[:2]

    def __repr__(self):
        return f'<Client {self.nom_complet}>'
