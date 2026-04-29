"""PDF rapor uretimi - ReportLab"""
import os
import io
import tempfile
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from db import BASE_DIR

_PDF_PREVIEW_DIR: Path | None = None
PDF_TOP_MARGIN_MM = 42

# Font kaydi (Turkce karakter destegi - Windows + Linux)
_font_registered = False
def _register_fonts():
    global _font_registered
    if _font_registered:
        return

    # Font arama yollari: Windows > Linux > fallback
    font_candidates = [
        # Windows
        (os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'),
         os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arialbd.ttf')),
        # Linux - DejaVu (en yaygin, Turkce destekli)
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        # Linux - Liberation Sans (Arial uyumlu)
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
        # Linux - FreeSans
        ('/usr/share/fonts/truetype/freefont/FreeSans.ttf',
         '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
    ]

    for regular, bold in font_candidates:
        if os.path.exists(regular):
            try:
                pdfmetrics.registerFont(TTFont('ArialTR', regular))
                bold_path = bold if os.path.exists(bold) else regular
                pdfmetrics.registerFont(TTFont('ArialTRB', bold_path))
                _font_registered = True
                return
            except Exception:
                continue

    # Hicbir font bulunamazsa ReportLab varsayilan Helvetica kullan
    _font_registered = True


def _styles():
    _register_fonts()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('TRNormal', fontName='ArialTR', fontSize=9, leading=12))
    styles.add(ParagraphStyle('TRTitle', fontName='ArialTRB', fontSize=14, leading=18, spaceAfter=10))
    styles.add(ParagraphStyle('TRSubtitle', fontName='ArialTRB', fontSize=10, leading=14, spaceAfter=6))
    styles.add(ParagraphStyle('TRSmall', fontName='ArialTR', fontSize=8, leading=10))
    return styles


def _fmt(val, blank_zero=False):
    if val is None:
        val = 0
    if blank_zero and abs(float(val)) < 1e-12:
        return ''
    s = f"{abs(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"-{s}" if val < 0 else s


def _pretty_text(value):
    text = str(value or '')
    key = text.strip().upper()
    mapping = {
        'ALIS': 'Alış',
        'SATIS': 'Satış',
        'ODEME': 'Ödeme',
        'TAHSILAT': 'Tahsilat',
        'GELIR': 'Gelir',
        'GIDER': 'Gider',
        'ALACAK': 'Alacak',
        'BORC': 'Borç',
        'BORÇ': 'Borç',
    }
    return mapping.get(key, text)


def get_pdf_preview_dir() -> Path:
    """PDF onizleme dosyalarinin yazilip static olarak servis edilecegi klasor."""
    global _PDF_PREVIEW_DIR
    if _PDF_PREVIEW_DIR is not None:
        return _PDF_PREVIEW_DIR

    candidates = [
        Path(BASE_DIR) / 'output' / 'pdf',
        Path.cwd() / 'output' / 'pdf',
        Path(tempfile.gettempdir()) / 'alse_muhasebe' / 'pdf_preview',
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / '.write_test'
            test_file.write_text('ok', encoding='utf-8')
            test_file.unlink(missing_ok=True)
            _PDF_PREVIEW_DIR = p
            return _PDF_PREVIEW_DIR
        except Exception:
            continue
    raise RuntimeError('PDF onizleme klasoru olusturulamadi')


def _header_footer(canvas, doc, title, show_title=True):
    _register_fonts()  # Font'larin kayitli oldugundan emin ol
    from services.settings_service import get_company_settings
    try:
        meta = get_company_settings()
    except Exception:
        meta = {}
    firma_adi = meta.get('firma_adi') or 'ALSE Plastik Hammadde'
    tel = meta.get('telefon') or ''
    mail = meta.get('email') or ''
    adres = meta.get('adres') or ''
    vkn = meta.get('vkn_tckn') or ''
    vergi = meta.get('vergi_dairesi') or ''
    logo_path = meta.get('logo_path_resolved') or meta.get('logo_path') or ''

    canvas.saveState()
    has_logo = bool(logo_path and os.path.exists(logo_path))
    if has_logo:
        try:
            canvas.drawImage(
                logo_path,
                15 * mm,
                A4[1] - 27 * mm,
                width=34 * mm,
                height=16 * mm,
                preserveAspectRatio=True,
                mask='auto',
            )
        except Exception:
            pass
    # Sol ust: firma adi (her zaman)
    center_x = A4[0] / 2
    logo_end_x = (52 * mm) if has_logo else (15 * mm)
    canvas.setFont('ArialTRB', 11)
    canvas.drawString(logo_end_x, A4[1] - 15 * mm, firma_adi[:50])
    # Baslik ortada
    if show_title:
        canvas.setFont('ArialTR', 8)
        canvas.drawCentredString(center_x, A4[1] - 21 * mm, title[:90])

    # Sag ust: tarih ve telefon
    right_lines = [datetime.now().strftime('%d.%m.%Y')]
    if tel:
        right_lines.append(f'Tel: {tel}')
    if mail:
        right_lines.append(f'Mail: {mail}')
    y = A4[1] - 18 * mm
    canvas.setFont('ArialTR', 7)
    for line in right_lines[:3]:
        canvas.drawRightString(A4[0] - 20*mm, y, line)
        y -= 4.2 * mm

    # --- FOOTER: Adres + VD + VKN ---
    footer_y = 12 * mm
    canvas.setFont('ArialTR', 7)

    # VD ve VKN ayni satirda (sigarsa)
    vd_vkn = ' | '.join([x for x in [f'VD: {vergi}' if vergi else '', f'VKN/TCKN: {vkn}' if vkn else ''] if x])
    if vd_vkn:
        canvas.drawCentredString(A4[0] / 2, footer_y, vd_vkn)
        footer_y -= 3.5 * mm

    if adres:
        canvas.drawCentredString(A4[0] / 2, footer_y, adres[:90])
        footer_y -= 3.5 * mm

    # Sayfa numarasi sag alt
    canvas.drawRightString(A4[0] - 20*mm, 5*mm, f'Sayfa {doc.page}')
    canvas.restoreState()


def generate_cari_ekstre_pdf(firma_ad, ekstre_data, donem_label=None, devir=None, firma=None):
    """Cari ekstre PDF.
    ekstre_data: list (eski API) VEYA dict (yeni API: {donem_label, devir, satirlar, ...})
    donem_label / devir: opsiyonel manuel parametreler (geriye uyumluluk).
    firma: opsiyonel firma dict ({kod, ad, vkn_tckn, vergi_dairesi, tel, adres}).
        Verilirse ve WeasyPrint kuruluysa modern v3 PDF tasarimi uygulanir.

    Onceki donem icin reportlab fallback otomatik calisir.
    """
    # V3 modern PDF (WeasyPrint) tercihen denenir
    try:
        from services import pdf_v3_service
        if pdf_v3_service.WEASYPRINT_AVAILABLE and isinstance(ekstre_data, dict):
            from services.settings_service import get_company_settings
            try:
                sirket = get_company_settings()
            except Exception:
                sirket = {'firma_adi': firma_ad}
            firma_dict = firma or {'ad': firma_ad}
            return pdf_v3_service.render_cari_ekstre(firma_dict, ekstre_data, sirket)
    except Exception:
        # WeasyPrint render basarisiz - reportlab fallback'e dus
        pass

    # Yeni API: dict olarak geldi
    if isinstance(ekstre_data, dict):
        donem_label = donem_label or ekstre_data.get('donem_label')
        devir = devir if devir is not None else ekstre_data.get('devir', 0)
        ekstre_data = ekstre_data.get('satirlar', [])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=35 * mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = _styles()
    elements = []

    # Cari ekstre basligi tabloya yakin dursun.
    elements.append(Spacer(1, 2 * mm))
    title_style = ParagraphStyle(
        'TRTitleCenter',
        parent=styles['TRTitle'],
        fontSize=12,
        leading=15,
        alignment=1,
        spaceAfter=0,
    )
    elements.append(Paragraph(f'Cari Ekstre - {firma_ad}', title_style))
    if donem_label:
        donem_style = ParagraphStyle(
            'TRDonem', parent=styles['TRSmall'], fontSize=9, alignment=1, spaceAfter=2,
            textColor=colors.HexColor('#546E7A'),
        )
        elements.append(Paragraph(f'Donem: {donem_label}', donem_style))
    elements.append(Spacer(1, 3 * mm))

    data = [['Tarih', 'Tür', 'Açıklama', 'Borç', 'Alacak', 'Bakiye']]

    # Devir satiri (donem secili modda devir tablonun en ustunde)
    devir_row_idx = None
    if devir is not None and abs(float(devir or 0)) > 0.005:
        d = float(devir)
        devir_row_idx = len(data)
        data.append([
            '',
            'Devir',
            Paragraph('<b>Onceki donem devir bakiyesi</b>', styles['TRSmall']),
            _fmt(abs(d) if d < 0 else 0, blank_zero=True),
            _fmt(d if d > 0 else 0, blank_zero=True),
            _fmt(d, blank_zero=True),
        ])

    for row in ekstre_data:
        tarih = row['tarih'] or ''
        if '-' in tarih:
            p = tarih.split('-')
            tarih = f"{p[2]}.{p[1]}.{p[0]}"
        aciklama = str(row.get('aciklama', '') or '')
        aciklama_l = aciklama.lower()
        if aciklama_l.startswith('alis'):
            tip = 'Alış'
        elif aciklama_l.startswith('satis'):
            tip = 'Satış'
        elif aciklama_l.startswith('tahsilat'):
            tip = 'Tahsilat'
        elif aciklama_l.startswith('odeme'):
            tip = 'Ödeme'
        else:
            tip = ''
        temiz = aciklama
        for pfx in ('Alış:', 'Alis:', 'Satış:', 'Satis:', 'Tahsilat:', 'Ödeme:', 'Odeme:'):
            if temiz.strip().lower().startswith(pfx.lower()):
                temiz = temiz.split(':', 1)[1].strip() if ':' in temiz else temiz
                break
        data.append([
            tarih,
            tip,
            Paragraph(temiz[:56], styles['TRSmall']),
            _fmt(row['borc'], blank_zero=True),
            _fmt(row['alacak'], blank_zero=True),
            _fmt(row['bakiye'], blank_zero=True),
        ])

    col_widths = [20*mm, 16*mm, 59*mm, 24*mm, 24*mm, 24*mm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.hAlign = 'CENTER'
    style_cmds = [
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    if devir_row_idx is not None:
        # Devir satiri vurgulu (acik mavi arkaplan + bold)
        style_cmds.append(('BACKGROUND', (0, devir_row_idx), (-1, devir_row_idx), colors.HexColor('#E3F2FD')))
        style_cmds.append(('FONTNAME', (0, devir_row_idx), (-1, devir_row_idx), 'ArialTRB'))
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    title = f'Cari Ekstre - {firma_ad}'
    doc.build(
        elements,
        onFirstPage=lambda c, d: _header_footer(c, d, title, show_title=False),
        onLaterPages=lambda c, d: _header_footer(c, d, title, show_title=False),
    )
    buf.seek(0)
    return buf.getvalue()


def generate_stok_raporu_pdf(stok_data, donem_label=None):
    # V3 modern PDF (WeasyPrint) tercihen denenir
    try:
        from services import pdf_v3_service
        if pdf_v3_service.WEASYPRINT_AVAILABLE:
            from services.settings_service import get_company_settings
            try:
                sirket = get_company_settings()
            except Exception:
                sirket = {'firma_adi': 'Firma'}
            return pdf_v3_service.render_stok_raporu(stok_data, sirket, donem_label=donem_label or '')
    except Exception:
        pass

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=PDF_TOP_MARGIN_MM * mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = _styles()
    elements = []

    # Baslik ust bilgide veriliyor; govdede tekrar baslik gostermeyelim.
    elements.append(Spacer(1, 2 * mm))

    data = [['Kod', 'Ürün', 'Alış', 'Satış', 'Stok', 'Birim']]
    for row in stok_data:
        data.append([
            row['kod'], row['ad'], _fmt(row['alis'], blank_zero=True),
            _fmt(row['satis'], blank_zero=True), _fmt(row['stok'], blank_zero=True), row.get('birim', 'KG')
        ])

    t = Table(data, colWidths=[25*mm, 55*mm, 25*mm, 25*mm, 25*mm, 15*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, 'Stok Raporu'),
              onLaterPages=lambda c, d: _header_footer(c, d, 'Stok Raporu'))
    buf.seek(0)
    return buf.getvalue()


def generate_kasa_raporu_pdf(kasa_data, bakiye_info):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=PDF_TOP_MARGIN_MM * mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = _styles()
    elements = []

    # Baslik ust bilgide veriliyor; govdede tekrar baslik gostermeyelim.
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        f"Giriş: {_fmt(bakiye_info['giris'])} TL  |  Çıkış: {_fmt(bakiye_info['cikis'])} TL  |  Bakiye: {_fmt(bakiye_info['bakiye'])} TL",
        styles['TRSubtitle']
    ))
    elements.append(Spacer(1, 3 * mm))

    data = [['Tarih', 'Firma', 'Tür', 'Tutar', 'Ödeme Şekli', 'Açıklama']]
    for row in kasa_data:
        tarih = row['tarih'] or ''
        if '-' in tarih:
            p = tarih.split('-')
            tarih = f"{p[2]}.{p[1]}.{p[0]}"
        data.append([
            tarih, row.get('firma_ad', ''), row['tur'],
            _fmt(row['tutar'], blank_zero=True), row.get('odeme_sekli', ''),
            Paragraph(str(row.get('aciklama', ''))[:40], styles['TRSmall'])
        ])

    t = Table(data, colWidths=[20*mm, 35*mm, 15*mm, 25*mm, 22*mm, 50*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, 'Kasa Raporu'),
              onLaterPages=lambda c, d: _header_footer(c, d, 'Kasa Raporu'))
    buf.seek(0)
    return buf.getvalue()


def generate_cek_raporu_pdf(cek_data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=PDF_TOP_MARGIN_MM * mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = _styles()
    elements = []

    # Baslik ust bilgide veriliyor; govdede tekrar baslik gostermeyelim.
    elements.append(Spacer(1, 2 * mm))

    data = [['Çek No', 'Firma', 'Vade', 'Tutar', 'Tür', 'Durum']]
    for row in cek_data:
        vade = row.get('vade_tarih', '') or ''
        if '-' in vade:
            p = vade.split('-')
            vade = f"{p[2]}.{p[1]}.{p[0]}"
        data.append([
            row.get('cek_no', ''), row.get('firma_ad', ''), vade,
            _fmt(row['tutar'], blank_zero=True), row.get('cek_turu', ''), row.get('durum', '')
        ])

    t = Table(data, colWidths=[25*mm, 45*mm, 22*mm, 28*mm, 20*mm, 30*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, 'Çek Portföy Raporu'),
              onLaterPages=lambda c, d: _header_footer(c, d, 'Çek Portföy Raporu'))
    buf.seek(0)
    return buf.getvalue()

def generate_table_pdf(title, headers, rows):
    """Generic tablo PDF'i: hizli ekran ciktilari icin."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=PDF_TOP_MARGIN_MM * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    _styles()
    elements = [Spacer(1, 2 * mm)]

    table_data = [headers]
    for row in rows:
        line = []
        for cell in row:
            if isinstance(cell, (int, float)):
                line.append(_fmt(cell, blank_zero=True))
            else:
                line.append(_pretty_text(cell))
        table_data.append(line)

    col_widths = None
    if [str(h).strip().lower() for h in headers] == ['tarih', 'tür', 'ürün', 'miktar', 'birim fiyat', 'toplam']:
        col_widths = [24 * mm, 18 * mm, 48 * mm, 24 * mm, 24 * mm, 24 * mm]
    if col_widths is None:
        usable_width = A4[0] - (30 * mm)
        col_count = max(1, len(headers))
        col_w = usable_width / col_count
        col_widths = [col_w] * col_count

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    if len(headers) >= 4:
        t.setStyle(TableStyle([
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ]))
    elements.append(t)

    doc.build(
        elements,
        onFirstPage=lambda c, d: _header_footer(c, d, title),
        onLaterPages=lambda c, d: _header_footer(c, d, title),
    )
    buf.seek(0)
    return buf.getvalue()


def generate_hizli_mutabakat_pdf(firma_ad, ekstre_rows, cek_rows, kasa_rows):
    """Cari detay icin tek tus mutabakat PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=PDF_TOP_MARGIN_MM * mm, bottomMargin=20 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    styles = _styles()
    elements = [Spacer(1, 2 * mm)]

    # Ozet
    ekstre_bakiye = ekstre_rows[-1]['bakiye'] if ekstre_rows else 0
    cek_toplam = sum(float(r.get('tutar', 0) or 0) for r in cek_rows)
    kasa_giris = sum(float(r.get('tutar', 0) or 0) for r in kasa_rows if r.get('tur') == 'GELIR')
    kasa_cikis = sum(float(r.get('tutar', 0) or 0) for r in kasa_rows if r.get('tur') == 'GIDER')
    ozet_data = [
        ['Kalem', 'Tutar'],
        ['Ekstre Bakiye', f"{_fmt(ekstre_bakiye)} TL"],
        ['Cek Toplam', f"{_fmt(cek_toplam)} TL"],
        ['Kasa Giris', f"{_fmt(kasa_giris)} TL"],
        ['Kasa Cikis', f"{_fmt(kasa_cikis)} TL"],
    ]
    ozet = Table(ozet_data, colWidths=[60 * mm, 40 * mm], repeatRows=1)
    ozet.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
        ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ]))
    elements.extend([ozet, Spacer(1, 4 * mm)])

    def _section(title, headers, rows, col_widths):
        elements.append(Paragraph(title, styles['TRSubtitle']))
        data = [headers]
        for row in rows:
            data.append([_pretty_text(x) for x in row])
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'ArialTRB'),
            ('FONTNAME', (0, 1), (-1, -1), 'ArialTR'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#607D8B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        elements.extend([t, Spacer(1, 3 * mm)])

    _section(
        'Ekstre (Son 20)',
        ['Tarih', 'Aciklama', 'Borc', 'Alacak', 'Bakiye'],
        [
            [r.get('tarih', ''), r.get('aciklama', ''), _fmt(r.get('borc', 0)), _fmt(r.get('alacak', 0)), _fmt(r.get('bakiye', 0))]
            for r in (ekstre_rows[-20:] if ekstre_rows else [])
        ],
        [18 * mm, 70 * mm, 25 * mm, 25 * mm, 25 * mm],
    )
    _section(
        'Cekler',
        ['Cek No', 'Vade', 'Durum', 'Tutar'],
        [[r.get('cek_no', ''), r.get('vade_tarih', ''), r.get('durum', ''), _fmt(r.get('tutar', 0))] for r in cek_rows],
        [38 * mm, 26 * mm, 36 * mm, 30 * mm],
    )
    _section(
        'Kasa',
        ['Tarih', 'Tur', 'Odeme', 'Tutar', 'Aciklama'],
        [[r.get('tarih', ''), r.get('tur', ''), r.get('odeme_sekli', ''), _fmt(r.get('tutar', 0)), str(r.get('aciklama', ''))[:30]] for r in kasa_rows],
        [20 * mm, 18 * mm, 20 * mm, 25 * mm, 60 * mm],
    )

    doc.build(
        elements,
        onFirstPage=lambda c, d: _header_footer(c, d, f'Hizli Mutabakat - {firma_ad}'),
        onLaterPages=lambda c, d: _header_footer(c, d, f'Hizli Mutabakat - {firma_ad}'),
    )
    buf.seek(0)
    return buf.getvalue()


def generate_gelir_gider_pdf(gg_data, donem_label=None):
    """Gelir/Gider rapor PDF. WeasyPrint varsa v3 modern tasarim, yoksa generic tablo."""
    # V3 modern PDF (WeasyPrint) tercihen denenir
    try:
        from services import pdf_v3_service
        if pdf_v3_service.WEASYPRINT_AVAILABLE:
            from services.settings_service import get_company_settings
            try:
                sirket = get_company_settings()
            except Exception:
                sirket = {'firma_adi': 'Firma'}
            return pdf_v3_service.render_gelir_gider(gg_data, sirket, donem_label=donem_label or '')
    except Exception:
        pass

    # Fallback: generic tablo PDF
    headers = ['Tarih', 'Kategori', 'Açıklama', 'Tür', 'Tutar']
    rows = []
    for r in gg_data:
        tarih = r.get('tarih', '') or ''
        if '-' in tarih:
            p = tarih.split('-')
            tarih = f"{p[2]}.{p[1]}.{p[0]}"
        rows.append([
            tarih,
            r.get('kategori', ''),
            str(r.get('aciklama', ''))[:40],
            r.get('tur', ''),
            float(r.get('tutar', 0) or 0),
        ])
    title = 'Gelir / Gider Raporu'
    if donem_label:
        title += f' — {donem_label}'
    return generate_table_pdf(title, headers, rows)


def save_pdf_preview(pdf_bytes, filename):
    """PDF'i preview klasorune yazar ve tarayicida acilacak URL dondurur."""
    safe_name = ''.join(c for c in filename if c.isalnum() or c in ('_', '-', '.')).strip('.')
    if not safe_name.lower().endswith('.pdf'):
        safe_name += '.pdf'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    final_name = f"{Path(safe_name).stem}_{ts}.pdf"
    out_dir = get_pdf_preview_dir()
    out_path = out_dir / final_name
    out_path.write_bytes(pdf_bytes)
    return f"/pdf-preview/{final_name}"

