from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.models.depense import Depense
from app import db
from datetime import date
import base64, io, os, uuid
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

depenses_bp = Blueprint('depenses', __name__, url_prefix='/depenses')

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'justificatifs')


def _save_image(img: Image.Image) -> str:
    """Sauvegarde une image PIL en JPEG, retourne le nom du fichier."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    img.save(os.path.join(UPLOAD_DIR, filename), format='JPEG', quality=92)
    return filename


def _open_image(f) -> Image.Image:
    """Ouvre un fichier image ou PDF (première page) en PIL Image RGB."""
    data = f.read() if hasattr(f, 'read') else open(f, 'rb').read()
    # Détection PDF par magic bytes
    if data[:4] == b'%PDF':
        import fitz  # PyMuPDF
        doc  = fitz.open(stream=data, filetype='pdf')
        page = doc[0]
        mat  = fitz.Matrix(2.0, 2.0)  # 2x = ~144 dpi
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    return Image.open(io.BytesIO(data)).convert('RGB')


@depenses_bp.route('/')
@login_required
def index():
    depenses = Depense.query.filter_by(tenant_id=current_user.tenant_id)\
                            .order_by(Depense.date_depense.desc()).all()
    total = sum(float(d.montant) for d in depenses)
    return render_template('depenses/index.html', depenses=depenses, total=total, today=date.today())


@depenses_bp.route('/ajouter', methods=['POST'])
@login_required
def ajouter():
    # Récupère le justificatif s'il a été envoyé avec le formulaire (champ caché base64)
    justificatif_url = None
    justificatif_b64 = request.form.get('justificatif_b64', '').strip()
    if justificatif_b64:
        try:
            raw = justificatif_b64.split(',', 1)[1] if ',' in justificatif_b64 else justificatif_b64
            img = Image.open(io.BytesIO(base64.b64decode(raw))).convert('RGB')
            justificatif_url = _save_image(img)
        except Exception:
            pass

    depense = Depense(
        tenant_id       = current_user.tenant_id,
        user_id         = current_user.id,
        libelle         = request.form.get('libelle', '').strip(),
        categorie       = request.form.get('categorie', 'divers'),
        montant         = float(request.form.get('montant', 0) or 0),
        source          = request.form.get('source', 'manuel'),
        date_depense    = date.fromisoformat(request.form.get('date_depense')) if request.form.get('date_depense') else date.today(),
        notes           = request.form.get('notes', '').strip(),
        justificatif_url= justificatif_url,
    )
    db.session.add(depense)
    db.session.commit()
    flash('Charge enregistrée.', 'success')
    return redirect(url_for('depenses.index'))


@depenses_bp.route('/scan/analyser', methods=['POST'])
@login_required
def scan_analyser():
    """Analyse une facture via Claude Vision. Sauvegarde l'image et retourne JSON + nom fichier."""
    try:
        if 'file' in request.files:
            img = _open_image(request.files['file'])
        else:
            payload = request.get_json(silent=True) or {}
            raw = payload.get('image', '')
            if not raw:
                return jsonify({'success': False, 'error': 'Aucune image fournie'}), 400
            if ',' in raw:
                raw = raw.split(',', 1)[1]
            img = Image.open(io.BytesIO(base64.b64decode(raw))).convert('RGB')

        # Sauvegarder le justificatif
        filename = _save_image(img)

        # Encoder pour Claude
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=92)
        image_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

        from app.services.claude_service import analyser_facture
        resultat = analyser_facture(image_b64)
        resultat['justificatif_filename'] = filename
        return jsonify(resultat)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@depenses_bp.route('/<int:depense_id>/pdf')
@login_required
def telecharger_pdf(depense_id):
    """Génère et télécharge un PDF justificatif de la charge."""
    d = Depense.query.filter_by(id=depense_id, tenant_id=current_user.tenant_id).first_or_404()
    tenant = current_user.tenant

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    navy   = colors.HexColor('#1A3A6B')
    gold   = colors.HexColor('#B8860B')
    light  = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle('title', parent=styles['Normal'],
                                  fontSize=20, fontName='Helvetica-Bold',
                                  textColor=navy, spaceAfter=4)
    sub_style   = ParagraphStyle('sub', parent=styles['Normal'],
                                  fontSize=10, textColor=colors.HexColor('#64748B'))
    label_style = ParagraphStyle('label', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.HexColor('#94A3B8'),
                                  fontName='Helvetica-Bold', spaceAfter=2)
    value_style = ParagraphStyle('value', parent=styles['Normal'],
                                  fontSize=11, textColor=colors.HexColor('#1E293B'))

    story = []

    # En-tête
    story.append(Paragraph(tenant.nom, title_style))
    if tenant.ninea:
        story.append(Paragraph(f"NINEA : {tenant.ninea}", sub_style))
    story.append(Spacer(1, 0.5*cm))

    # Titre document
    story.append(Paragraph("JUSTIFICATIF DE CHARGE", ParagraphStyle('h',
        parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold',
        textColor=gold, spaceBefore=6, spaceAfter=12)))

    # Tableau infos
    cat_labels = {
        'transport':'Transport','repas':'Repas','fournitures':'Fournitures',
        'communication':'Communication','loyer':'Loyer','salaires':'Salaires',
        'hebergement':'Hébergement','divers':'Divers',
    }
    rows = [
        ['Libellé',     d.libelle],
        ['Fournisseur', d.notes or ''],
        ['Montant TTC', f"{float(d.montant):,.0f} FCFA"],
        ['Catégorie',   cat_labels.get(d.categorie, d.categorie)],
        ['Date',        d.date_depense.strftime('%d/%m/%Y') if d.date_depense else ''],
        ['Source',      'Scan IA' if d.source == 'scan_recu' else 'Manuel'],
    ]
    tbl = Table([[Paragraph(r[0], label_style), Paragraph(str(r[1]), value_style)] for r in rows],
                colWidths=[4*cm, 12*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, light]),
        ('GRID',  (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.6*cm))

    # Image justificatif
    if d.justificatif_url:
        img_path = os.path.join(UPLOAD_DIR, d.justificatif_url)
        if os.path.exists(img_path):
            story.append(Paragraph("Justificatif original :", ParagraphStyle('jlabel',
                parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold',
                textColor=colors.HexColor('#94A3B8'), spaceAfter=6)))
            rl_img = RLImage(img_path, width=14*cm, height=10*cm, kind='proportional')
            story.append(rl_img)

    # Pied de page
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"Document généré le {date.today().strftime('%d/%m/%Y')} par SenGestion",
        ParagraphStyle('footer', parent=styles['Normal'],
                       fontSize=8, textColor=colors.HexColor('#CBD5E1'))
    ))

    doc.build(story)
    buf.seek(0)
    filename = f"charge_{d.id}_{d.date_depense or date.today()}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


@depenses_bp.route('/<int:depense_id>/supprimer', methods=['POST'])
@login_required
def supprimer(depense_id):
    d = Depense.query.filter_by(id=depense_id, tenant_id=current_user.tenant_id).first_or_404()
    # Supprimer le justificatif si présent
    if d.justificatif_url:
        path = os.path.join(UPLOAD_DIR, d.justificatif_url)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(d)
    db.session.commit()
    flash('Charge supprimée.', 'success')
    return redirect(url_for('depenses.index'))
