"""V3 modern PDF rendering — WeasyPrint + Jinja2.

Bu servis v3 'PDF Dökümleri.html' tasarımını birebir backend'e portluyor:
- Cari Hesap Ekstresi (cari ekstre PDF)
- Stok Durum Raporu (stok rapor PDF)
- Gelir / Gider Raporu (gg rapor PDF)

Kullanım: pdf_service.generate_*_pdf fonksiyonlari WeasyPrint kuruluysa buraya
delegate eder, yoksa eski reportlab cıktısına dönerler (graceful fallback).
"""
import os
import re
from datetime import datetime
from pathlib import Path

# WeasyPrint Linux'ta sorunsuz, Windows'ta GTK ister.
# Local dev (Windows) icin import hatasini yakalayip flag set ediyoruz.
try:
    from weasyprint import HTML  # type: ignore
    WEASYPRINT_AVAILABLE = True
    WEASYPRINT_ERROR = None
except Exception as e:  # noqa: BLE001 — herhangi bir import/dlopen hatasini yakala
    HTML = None  # type: ignore
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_ERROR = str(e)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from db import BASE_DIR


# ---------- Jinja env ----------
_TEMPLATE_DIR = Path(BASE_DIR) / 'templates'
_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=False,
            lstrip_blocks=False,
        )
        _env.filters['abs'] = lambda x: abs(float(x or 0))
    return _env


# ---------- Format helpers ----------
def _format_money(val) -> str:
    """1234.5 -> '1.234,50' (Turkce muhasebe formati)."""
    try:
        v = float(val or 0)
    except (TypeError, ValueError):
        v = 0.0
    s = f"{abs(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"-{s}" if v < 0 else s


def _format_money_short(val) -> str:
    """Buyuk tutarlar icin kisa: 1.234.567 -> '1,23 M'."""
    try:
        v = float(val or 0)
    except (TypeError, ValueError):
        v = 0.0
    av = abs(v)
    sign = '-' if v < 0 else ''
    if av >= 1_000_000_000:
        return f"{sign}{(av/1_000_000_000):.2f}".replace('.', ',') + ' Mr'
    if av >= 1_000_000:
        return f"{sign}{(av/1_000_000):.2f}".replace('.', ',') + ' M'
    if av >= 1_000:
        return f"{sign}{(av/1_000):.1f}".replace('.', ',') + ' K'
    return _format_money(v)


def _format_date(s) -> str:
    """'2026-04-29' -> '29.04.2026'. Bos / hatali ise '—'."""
    if not s:
        return '—'
    txt = str(s).strip()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', txt)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return txt


def _brand_initials(firma_adi: str) -> str:
    """Firma adından markamsı 2-3 harf kısaltma uretir.

    'ALSE Plastik Hammadde San.' -> 'AP'
    'Şenol Çelik Tic.' -> 'ŞÇ'
    """
    if not firma_adi:
        return '—'
    # Noktalama ve kisaltma kelimelerini at
    skip = {'san', 'tic', 'ltd', 'sti', 'sti.', 'ltd.', 've', 'a.s.', 'as'}
    parts = [p.strip(' .,') for p in re.split(r'[\s.]+', firma_adi) if p.strip(' .,')]
    parts = [p for p in parts if p.lower() not in skip]
    if not parts:
        return firma_adi[:2].upper()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def _clean_aciklama(ack: str) -> str:
    """Ekstre aciklama prefixlerini ('Alış: ', 'Tahsilat: ' ...) kaldir."""
    if not ack:
        return ''
    txt = str(ack).strip()
    for pfx in ('Alış:', 'Alis:', 'Satış:', 'Satis:', 'Tahsilat:', 'Ödeme:',
                'Odeme:', 'Gelir:', 'Gider:', 'Alınan Çek:', 'Alinan Cek:',
                'Verilen Çek:', 'Verilen Cek:'):
        if txt.lower().startswith(pfx.lower()):
            rest = txt.split(':', 1)[1].strip() if ':' in txt else txt
            return rest if rest else txt
    return txt


def _doc_no(prefix: str) -> str:
    """EKS-2026-04-1430 gibi belge no uretir."""
    now = datetime.now()
    return f"{prefix}-{now.strftime('%Y-%m-%d-%H%M')}"


def _common_ctx(sirket: dict) -> dict:
    now = datetime.now()
    return {
        'sirket': sirket,
        'brand_initials': _brand_initials(sirket.get('firma_adi') or ''),
        'doc_date': now.strftime('%d.%m.%Y'),
        'doc_datetime': now.strftime('%d.%m.%Y %H:%M'),
        'format_money': _format_money,
        'format_money_short': _format_money_short,
        'format_date': _format_date,
    }


def _render(template_name: str, ctx: dict) -> bytes:
    env = _get_env()
    template = env.get_template(template_name)
    html = template.render(**ctx)
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(f'WeasyPrint kurulu degil: {WEASYPRINT_ERROR}')
    return HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()


# ---------- Public API ----------
def render_cari_ekstre(firma: dict, ekstre_meta: dict, sirket: dict) -> bytes:
    """Cari ekstre PDF.
    firma: {kod, ad, vkn_tckn, vergi_dairesi, tel, adres}
    ekstre_meta: get_cari_ekstre(with_meta=True) cikti
        {donem_label, devir, satirlar:[{tarih,aciklama,borc,alacak,bakiye,tip,kaynak}], donem_borc, donem_alacak, kapanis_bakiye}
    sirket: settings_company dict
    """
    satirlar = []
    for r in ekstre_meta.get('satirlar', []) or []:
        satirlar.append({
            **r,
            'aciklama_clean': _clean_aciklama(r.get('aciklama') or ''),
        })

    ctx = _common_ctx(sirket)
    ctx.update({
        'firma': firma or {},
        'donem_label': ekstre_meta.get('donem_label') or 'Tüm Zamanlar',
        'devir': ekstre_meta.get('devir', 0) or 0,
        'satirlar': satirlar,
        'donem_borc': ekstre_meta.get('donem_borc', 0) or 0,
        'donem_alacak': ekstre_meta.get('donem_alacak', 0) or 0,
        'kapanis_bakiye': ekstre_meta.get('kapanis_bakiye', 0) or 0,
        'doc_no': _doc_no('EKS'),
    })
    return _render('pdf_cari_ekstre.html', ctx)


