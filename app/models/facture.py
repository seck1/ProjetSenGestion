from app import db
from datetime import datetime

class Facture(db.Model):
    __tablename__ = 'factures'

    id          = db.Column(db.Integer, primary_key=True)
    tenant_id   = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    client_id   = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    devis_id    = db.Column(db.Integer, db.ForeignKey('devis.id'), nullable=True)
    numero      = db.Column(db.String(30), unique=True)  # FA-2026-0142
    statut      = db.Column(db.Enum('brouillon', 'envoyee', 'payee', 'en_retard', 'annulee'), default='brouillon')
    objet       = db.Column(db.String(255))
    tva_pct     = db.Column(db.Numeric(5, 2), default=18.00)
    total_ht    = db.Column(db.Numeric(15, 2), default=0)
    total_tva   = db.Column(db.Numeric(15, 2), default=0)
    total_ttc   = db.Column(db.Numeric(15, 2), default=0)
    echeance    = db.Column(db.Date)
    payee_at    = db.Column(db.DateTime)
    pdf_url     = db.Column(db.String(255))
    notes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    lignes = db.relationship('LigneFacture', backref='facture', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Facture {self.numero}>'


class LigneFacture(db.Model):
    __tablename__ = 'lignes_facture'

    id            = db.Column(db.Integer, primary_key=True)
    facture_id    = db.Column(db.Integer, db.ForeignKey('factures.id'), nullable=False)
    description   = db.Column(db.Text, nullable=False)
    quantite      = db.Column(db.Numeric(10, 2), default=1)
    prix_unitaire = db.Column(db.Numeric(15, 2), nullable=False)
    total         = db.Column(db.Numeric(15, 2))
    ordre         = db.Column(db.Integer, default=0)
