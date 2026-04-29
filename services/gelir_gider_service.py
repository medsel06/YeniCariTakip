"""Gelir/Gider islemleri"""
from datetime import datetime
from db import get_db

# One cikan (cari bazli) kategoriler - dialog'da ustte ve farkli renkte
ONE_CIKAN_GIDER_KATEGORILER = ['Nakliye', 'Ardiye']

GELIR_KATEGORILER = [
    'Fason İşçilik', 'Hurda Satış', 'Kira Geliri', 'Komisyon',
    'Faiz', 'Kur Farkı Geliri', 'Vade Farkı Geliri', 'Diğer',
]

GIDER_KATEGORILER = [
    'Nakliye', 'Ardiye',  # One cikanlar ustte
    'Kira', 'Elektrik', 'Su', 'Doğalgaz', 'Telefon', 'İnternet',
    'Personel Maaş', 'SGK', 'Vergi', 'Sigorta', 'Akaryakıt',
    'Bakım/Onarım', 'Kırtasiye', 'Banka Masrafı',
    'Damga Vergisi', 'Noter', 'Yemek/İkram', 'Diğer',
]


def _date_filter(yil=None, ay=None, col='tarih'):
    """Donem filtresi (3 modlu): aylik / yillik / tum zamanlar.
    Bos tarih ('') ve NULL kayitlari dislar."""
    yil = int(yil) if yil else None
    ay = int(ay) if ay else None
    if ay is not None and ay not in range(1, 13):
        ay = None
    base = f" AND {col} IS NOT NULL AND {col} != ''"
    if yil and ay:
        return base + f" AND {col} LIKE ?", [f'{yil:04d}-{ay:02d}%']
    elif yil:
        return base + f" AND {col} LIKE ?", [f'{yil:04d}-%']
    return base, []


def get_gelir_gider_list(yil=None, ay=None):
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM gelir_gider WHERE 1=1{flt} ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def get_gelir_gider_ozet(yil=None, ay=None):
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        gelir = conn.execute(
            f"SELECT COALESCE(SUM(toplam),0) FROM gelir_gider WHERE tur='GELIR'{flt}", params
        ).fetchone()[0]
        gider = conn.execute(
            f"SELECT COALESCE(SUM(toplam),0) FROM gelir_gider WHERE tur='GIDER'{flt}", params
        ).fetchone()[0]
        return {'gelir': gelir, 'gider': gider, 'net': gelir - gider}


def _add_gelir_gider_conn(conn, data):
    """Acik bir conn uzerinde gelir_gider ekler. Icerideki baska islemlerle ayni transaction'da calisir."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    cur = conn.execute('''
        INSERT INTO gelir_gider
            (tarih, tur, kategori, aciklama, tutar, kdv_orani, kdv_tutar, toplam, odeme_sekli,
             firma_kod, firma_ad, odeme_durumu, vade_tarih, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        RETURNING id
    ''', (
        data['tarih'], data['tur'], data.get('kategori', ''),
        data.get('aciklama', ''), data['tutar'],
        data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
        data.get('toplam', data['tutar']),
        data.get('odeme_sekli', ''),
        data.get('firma_kod', ''), data.get('firma_ad', ''),
        data.get('odeme_durumu', 'ODENDI'),
        data.get('vade_tarih', ''),
        now,
    ))
    return cur.fetchone()['id']


def add_gelir_gider(data):
    with get_db() as conn:
        return _add_gelir_gider_conn(conn, data)


def update_gelir_gider(rec_id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE gelir_gider
            SET tarih=?, tur=?, kategori=?, aciklama=?, tutar=?, kdv_orani=?, kdv_tutar=?, toplam=?, odeme_sekli=?,
                firma_kod=?, firma_ad=?, odeme_durumu=?, vade_tarih=?
            WHERE id=?
        ''', (
            data['tarih'], data['tur'], data.get('kategori', ''),
            data.get('aciklama', ''), data['tutar'],
            data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
            data.get('toplam', data['tutar']),
            data.get('odeme_sekli', ''),
            data.get('firma_kod', ''), data.get('firma_ad', ''),
            data.get('odeme_durumu', 'ODENDI'),
            data.get('vade_tarih', ''),
            rec_id,
        ))


def delete_gelir_gider(rec_id):
    with get_db() as conn:
        # Bagli kasa kayitlarini da sil (auto-olusturulanlar)
        conn.execute('DELETE FROM kasa WHERE gelir_gider_id=?', (rec_id,))
        conn.execute('DELETE FROM gelir_gider WHERE id=?', (rec_id,))
