from app import db
from datetime import datetime

class Devis(db.Model):
    __tablename__ = 'devis'

    id            = db.Column(db.Integer, primary_key=True)
    tenant_id     = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    client_id     = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'))
    reunion_id    = db.Column(db.Integer, db.ForeignKey('reunions.id'), nullable=True)
    numero        = db.Column(db.String(30), unique=True)  # DV-2026-0142
    statut        = db.Column(db.Enum('brouillon', 'envoye', 'ouvert', 'signe', 'refuse'), default='brouillon')
    objet         = db.Column(db.String(255))
    notes         = db.Column(db.Text)
    conditions    = db.Column(db.Text)
    tva_pct       = db.Column(db.Numeric(5, 2), default=18.00)
    remise_pct    = db.Column(db.Numeric(5, 2), default=0.00)
    total_ht      = db.Column(db.Numeric(15, 2), default=0)
    total_tva     = db.Column(db.Numeric(15, 2), default=0)
    total_ttc     = db.Column(db.Numeric(15, 2), default=0)
    valide_jusqu  = db.Column(db.Date)
    envoye_at     = db.Column(db.DateTime)
    ouvert_at     = db.Column(db.DateTime)
    signe_at      = db.Column(db.DateTime)
    signature_nom = db.Column(db.String(150))
    token_signature = db.Column(db.String(64), unique=True)
    signature_ip    = db.Column(db.String(45))
    pdf_url       = db.Column(db.String(255))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lignes   = db.relationship('LigneDevis', backref='devis', lazy=True, cascade='all, delete-orphan')
    factures = db.relationship('Facture',    backref='devis', lazy=True)

    def calculer_totaux(self):
        from decimal import Decimal
        self.total_ht  = sum((l.total or Decimal('0') for l in self.lignes), Decimal('0'))
        tva_pct        = Decimal(str(self.tva_pct))
        self.total_tva = self.total_ht * tva_pct / Decimal('100')
        self.total_ttc = self.total_ht + self.total_tva

    @property
    def statut_label(self):
        labels = {
            'brouillon': 'Brouillon', 'envoye': 'Envoyé',
            'ouvert': 'Ouvert', 'signe': 'Signé', 'refuse': 'Refusé'
        }
        return labels.get(self.statut, self.statut)

    def __repr__(self):
        return f'<Devis {self.numero}>'


class LigneDevis(db.Model):
    __tablename__ = 'lignes_devis'

    id          = db.Column(db.Integer, primary_key=True)
    devis_id    = db.Column(db.Integer, db.ForeignKey('devis.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantite    = db.Column(db.Numeric(10, 2), default=1)
    prix_unitaire = db.Column(db.Numeric(15, 2), nullable=False)
    total       = db.Column(db.Numeric(15, 2))
    ordre       = db.Column(db.Integer, default=0)
    source_ia   = db.Column(db.Boolean, default=False)

    def calculer(self):
        from decimal import Decimal
        self.total = Decimal(str(self.quantite)) * Decimal(str(self.prix_unitaire))
