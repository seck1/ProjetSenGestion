from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as pdfcanvas
import io, os, qrcode

NAVY   = colors.HexColor('#1A3A6B')
GOLD   = colors.HexColor('#B8860B')
GREY   = colors.HexColor('#6B7280')
LIGHT  = colors.HexColor('#F4F6FB')
WHITE  = colors.white
BLACK  = colors.HexColor('#111827')
GREEN  = colors.HexColor('#145A32')
NAVY_DARK = colors.HexColor('#122B52')

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# Header band height drawn via canvas
HEADER_H = 28 * mm
# QR footer height
QR_FOOTER_H = 28 * mm

_MOIS_FR = ['janvier','février','mars','avril','mai','juin',
            'juillet','août','septembre','octobre','novembre','décembre']

def _date_fr(d, heure=False):
    if d is None:
        return ''
    s = f"{d.day:02d} {_MOIS_FR[d.month-1]} {d.year}"
    if heure:
        s += f" à {d.strftime('%H:%M')}"
    return s


def _logo_image(logo_path, max_w=38*mm, max_h=20*mm):
    from PIL import Image as PILImage
    with PILImage.open(logo_path) as pil_img:
        w_px, h_px = pil_img.size
    ratio = w_px / h_px
    if ratio > (max_w / max_h):
        w, h = max_w, max_w / ratio
    else:
        w, h = max_h * ratio, max_h
    return Image(logo_path, width=w, height=h)


def _style(name='Normal', **kwargs):
    base = getSampleStyleSheet()[name]
    return ParagraphStyle(name + str(id(kwargs)), parent=base, **kwargs)


def _draw_header_band(c, tenant):
    """Dessine le bandeau navy en haut de page avec logo + infos entreprise."""
    from reportlab.lib.utils import ImageReader

    bx = 0
    by = PAGE_H - HEADER_H
    bw = PAGE_W
    bh = HEADER_H

    # Fond navy pleine largeur
    c.setFillColor(NAVY_DARK)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)

    # Liseré gold en bas du bandeau
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(bx, by, bx + bw, by)

    # Logo (si disponible)
    logo_drawn_w = 0
    if tenant.logo_url:
        try:
            from flask import current_app
            logo_path = os.path.join(current_app.root_path, 'static', tenant.logo_url)
            if os.path.exists(logo_path):
                from PIL import Image as PILImage
                with PILImage.open(logo_path) as pil_img:
                    w_px, h_px = pil_img.size
                ratio = w_px / h_px
                max_h = bh - 8 * mm
                max_w = 36 * mm
                if ratio > (max_w / max_h):
                    lw, lh = max_w, max_w / ratio
                else:
                    lw, lh = max_h * ratio, max_h
                lx = bx + 8 * mm
                ly = by + (bh - lh) / 2
                c.drawImage(ImageReader(logo_path), lx, ly, width=lw, height=lh,
                            preserveAspectRatio=True, mask='auto')
                logo_drawn_w = lw + 5 * mm
        except Exception:
            pass

    # Nom entreprise
    text_x = bx + 8 * mm + logo_drawn_w
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 13)
    c.drawString(text_x, by + bh - 11 * mm, tenant.nom or '')

    # Sous-infos entreprise (NINEA, tel, email)
    sub_parts = []
    if tenant.ninea:     sub_parts.append(f'NINEA : {tenant.ninea}')
    if tenant.telephone: sub_parts.append(tenant.telephone)
    if tenant.email:     sub_parts.append(tenant.email)
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#B8C8E0'))
    c.drawString(text_x, by + bh - 17 * mm, '  ·  '.join(sub_parts))

    if tenant.adresse:
        c.setFont('Helvetica', 7.5)
        c.setFillColor(colors.HexColor('#8FA8CC'))
        c.drawString(text_x, by + bh - 22 * mm, tenant.adresse)


