from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.fournisseur import Fournisseur
from app.models.depense import Depense
from sqlalchemy import func

fournisseurs_bp = Blueprint('fournisseurs', __name__, url_prefix='/fournisseurs')

@fournisseurs_bp.route('/')
@login_required
def index():
    tid = current_user.tenant_id
    fournisseurs = Fournisseur.query.filter_by(tenant_id=tid, actif=True).order_by(Fournisseur.nom).all()
    # Total dépensé par fournisseur
    totaux = {}
    for f in fournisseurs:
        totaux[f.id] = float(db.session.query(func.sum(Depense.montant)).filter_by(
            tenant_id=tid, fournisseur_id=f.id).scalar() or 0)
    return render_template('fournisseurs/index.html', fournisseurs=fournisseurs, totaux=totaux)

@fournisseurs_bp.route('/nouveau', methods=['GET','POST'])
@login_required
def nouveau():
    if request.method == 'POST':
        f = Fournisseur(
            tenant_id=current_user.tenant_id,
            nom=request.form['nom'],
            categorie=request.form.get('categorie','divers'),
            telephone=request.form.get('telephone',''),
            email=request.form.get('email',''),
            adresse=request.form.get('adresse',''),
            ninea=request.form.get('ninea',''),
            site_web=request.form.get('site_web',''),
            notes=request.form.get('notes',''),
        )
        db.session.add(f)
        db.session.commit()
        flash('Fournisseur ajouté.')
        return redirect(url_for('fournisseurs.index'))
    return render_template('fournisseurs/nouveau.html')

@fournisseurs_bp.route('/<int:fournisseur_id>')
@login_required
def detail(fournisseur_id):
    f = Fournisseur.query.filter_by(id=fournisseur_id, tenant_id=current_user.tenant_id).first_or_404()
    depenses = Depense.query.filter_by(tenant_id=current_user.tenant_id, fournisseur_id=f.id).order_by(Depense.date_depense.desc()).all()
    total = sum(float(d.montant) for d in depenses)
    return render_template('fournisseurs/detail.html', f=f, depenses=depenses, total=total)

@fournisseurs_bp.route('/<int:fournisseur_id>/modifier', methods=['GET','POST'])
@login_required
def modifier(fournisseur_id):
    f = Fournisseur.query.filter_by(id=fournisseur_id, tenant_id=current_user.tenant_id).first_or_404()
    if request.method == 'POST':
        f.nom       = request.form['nom']
        f.categorie = request.form.get('categorie', 'divers')
        f.telephone = request.form.get('telephone','')
        f.email     = request.form.get('email','')
        f.adresse   = request.form.get('adresse','')
        f.ninea     = request.form.get('ninea','')
        f.site_web  = request.form.get('site_web','')
        f.notes     = request.form.get('notes','')
        db.session.commit()
        flash('Fournisseur mis à jour.')
        return redirect(url_for('fournisseurs.detail', fournisseur_id=f.id))
    return render_template('fournisseurs/modifier.html', f=f)

@fournisseurs_bp.route('/<int:fournisseur_id>/supprimer', methods=['POST'])
@login_required
def supprimer(fournisseur_id):
    f = Fournisseur.query.filter_by(id=fournisseur_id, tenant_id=current_user.tenant_id).first_or_404()
    f.actif = False
    db.session.commit()
    flash('Fournisseur supprimé.')
    return redirect(url_for('fournisseurs.index'))
