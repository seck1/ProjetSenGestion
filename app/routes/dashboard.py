from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.devis   import Devis
from app.models.facture import Facture
from app.models.depense import Depense
from sqlalchemy import func
from datetime import datetime
from dateutil.relativedelta import relativedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    tid = current_user.tenant_id
    now = datetime.utcnow()
    mois_courant  = now.month
    annee_courant = now.year
    mois_precedent = (now - relativedelta(months=1))

    # Revenue for current month
    ca_mois = (Devis.query
               .filter_by(tenant_id=tid, statut='signe')
               .filter(func.month(Devis.signe_at) == mois_courant,
                       func.year(Devis.signe_at)  == annee_courant)
               .with_entities(func.sum(Devis.total_ttc))
               .scalar() or 0)

    # Previous month revenue for variation calculation
    ca_mois_prec = (Devis.query
               .filter_by(tenant_id=tid, statut='signe')
               .filter(func.month(Devis.signe_at) == mois_precedent.month,
                       func.year(Devis.signe_at)  == mois_precedent.year)
               .with_entities(func.sum(Devis.total_ttc))
               .scalar() or 0)

    if ca_mois_prec > 0:
        ca_variation = round((ca_mois - ca_mois_prec) / ca_mois_prec * 100)
    else:
        ca_variation = None

    # Unpaid invoices
    factures_impayees = Facture.query.filter(
        Facture.tenant_id == tid,
        Facture.statut.in_(['envoyee', 'en_retard'])
    ).all()
    montant_impaye = sum(f.total_ttc for f in factures_impayees)

    # Signed quotes this month
    devis_signes_q = Devis.query.filter(
        Devis.tenant_id == tid,
        Devis.statut == 'signe',
        func.month(Devis.signe_at) == mois_courant,
        func.year(Devis.signe_at)  == annee_courant
    ).all()
    devis_signes_count   = len(devis_signes_q)
    devis_signes_montant = sum(d.total_ttc for d in devis_signes_q)

    # Annual revenue
    ca_annuel = (Devis.query
                 .filter_by(tenant_id=tid, statut='signe')
                 .filter(func.year(Devis.signe_at) == annee_courant)
                 .with_entities(func.sum(Devis.total_ttc))
                 .scalar() or 0)

    # Expenses for current month
    charges_mois = (Depense.query
                    .filter_by(tenant_id=tid)
                    .filter(func.month(Depense.date_depense) == mois_courant,
                            func.year(Depense.date_depense)  == annee_courant)
                    .with_entities(func.sum(Depense.montant))
                    .scalar() or 0)

    # Unpaid invoices (re-query after expenses for template context)
    factures_impayees = Facture.query.filter(
        Facture.tenant_id == tid,
        Facture.statut.in_(['envoyee', 'en_retard'])
    ).all()
    montant_impaye = sum(f.total_ttc for f in factures_impayees)

    # Latest activity — last 10 quotes
    derniers_devis = (Devis.query
                      .filter_by(tenant_id=tid)
                      .order_by(Devis.created_at.desc())
                      .limit(10).all())

    return render_template('dashboard/index.html',
        ca_mois=ca_mois,
        ca_annuel=ca_annuel,
        ca_variation=ca_variation,
        devis_signes_count=devis_signes_count,
        devis_signes_montant=devis_signes_montant,
        charges_mois=charges_mois,
        factures_impayees=factures_impayees,
        montant_impaye=montant_impaye,
        derniers_devis=derniers_devis,
        annee=annee_courant,
        mois_label=(['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'][now.month-1] + ' ' + str(annee_courant)),
        user_prenom=current_user.prenom or current_user.nom,
    )
