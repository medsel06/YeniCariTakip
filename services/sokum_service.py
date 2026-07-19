"""Söküm (ayrıştırma) verimi — parti bazlı girdi/çıktı kâr takibi (özellikle hurda).

Bir parti: karışık hurda/motosiklet alınır (giriş: miktar kg + maliyet TL),
sökülüp ayrıştırılır, çıkan malzemeler (bakır, alüminyum...) satılır (çıktılar).
Kâr = çıktı toplamı - giriş maliyeti; fire = giriş kg - çıktı kg; verim = çıktı/giriş.
Çıktılar tek JSON kolonunda tutulur (ayrı tablo gerektirmez)."""
import json
from datetime import datetime
from db import get_db


def _ensure_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sokum_parti (
            id SERIAL PRIMARY KEY,
            tarih TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            giris_miktar REAL DEFAULT 0,
            giris_maliyet REAL DEFAULT 0,
            ciktilar TEXT DEFAULT '[]',
            cikti_toplam REAL DEFAULT 0,
            cikti_miktar REAL DEFAULT 0,
            notlar TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')


def _hesapla(row):
    giris_mal = float(row.get('giris_maliyet', 0) or 0)
    giris_kg = float(row.get('giris_miktar', 0) or 0)
    cikti_t = float(row.get('cikti_toplam', 0) or 0)
    cikti_kg = float(row.get('cikti_miktar', 0) or 0)
    row['kar'] = cikti_t - giris_mal
    row['fire_kg'] = giris_kg - cikti_kg
    row['verim'] = (cikti_kg / giris_kg * 100.0) if giris_kg > 0 else 0.0
    row['marj'] = (row['kar'] / giris_mal * 100.0) if giris_mal > 0 else 0.0
    try:
        row['ciktilar_list'] = json.loads(row.get('ciktilar') or '[]')
    except Exception:
        row['ciktilar_list'] = []
    return row


def _ozetle(ciktilar):
    toplam = sum(float(c.get('tutar', 0) or 0) for c in ciktilar)
    miktar = sum(float(c.get('miktar', 0) or 0) for c in ciktilar)
    return toplam, miktar


def get_sokum_partileri():
    with get_db() as conn:
        _ensure_table(conn)
        rows = conn.execute("SELECT * FROM sokum_parti ORDER BY tarih DESC, id DESC").fetchall()
        return [_hesapla(dict(r)) for r in rows]


def add_sokum_parti(data):
    ciktilar = data.get('ciktilar') or []
    cikti_t, cikti_kg = _ozetle(ciktilar)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute('''
            INSERT INTO sokum_parti
                (tarih, aciklama, giris_miktar, giris_maliyet, ciktilar, cikti_toplam, cikti_miktar, notlar, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (
            data.get('tarih', ''), data.get('aciklama', ''),
            float(data.get('giris_miktar', 0) or 0), float(data.get('giris_maliyet', 0) or 0),
            json.dumps(ciktilar, ensure_ascii=False), cikti_t, cikti_kg,
            data.get('notlar', ''), now,
        ))


def update_sokum_parti(pid, data):
    ciktilar = data.get('ciktilar') or []
    cikti_t, cikti_kg = _ozetle(ciktilar)
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute('''
            UPDATE sokum_parti
            SET tarih=?, aciklama=?, giris_miktar=?, giris_maliyet=?, ciktilar=?, cikti_toplam=?, cikti_miktar=?, notlar=?
            WHERE id=?
        ''', (
            data.get('tarih', ''), data.get('aciklama', ''),
            float(data.get('giris_miktar', 0) or 0), float(data.get('giris_maliyet', 0) or 0),
            json.dumps(ciktilar, ensure_ascii=False), cikti_t, cikti_kg,
            data.get('notlar', ''), pid,
        ))


def delete_sokum_parti(pid):
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM sokum_parti WHERE id=?", (pid,))


def get_sokum_ozet():
    rows = get_sokum_partileri()
    return {
        'parti': len(rows),
        'giris_maliyet': sum(float(r.get('giris_maliyet', 0) or 0) for r in rows),
        'cikti_toplam': sum(float(r.get('cikti_toplam', 0) or 0) for r in rows),
        'kar': sum(float(r.get('kar', 0) or 0) for r in rows),
    }
