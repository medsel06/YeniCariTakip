"""Uygulama ayarlari islemleri."""
import os
import sys
from datetime import datetime
from db import get_db, BASE_DIR


def _normalize_logo_path(path: str) -> str:
    p = (path or '').strip()
    if not p:
        return ''
    # Mutlaka proje-ici goreli path sakla ki farkli PC'lerde de calissin.
    if os.path.isabs(p):
        try:
            rel = os.path.relpath(p, BASE_DIR)
            if not rel.startswith('..'):
                return rel.replace('\\', '/')
        except Exception:
            pass
    return p.replace('\\', '/')


def resolve_logo_path(path: str) -> str:
    """Logo yolunu mutlak hale getir. EXE (frozen) modunda asagidaki sirayla arar:
    1) Verilen mutlak path
    2) BASE_DIR + relative (EXE yaninda assets/ klasoru)
    3) sys._MEIPASS + relative (PyInstaller onefile bundle icine gomulmus)
    4) Son care: ilk uretilen path (dosya olmasa bile)
    """
    p = (path or '').strip()
    if not p:
        return ''
    if os.path.isabs(p):
        if os.path.exists(p):
            return p
        # Relatif hale getirmeyi dene, frozen icinde arayalim
        try:
            p = os.path.relpath(p, BASE_DIR).replace('\\', '/')
        except Exception:
            return p

    # 1) BASE_DIR
    candidate = os.path.join(BASE_DIR, p)
    if os.path.exists(candidate):
        return candidate

    # 2) Frozen mode: sys._MEIPASS icinde ara
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate2 = os.path.join(meipass, p)
        if os.path.exists(candidate2):
            return candidate2

    # Fallback: BASE_DIR path'i don
    return candidate


def get_company_settings():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM settings_company WHERE id=1").fetchone()
        if not row:
            conn.execute("INSERT INTO settings_company (id, updated_at) VALUES (1, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
            row = conn.execute("SELECT * FROM settings_company WHERE id=1").fetchone()
        data = dict(row) if row else {}
        data['logo_path'] = _normalize_logo_path(data.get('logo_path', ''))
        data['logo_path_resolved'] = resolve_logo_path(data.get('logo_path', ''))
        return data


def update_company_settings(data):
    payload = {
        'firma_adi': data.get('firma_adi', ''),
        'vkn_tckn': data.get('vkn_tckn', ''),
        'vergi_dairesi': data.get('vergi_dairesi', ''),
        'adres': data.get('adres', ''),
        'nace': data.get('nace', ''),
        'is_alani': data.get('is_alani', ''),
        'telefon': data.get('telefon', ''),
        'email': data.get('email', ''),
        'logo_path': _normalize_logo_path(data.get('logo_path', '')),
        'ucret_periyodu': data.get('ucret_periyodu', 'AYLIK'),
        'uretim_takibi': 1 if data.get('uretim_takibi') else 0,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with get_db() as conn:
        conn.execute("INSERT INTO settings_company (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
        conn.execute(
            """
            UPDATE settings_company
            SET firma_adi=?, vkn_tckn=?, vergi_dairesi=?, adres=?, nace=?, is_alani=?,
                telefon=?, email=?, logo_path=?, ucret_periyodu=?, uretim_takibi=?, updated_at=?
            WHERE id=1
            """,
            (
                payload['firma_adi'],
                payload['vkn_tckn'],
                payload['vergi_dairesi'],
                payload['adres'],
                payload['nace'],
                payload['is_alani'],
                payload['telefon'],
                payload['email'],
                payload['logo_path'],
                payload['ucret_periyodu'],
                payload['uretim_takibi'],
                payload['updated_at'],
            ),
        )
    return payload