def _draw_doc_badge(c, label, numero, date_str, extra_label='', extra_val=''):
    """Dessine le badge document (DEVIS / FACTURE) sous le bandeau navy."""
    # Zone: juste sous le bandeau
    bx = MARGIN
    by = PAGE_H - HEADER_H - 20 * mm
    bw = CONTENT_W

    # Badge coloré à gauche
    badge_w = 28 * mm
    badge_h = 14 * mm
    c.setFillColor(GOLD)
    c.roundRect(bx, by, badge_w, badge_h, 3, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 14)
    # Centre du badge
    c.drawCentredString(bx + badge_w / 2, by + 4 * mm, label)

    # Numéro à droite du badge
    nx = bx + badge_w + 6 * mm
    c.setFillColor(NAVY)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(nx, by + 5 * mm, numero)

    # Métadonnées à droite
    meta_parts = [f'Date : {date_str}']
    if extra_val:
        meta_parts.append(f'{extra_label} : {extra_val}')
    c.setFont('Helvetica', 8)
    c.setFillColor(GREY)
    c.drawRightString(bx + bw, by + 5 * mm, '    ·    '.join(meta_parts))


def _draw_qr_footer(c, lien, numero):
    x = MARGIN
    y = 8 * mm
    w = CONTENT_W
    h = QR_FOOTER_H

    c.setFillColor(NAVY_DARK)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=0)

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(x, y + h, x + w, y + h)

    qr_obj = qrcode.QRCode(version=1, box_size=5, border=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr_obj.add_data(lien)
    qr_obj.make(fit=True)
    qr_pil = qr_obj.make_image(fill_color='white', back_color='#122B52')
    qr_buf = io.BytesIO()
    qr_pil.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    from reportlab.lib.utils import ImageReader
    qr_size = h - 6 * mm
    c.drawImage(ImageReader(qr_buf), x + 4 * mm, y + 3 * mm, width=qr_size, height=qr_size,
                preserveAspectRatio=True, mask='auto')

    text_x = x + qr_size + 10 * mm
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(text_x, y + h - 9 * mm, 'Signez ce devis en ligne')
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#B8C8E0'))
    c.drawString(text_x, y + h - 15 * mm, 'Scannez le QR code avec votre smartphone')
    c.drawString(text_x, y + h - 20 * mm, 'pour consulter et signer ce devis en toute sécurité.')
    c.setFont('Helvetica', 7)
    c.setFillColor(GOLD)
    short_url = lien if len(lien) < 70 else lien[:67] + '...'
    c.drawString(text_x, y + 5 * mm, short_url)
    c.setFont('Helvetica', 7.5)
    c.setFillColor(colors.HexColor('#8FA8CC'))
    c.drawRightString(x + w - 4 * mm, y + 4 * mm, f'Réf. {numero}')


def _draw_signature_footer(c, devis):
    x = MARGIN
    y = 8 * mm
    w = CONTENT_W
    h = QR_FOOTER_H

    c.setFillColor(colors.HexColor('#D6EAE0'))
    c.roundRect(x, y, w, h, 5, fill=1, stroke=0)
    c.setStrokeColor(GREEN)
    c.setLineWidth(1.5)
    c.line(x, y + h, x + w, y + h)

    c.setFillColor(GREEN)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(x + 6 * mm, y + h - 9 * mm,
                 f'Signe electroniquement par : {devis.signature_nom}')
    c.setFont('Helvetica', 9)
    date_str = _date_fr(devis.signe_at, heure=True) if devis.signe_at else ''
    ip_str   = f'  ·  IP : {devis.signature_ip}' if devis.signature_ip else ''
    c.drawString(x + 6 * mm, y + h - 17 * mm, f'Le {date_str}{ip_str}')
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#145A32'))
    c.drawString(x + 6 * mm, y + 5 * mm,
                 'Cette signature electronique a valeur legale de signature manuscrite.')


def _draw_legal_line(c, has_footer):
    """Ligne légale fine au bas de la zone contenu."""
    footer_offset = (QR_FOOTER_H + 12 * mm) if has_footer else 10 * mm
    text_y = footer_offset
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.HexColor('#9CA3AF'))
    c.setStrokeColor(colors.HexColor('#E5E7EB'))
    c.setLineWidth(0.5)
    c.line(MARGIN, text_y + 5 * mm, PAGE_W - MARGIN, text_y + 5 * mm)
    c.drawString(MARGIN, text_y + 1.5 * mm,
                 "Ce document est valable 30 jours. SenGestion - Gestion intelligente pour les PME senegalaises.")


