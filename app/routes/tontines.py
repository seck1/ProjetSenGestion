from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models.tontine import Tontine, MembreTontine, TourTontine
from app import db
from datetime import date

tontines_bp = Blueprint('tontines', __name__, url_prefix='/tontines')

@tontines_bp.route('/')
@login_required
def index():
    tontines = Tontine.query.filter_by(tenant_id=current_user.tenant_id)\
                            .order_by(Tontine.created_at.desc()).all()
    selected_id = request.args.get('id', type=int)
    selected    = None
    if selected_id:
        selected = Tontine.query.filter_by(id=selected_id, tenant_id=current_user.tenant_id).first()
    elif tontines:
        selected = tontines[0]

    return render_template('tontines/index.html', tontines=tontines, selected=selected)

@tontines_bp.route('/creer', methods=['POST'])
@login_required
def creer():
    t = Tontine(
        tenant_id  = current_user.tenant_id,
        nom        = request.form.get('nom', '').strip(),
        frequence  = request.form.get('frequence', 'mensuelle'),
        mise       = float(request.form.get('mise', 0)),
        nb_tours   = int(request.form.get('nb_tours', 1)),
        date_debut = date.fromisoformat(request.form.get('date_debut')) if request.form.get('date_debut') else date.today(),
    )
    db.session.add(t)
    db.session.commit()
    flash(f'Tontine « {t.nom} » créée.', 'success')
    return redirect(url_for('tontines.index'))

@tontines_bp.route('/<int:tontine_id>/valider-tour', methods=['POST'])
@login_required
def valider_tour(tontine_id):
    t = Tontine.query.filter_by(id=tontine_id, tenant_id=current_user.tenant_id).first_or_404()
    tour = TourTontine.query.filter_by(tontine_id=t.id, numero_tour=t.tour_actuel).first()
    if tour:
        tour.statut         = 'termine'
        tour.date_realisee  = date.today()
        tour.valide_par     = current_user.id
    t.tour_actuel += 1
    if t.tour_actuel > t.nb_tours:
        t.statut = 'termine'
    db.session.commit()
    flash('Tour validé avec succès.', 'success')
    return redirect(url_for('tontines.index', id=tontine_id))
