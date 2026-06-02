from app import db
from datetime import datetime

class Contact(db.Model):
    __tablename__ = 'contacts'

    id           = db.Column(db.Integer, primary_key=True)
    tenant_id    = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nom          = db.Column(db.String(100), nullable=False)
    prenom       = db.Column(db.String(100))
    entreprise   = db.Column(db.String(150))
    fonction     = db.Column(db.String(100))
    email        = db.Column(db.String(150))
    telephone    = db.Column(db.String(20))
    adresse      = db.Column(db.Text)
    site_web     = db.Column(db.String(255))
    notes        = db.Column(db.Text)
    source       = db.Column(db.Enum('scan_carte', 'qrcode', 'manuel'), default='manuel')
    confiance_ia = db.Column(db.Integer)
    evenement    = db.Column(db.String(150))  # nom du salon / événement
    converti_client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nom_complet(self):
        return f'{self.prenom or ""} {self.nom}'.strip()

    @property
    def initiales(self):
        parts = [self.prenom or '', self.nom or '']
        return ''.join(p[0].upper() for p in parts if p)[:2]

    @property
    def est_converti(self):
        return self.converti_client_id is not None

    def __repr__(self):
        return f'<Contact {self.nom_complet}>'