def render_stok_raporu(stok_data: list, sirket: dict, donem_label: str = '') -> bytes:
    """Stok rapor PDF.
    stok_data: [{kod, ad, kategori, birim, alis, satis, stok, alis_tutar, satis_tutar}]
    """
    rows = list(stok_data or [])
    cesit = len(rows)

    # Kategori grouping
    kategoriler_map: dict = {}
    toplam_alis_tutar = 0.0
    kritik = 0
    for r in rows:
        k = (r.get('kategori') or 'Diğer').strip() or 'Diğer'
        if k not in kategoriler_map:
            kategoriler_map[k] = {'kategori': k, 'cesit': 0, 'toplam_stok': 0.0, 'alis_tutar': 0.0}
        kategoriler_map[k]['cesit'] += 1
        kategoriler_map[k]['toplam_stok'] += float(r.get('stok') or 0)
        kategoriler_map[k]['alis_tutar'] += float(r.get('alis_tutar') or 0)
        toplam_alis_tutar += float(r.get('alis_tutar') or 0)
        if float(r.get('stok') or 0) < 0:
            kritik += 1

    kategoriler = sorted(kategoriler_map.values(), key=lambda x: -x['alis_tutar'])
    for k in kategoriler:
        k['pct'] = (k['alis_tutar'] / toplam_alis_tutar * 100.0) if toplam_alis_tutar > 0 else 0.0

    toplam_satis_tutar = sum(float(r.get('satis_tutar') or 0) for r in rows)

    ctx = _common_ctx(sirket)
    ctx.update({
        'stok_data': rows,
        'kategoriler': kategoriler,
        'donem_label': donem_label or '',
        'doc_no': _doc_no('STK'),
        'stat': {
            'cesit': cesit,
            'kategori_sayisi': len(kategoriler),
            'alis_tutar': toplam_alis_tutar,
            'satis_tutar': toplam_satis_tutar,
            'kritik': kritik,
        },
    })
    return _render('pdf_stok_raporu.html', ctx)


def render_gelir_gider(rows: list, sirket: dict, donem_label: str = '') -> bytes:
    """Gelir/Gider rapor PDF.
    rows: [{tarih, kategori, aciklama, firma_ad, odeme_sekli, tur (GELIR/GIDER), tutar}]
    """
    rows = list(rows or [])

    gelir_top = sum(float(r.get('tutar') or 0) for r in rows if (r.get('tur') or '').upper() == 'GELIR')
    gider_top = sum(float(r.get('tutar') or 0) for r in rows if (r.get('tur') or '').upper() == 'GIDER')
    gelir_adet = sum(1 for r in rows if (r.get('tur') or '').upper() == 'GELIR')
    gider_adet = sum(1 for r in rows if (r.get('tur') or '').upper() == 'GIDER')
    net = gelir_top - gider_top
    oran = f"{(gider_top/gelir_top*100):.1f}%".replace('.', ',') if gelir_top > 0 else '—'
    kar_marji = f"%{(net/gelir_top*100):.1f}".replace('.', ',') if gelir_top > 0 else '—'

    # Kategori dağılımı (sadece GIDER)
    kategori_map: dict = {}
    for r in rows:
        if (r.get('tur') or '').upper() != 'GIDER':
            continue
        k = (r.get('kategori') or 'Diğer').strip() or 'Diğer'
        if k not in kategori_map:
            kategori_map[k] = {'kategori': k, 'tutar': 0.0}
        kategori_map[k]['tutar'] += float(r.get('tutar') or 0)
    kategori_dagilim = sorted(kategori_map.values(), key=lambda x: -x['tutar'])
    for k in kategori_dagilim:
        k['pct'] = (k['tutar'] / gider_top * 100.0) if gider_top > 0 else 0.0

    sabit_keys = {'KIRA', 'MAAS', 'MAAŞ', 'SGK', 'INTERNET', 'INTERNET/TELEFON', 'TELEFON'}
    sabit = sum(k['tutar'] for k in kategori_dagilim if k['kategori'].upper() in sabit_keys)
    degisken = gider_top - sabit
    sabit_pct = f"%{(sabit/gider_top*100):.0f}" if gider_top > 0 else '%0'
    degisken_pct = f"%{(degisken/gider_top*100):.0f}" if gider_top > 0 else '%0'

    ctx = _common_ctx(sirket)
    ctx.update({
        'rows': rows,
        'kategori_dagilim': kategori_dagilim,
        'donem_label': donem_label or '',
        'doc_no': _doc_no('GG'),
        'stat': {
            'gelir_top': gelir_top,
            'gider_top': gider_top,
            'gelir_adet': gelir_adet,
            'gider_adet': gider_adet,
            'net': net,
            'oran': oran,
            'kar_marji': kar_marji,
            'sabit': sabit,
            'degisken': degisken,
            'sabit_pct': sabit_pct,
            'degisken_pct': degisken_pct,
        },
    })
    return _render('pdf_gelir_gider.html', ctx)