def generer_devis_pdf(devis, tenant, output_path=None) -> bytes:

    lien_signature = None
    if devis.token_signature and not devis.signature_nom:
        try:
            from flask import url_for
            lien_signature = url_for('devis.page_signature',
                                     token=devis.token_signature, _external=True)
        except RuntimeError:
            lien_signature = f'http://localhost:5001/devis/signer/{devis.token_signature}'

    has_footer = bool(lien_signature or devis.signature_nom)

    def on_page(c, doc):
        c.saveState()
        _draw_header_band(c, tenant)
        date_str  = _date_fr(devis.created_at)
        valid_str = _date_fr(devis.valide_jusqu) if devis.valide_jusqu else ''
        _draw_doc_badge(c, 'DEVIS', devis.numero, date_str,
                        "Valide jusqu'au", valid_str)
        _draw_legal_line(c, has_footer)
        if devis.signature_nom:
            _draw_signature_footer(c, devis)
        elif lien_signature:
            _draw_qr_footer(c, lien_signature, devis.numero)

        # Cachet ancré juste au-dessus du footer (ne dépend pas du flux)
        if tenant.cachet_url:
            try:
                from flask import current_app
                from reportlab.lib.utils import ImageReader
                cachet_path = os.path.join(current_app.root_path, 'static', tenant.cachet_url)
                if os.path.exists(cachet_path):
                    footer_top = (QR_FOOTER_H + 18 * mm) if has_footer else 14 * mm
                    cw, ch = 55 * mm, 28 * mm
                    cx = MARGIN + CONTENT_W - cw
                    cy = footer_top
                    c.drawImage(ImageReader(cachet_path), cx, cy, width=cw, height=ch,
                                preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        c.restoreState()

    # Top margin: bandeau (HEADER_H) + badge zone (20mm) + gap
    top_margin    = HEADER_H + 22 * mm
    bottom_margin = (QR_FOOTER_H + 16 * mm) if has_footer else 20 * mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=top_margin, bottomMargin=bottom_margin
    )

    story = []

    # ── Adresses : Émetteur (gauche) | Client (droite) ───────────────────────
    client = devis.client

    em_lines = ['<b>Émetteur</b>']
    em_lines.append(f'<font color="#1A3A6B"><b>{tenant.nom}</b></font>')
    if tenant.ninea:     em_lines.append(f'NINEA : {tenant.ninea}')
    if tenant.adresse:   em_lines.append(tenant.adresse)
    if tenant.telephone: em_lines.append(tenant.telephone)
    if tenant.email:     em_lines.append(tenant.email)

    cl_lines = ['<b>Destinataire</b>']
    cl_lines.append(f'<font color="#1A3A6B"><b>{client.nom_complet}</b></font>')
    if client.entreprise: cl_lines.append(client.entreprise)
    if client.adresse:    cl_lines.append(client.adresse)
    parts = list(filter(None, [client.telephone, client.email]))
    if parts: cl_lines.append('  ·  '.join(parts))

    addr_style = _style(fontSize=9, leading=14, textColor=BLACK)
    label_style = _style(fontSize=7.5, textColor=GREY, spaceAfter=2)

    em_para = Paragraph('<br/>'.join(em_lines), addr_style)
    cl_para = Paragraph('<br/>'.join(cl_lines), addr_style)

    half = (CONTENT_W - 6 * mm) / 2

    def addr_box(para, border_color):
        tbl = Table([[para]], colWidths=[half])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(0,0), LIGHT),
            ('TOPPADDING',    (0,0),(0,0), 9),
            ('BOTTOMPADDING', (0,0),(0,0), 9),
            ('LEFTPADDING',   (0,0),(0,0), 10),
            ('RIGHTPADDING',  (0,0),(0,0), 8),
            ('LINEBEFORE',    (0,0),(0,0), 3, border_color),
            ('LINEBELOW',     (0,0),(0,0), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        return tbl

    addr_row = Table([[addr_box(em_para, NAVY), addr_box(cl_para, GOLD)]],
                     colWidths=[half, half], spaceBefore=0)
    addr_row.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('ALIGN',        (0,0),(-1,-1), 'LEFT'),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('INNERGRID',    (0,0),(-1,-1), 0, WHITE),
        ('BOX',          (0,0),(-1,-1), 0, WHITE),
        ('COLPADDING',   (0,0),(-1,-1), 3),
    ]))
    story.append(addr_row)
    story.append(Spacer(1, 12))

    # ── Objet ────────────────────────────────────────────────────────────────
    if devis.objet:
        story.append(Paragraph(
            f'<font size="9.5" color="#374151"><b>Objet :</b> {devis.objet}</font>',
            _style(fontSize=9.5, textColor=BLACK)
        ))
        story.append(Spacer(1, 10))

    # ── Tableau prestations ──────────────────────────────────────────────────
    def th(txt, align=TA_LEFT):
        return Paragraph(f"<font color='white' size='8.5'><b>{txt}</b></font>",
                         _style(fontSize=8.5, alignment=align))

    def td(txt, align=TA_LEFT, bold=False):
        tag = '<b>' if bold else ''
        etag = '</b>' if bold else ''
        return Paragraph(f"<font size='9'>{tag}{txt}{etag}</font>",
                         _style(fontSize=9, alignment=align))

    col_w = [90*mm, 18*mm, 36*mm, 36*mm]
    rows = [[th('Description'), th('Qté', TA_RIGHT),
             th('Prix unit. (FCFA)', TA_RIGHT), th('Total (FCFA)', TA_RIGHT)]]

    for i, ligne in enumerate(devis.lignes):
        qte = float(ligne.quantite)
        qte_str = f"{qte:.0f}" if qte == int(qte) else f"{qte:.2f}"
        rows.append([
            td(ligne.description),
            td(qte_str, TA_RIGHT),
            td(f"{float(ligne.prix_unitaire):,.0f}".replace(',', ' '), TA_RIGHT),
            td(f"{float(ligne.total):,.0f}".replace(',', ' '), TA_RIGHT, bold=True),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    n = len(rows)
    tbl.setStyle(TableStyle([
        # En-tête navy
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LIGHT]),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#DDE3ED')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW',     (0,0), (-1,0),  1.5, GOLD),
        # Dernière ligne (total) légèrement différenciée
        ('LINEABOVE',     (0,n-1),(-1,n-1), 0.8, colors.HexColor('#DDE3ED')),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 14))

    # ── Totaux dans un encadré aligné à droite ───────────────────────────────
    tva_pct = float(devis.tva_pct)
    col_label = 88 * mm
    col_val   = 42 * mm

    def tr(label, val, bold=False, separator=False):
        fs = 10.5 if bold else 9
        color_hex = '#1A3A6B' if bold else '#6B7280'
        lp = Paragraph(
            f"<font size='{fs}' color='{color_hex}'>{'<b>' if bold else ''}{label}{'</b>' if bold else ''}</font>",
            _style(fontSize=fs, alignment=TA_RIGHT)
        )
        rp = Paragraph(
            f"<font size='{fs}' color='{color_hex}'>{'<b>' if bold else ''}{val}{'</b>' if bold else ''}</font>",
            _style(fontSize=fs, alignment=TA_RIGHT)
        )
        return [lp, rp]

    totaux_data = [
        tr('Sous-total HT',
           f"{float(devis.total_ht):,.0f} FCFA".replace(',', ' ')),
        tr(f'TVA ({tva_pct:.0f} %)',
           f"{float(devis.total_tva):,.0f} FCFA".replace(',', ' ')),
        tr('Total TTC',
           f"{float(devis.total_ttc):,.0f} FCFA".replace(',', ' '), bold=True),
    ]
    totaux_tbl = Table(totaux_data, colWidths=[col_label, col_val])
    totaux_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('LINEABOVE',     (0,2), (-1,2),  1.5, GOLD),
        ('BACKGROUND',    (0,2), (-1,2),  colors.HexColor('#EEF2FA')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(totaux_tbl)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    pdf_bytes = buffer.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def generer_facture_pdf(facture, tenant, output_path=None) -> bytes:
    """Génère le PDF d'une facture — même charte que le devis."""

    def on_page(c, doc):
        c.saveState()
        _draw_header_band(c, tenant)
        date_str     = _date_fr(facture.created_at)
        echeance_str = _date_fr(facture.echeance) if facture.echeance else ''
        _draw_doc_badge(c, 'FACTURE', facture.numero, date_str,
                        'Échéance', echeance_str)
        _draw_legal_line(c, False)
        c.restoreState()

    top_margin    = HEADER_H + 22 * mm
    bottom_margin = 20 * mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=top_margin, bottomMargin=bottom_margin
    )

    story = []

    # ── Adresses ─────────────────────────────────────────────────────────────
    client = facture.client

    em_lines = ['<b>Émetteur</b>',
                f'<font color="#1A3A6B"><b>{tenant.nom}</b></font>']
    if tenant.ninea:     em_lines.append(f'NINEA : {tenant.ninea}')
    if tenant.adresse:   em_lines.append(tenant.adresse)
    if tenant.telephone: em_lines.append(tenant.telephone)
    if tenant.email:     em_lines.append(tenant.email)

    cl_lines = ['<b>Destinataire</b>']
    if client:
        cl_lines.append(f'<font color="#1A3A6B"><b>{client.nom_complet}</b></font>')
        if client.entreprise: cl_lines.append(client.entreprise)
        if client.adresse:    cl_lines.append(client.adresse)
        parts = list(filter(None, [client.telephone, client.email]))
        if parts: cl_lines.append('  ·  '.join(parts))

    addr_style = _style(fontSize=9, leading=14, textColor=BLACK)
    half = (CONTENT_W - 6 * mm) / 2

    def addr_box(para, border_color):
        tbl = Table([[para]], colWidths=[half])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(0,0), LIGHT),
            ('TOPPADDING',    (0,0),(0,0), 9),
            ('BOTTOMPADDING', (0,0),(0,0), 9),
            ('LEFTPADDING',   (0,0),(0,0), 10),
            ('RIGHTPADDING',  (0,0),(0,0), 8),
            ('LINEBEFORE',    (0,0),(0,0), 3, border_color),
            ('LINEBELOW',     (0,0),(0,0), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        return tbl

    em_para = Paragraph('<br/>'.join(em_lines), addr_style)
    cl_para = Paragraph('<br/>'.join(cl_lines), addr_style)

    addr_row = Table([[addr_box(em_para, NAVY), addr_box(cl_para, GOLD)]],
                     colWidths=[half, half])
    addr_row.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('INNERGRID',    (0,0),(-1,-1), 0, WHITE),
        ('BOX',          (0,0),(-1,-1), 0, WHITE),
        ('COLPADDING',   (0,0),(-1,-1), 3),
    ]))
    story.append(addr_row)
    story.append(Spacer(1, 12))

    if facture.objet:
        story.append(Paragraph(
            f'<font size="9.5" color="#374151"><b>Objet :</b> {facture.objet}</font>',
            _style(fontSize=9.5, textColor=BLACK)
        ))
        story.append(Spacer(1, 10))

    # ── Tableau ───────────────────────────────────────────────────────────────
    def th(txt, align=TA_LEFT):
        return Paragraph(f"<font color='white' size='8.5'><b>{txt}</b></font>",
                         _style(fontSize=8.5, alignment=align))

    def td(txt, align=TA_LEFT, bold=False):
        tag = '<b>' if bold else ''
        etag = '</b>' if bold else ''
        return Paragraph(f"<font size='9'>{tag}{txt}{etag}</font>",
                         _style(fontSize=9, alignment=align))

    col_w = [90*mm, 18*mm, 36*mm, 36*mm]
    rows = [[th('Description'), th('Qté', TA_RIGHT),
             th('Prix unit. (FCFA)', TA_RIGHT), th('Total (FCFA)', TA_RIGHT)]]

    for ligne in facture.lignes:
        qte = float(ligne.quantite)
        qte_str = f"{qte:.0f}" if qte == int(qte) else f"{qte:.2f}"
        rows.append([
            td(ligne.description),
            td(qte_str, TA_RIGHT),
            td(f"{float(ligne.prix_unitaire):,.0f}".replace(',', ' '), TA_RIGHT),
            td(f"{float(ligne.total):,.0f}".replace(',', ' '), TA_RIGHT, bold=True),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    n = len(rows)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LIGHT]),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#DDE3ED')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW',     (0,0), (-1,0),  1.5, GOLD),
        ('LINEABOVE',     (0,n-1),(-1,n-1), 0.8, colors.HexColor('#DDE3ED')),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 14))

    # ── Totaux ────────────────────────────────────────────────────────────────
    tva_pct = float(facture.tva_pct)

    def tr(label, val, bold=False):
        fs = 10.5 if bold else 9
        color_hex = '#1A3A6B' if bold else '#6B7280'
        lp = Paragraph(
            f"<font size='{fs}' color='{color_hex}'>{'<b>' if bold else ''}{label}{'</b>' if bold else ''}</font>",
            _style(fontSize=fs, alignment=TA_RIGHT)
        )
        rp = Paragraph(
            f"<font size='{fs}' color='{color_hex}'>{'<b>' if bold else ''}{val}{'</b>' if bold else ''}</font>",
            _style(fontSize=fs, alignment=TA_RIGHT)
        )
        return [lp, rp]

    totaux_data = [
        tr('Sous-total HT', f"{float(facture.total_ht):,.0f} FCFA".replace(',', ' ')),
        tr(f'TVA ({tva_pct:.0f} %)', f"{float(facture.total_tva):,.0f} FCFA".replace(',', ' ')),
        tr('Total TTC', f"{float(facture.total_ttc):,.0f} FCFA".replace(',', ' '), bold=True),
    ]
    totaux_tbl = Table(totaux_data, colWidths=[88*mm, 42*mm])
    totaux_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('LINEABOVE',     (0,2), (-1,2),  1.5, GOLD),
        ('BACKGROUND',    (0,2), (-1,2),  colors.HexColor('#EEF2FA')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(totaux_tbl)

    # ── Cachet ────────────────────────────────────────────────────────────────
    if tenant.cachet_url:
        try:
            from flask import current_app
            cachet_path = os.path.join(current_app.root_path, 'static', tenant.cachet_url)
            if os.path.exists(cachet_path):
                story.append(Spacer(1, 14))
                cachet_img = Image(cachet_path, width=52*mm, height=26*mm)
                cachet_img.hAlign = 'RIGHT'
                story.append(cachet_img)
        except Exception:
            pass

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    pdf_bytes = buffer.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
