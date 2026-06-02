from app import db
from datetime import datetime

class Depense(db.Model):
    __tablename__ = 'depenses'

    id          = db.Column(db.Integer, primary_key=True)
    tenant_id   = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'))
    libelle     = db.Column(db.String(255), nullable=False)
    categorie   = db.Column(db.Enum(
        'transport', 'repas', 'fournitures', 'communication',
        'loyer', 'salaires', 'hebergement', 'divers'
    ), default='divers')
    montant     = db.Column(db.Numeric(15, 2), nullable=False)
    source      = db.Column(db.Enum('manuel', 'scan_recu', 'wave'), default='manuel')
    justificatif_url = db.Column(db.String(255))
    date_depense = db.Column(db.Date, default=datetime.utcnow)
    notes       = db.Column(db.Text)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Depense {self.libelle} {self.montant}>'
