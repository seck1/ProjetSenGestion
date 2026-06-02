from app import db
from datetime import datetime

class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'

    id           = db.Column(db.Integer, primary_key=True)
    tenant_id    = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nom          = db.Column(db.String(255), nullable=False)
    categorie    = db.Column(db.Enum(
        'transport', 'repas', 'fournitures', 'communication',
        'loyer', 'salaires', 'hebergement', 'divers'
    ), default='divers')
    telephone    = db.Column(db.String(50))
    email        = db.Column(db.String(255))
    adresse      = db.Column(db.Text)
    ninea        = db.Column(db.String(50))
    site_web     = db.Column(db.String(255))
    notes        = db.Column(db.Text)
    actif        = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    depenses     = db.relationship('Depense', backref='fournisseur', lazy='dynamic',
                                   foreign_keys='Depense.fournisseur_id')

    def __repr__(self):
        return f'<Fournisseur {self.nom}>'
