from app import db
from datetime import datetime

class Reunion(db.Model):
    __tablename__ = 'reunions'

    id              = db.Column(db.Integer, primary_key=True)
    tenant_id       = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    client_id       = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'))
    titre           = db.Column(db.String(255))
    date_reunion    = db.Column(db.DateTime)
    duree_secondes  = db.Column(db.Integer)
    audio_url       = db.Column(db.String(255))
    transcription   = db.Column(db.Text)
    analyse_ia      = db.Column(db.JSON)  # résultat brut Claude
    besoins         = db.Column(db.Text)
    inquietudes     = db.Column(db.Text)
    budget_estime   = db.Column(db.String(100))
    deadline        = db.Column(db.String(100))
    prestations_ia  = db.Column(db.JSON)  # liste des prestations détectées
    statut          = db.Column(db.Enum('en_cours', 'transcrit', 'analyse', 'devis_genere'), default='en_cours')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    devis = db.relationship('Devis', backref='reunion', lazy=True)

    def __repr__(self):
        return f'<Reunion {self.titre}>'
