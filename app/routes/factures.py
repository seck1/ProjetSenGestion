from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user
from app.models.facture import Facture, LigneFacture
from app.models.devis   import Devis
from app import db
from app.services.pdf_service  import generer_devis_pdf, generer_facture_pdf
from app.services.make_service import facture_generee as make_facture_generee
from datetime import datetime
import io

factures_bp = Blueprint('factures', __name__, url_prefix='/factures')

def _gen_numero(tenant_id):
    count = Facture.query.filter_by(tenant_id=tenant_id).count() + 1
    return f"FA-{datetime.utcnow().year}-{count:04d}"

@factures_bp.route('/')
@login_required
def index():
    factures = Facture.query.filter_by(tenant_id=current_user.tenant_id)\
                            .order_by(Facture.created_at.desc()).all()
    return render_template('factures/index.html', factures=factures)

@factures_bp.route('/depuis-devis/<int:devis_id>', methods=['POST'])
@login_required
def depuis_devis(devis_id):
    """Convertit un devis signé en facture."""
    d = Devis.query.filter_by(id=devis_id, tenant_id=current_user.tenant_id).first_or_404()

    facture = Facture(
        tenant_id  = current_user.tenant_id,
        client_id  = d.client_id,
        devis_id   = d.id,
        numero     = _gen_numero(current_user.tenant_id),
        objet      = d.objet,
        tva_pct    = d.tva_pct,
        total_ht   = d.total_ht,
        total_tva  = d.total_tva,
        total_ttc  = d.total_ttc,
        statut     = 'envoyee',
    )
    db.session.add(facture)
    db.session.flush()

    for ld in d.lignes:
        lf = LigneFacture(
            facture_id    = facture.id,
            description   = ld.description,
            quantite      = ld.quantite,
            prix_unitaire = ld.prix_unitaire,
            total         = ld.total,
            ordre         = ld.ordre,
        )
        db.session.add(lf)

    db.session.commit()

    make_facture_generee(
        facture.id, d.client.nom_complet,
        d.client.email, facture.total_ttc, facture.echeance
    )
    flash(f'Facture {facture.numero} générée et envoyée au client.', 'success')
    return redirect(url_for('factures.detail', facture_id=facture.id))

@factures_bp.route('/<int:facture_id>')
@login_required
def detail(facture_id):
    facture = Facture.query.filter_by(id=facture_id, tenant_id=current_user.tenant_id).first_or_404()
    return render_template('factures/detail.html', facture=facture)

@factures_bp.route('/<int:facture_id>/pdf')
@login_required
def telecharger_pdf(facture_id):
    facture = Facture.query.filter_by(id=facture_id, tenant_id=current_user.tenant_id).first_or_404()
    tenant  = current_user.tenant
    pdf     = generer_facture_pdf(facture, tenant)
    return send_file(
        io.BytesIO(pdf),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'{facture.numero}.pdf'
    )

@factures_bp.route('/<int:facture_id>/marquer-payee', methods=['POST'])
@login_required
def marquer_payee(facture_id):
    facture = Facture.query.filter_by(id=facture_id, tenant_id=current_user.tenant_id).first_or_404()
    facture.statut   = 'payee'
    facture.payee_at = datetime.utcnow()
    db.session.commit()
    flash('Facture marquée comme payée.', 'success')
    return redirect(url_for('factures.detail', facture_id=facture.id))
