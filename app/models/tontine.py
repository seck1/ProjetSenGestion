from app import db
from datetime import datetime

class Tontine(db.Model):
    __tablename__ = 'tontines'

    id           = db.Column(db.Integer, primary_key=True)
    tenant_id    = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    nom          = db.Column(db.String(150), nullable=False)
    frequence    = db.Column(db.Enum('hebdomadaire', 'mensuelle', 'trimestrielle'), default='mensuelle')
    mise         = db.Column(db.Numeric(15, 2), nullable=False)
    nb_tours     = db.Column(db.Integer, nullable=False)
    tour_actuel  = db.Column(db.Integer, default=1)
    statut       = db.Column(db.Enum('actif', 'pause', 'termine'), default='actif')
    date_debut   = db.Column(db.Date)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    membres = db.relationship('MembreTontine', backref='tontine', lazy=True, cascade='all, delete-orphan')
    tours   = db.relationship('TourTontine',   backref='tontine', lazy=True, cascade='all, delete-orphan')

    @property
    def pot_total(self):
        return self.mise * len(self.membres)

    def __repr__(self):
        return f'<Tontine {self.nom}>'


class MembreTontine(db.Model):
    __tablename__ = 'membres_tontine'

    id           = db.Column(db.Integer, primary_key=True)
    tontine_id   = db.Column(db.Integer, db.ForeignKey('tontines.id'), nullable=False)
    nom          = db.Column(db.String(150), nullable=False)
    telephone    = db.Column(db.String(20))
    position_tour = db.Column(db.Integer)  # ordre de bénéfice
    statut       = db.Column(db.Enum('actif', 'en_retard', 'sorti'), default='actif')
    dernier_paiement = db.Column(db.Date)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


class TourTontine(db.Model):
    __tablename__ = 'tours_tontine'

    id              = db.Column(db.Integer, primary_key=True)
    tontine_id      = db.Column(db.Integer, db.ForeignKey('tontines.id'), nullable=False)
    numero_tour     = db.Column(db.Integer, nullable=False)
    beneficiaire_id = db.Column(db.Integer, db.ForeignKey('membres_tontine.id'))
    montant         = db.Column(db.Numeric(15, 2))
    statut          = db.Column(db.Enum('a_venir', 'en_cours', 'termine'), default='a_venir')
    date_prevue     = db.Column(db.Date)
    date_realisee   = db.Column(db.Date)
    valide_par      = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    beneficiaire = db.relationship('MembreTontine', foreign_keys=[beneficiaire_id])
