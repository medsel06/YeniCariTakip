"""Cek State Machine ve islemleri"""
from datetime import datetime
from db import get_db

ALINAN_TRANSITIONS = {
    'PORTFOYDE': ['TAHSILE_VERILDI', 'CIRO_EDILDI', 'IADE_EDILDI'],
    'TAHSILE_VERILDI': ['TAHSIL_EDILDI', 'KARSILIKSIZ', 'IADE_EDILDI'],
}

VERILEN_TRANSITIONS = {
    'KESILDI': ['ODENDI', 'KARSILIKSIZ'],
}

DURUM_LABELS = {
    'PORTFOYDE': 'Portföyde',
    'TAHSILE_VERILDI': 'Tahsile Verildi',
    'TAHSIL_EDILDI': 'Tahsil Edildi',
    'CIRO_EDILDI': 'Ciro Edildi',
    'IADE_EDILDI': 'İade Edildi',
    'KARSILIKSIZ': 'Karşılıksız',
    'KESILDI': 'Kesildi',
    'ODENDI': 'Ödendi',
}

DURUM_COLORS = {
    'PORTFOYDE': 'blue',
    'TAHSILE_VERILDI': 'orange',
    'TAHSIL_EDILDI': 'green',
    'CIRO_EDILDI': 'purple',
    'IADE_EDILDI': 'grey',
    'KARSILIKSIZ': 'red',
    'KESILDI': 'blue',
    'ODENDI': 'green',
}


def get_valid_transitions(cek_turu, current_durum):
    if cek_turu == 'ALINAN':
        return ALINAN_TRANSITIONS.get(current_durum, [])
    elif cek_turu == 'VERILEN':
        return VERILEN_TRANSITIONS.get(current_durum, [])
    return []


def list_cekler(cek_turu=None):
    with get_db() as conn:
        if cek_turu:
            rows = conn.execute(
                'SELECT * FROM cekler WHERE cek_turu=? ORDER BY vade_tarih DESC, id DESC',
                (cek_turu,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM cekler ORDER BY vade_tarih DESC, id DESC'
            ).fetchall()
        return [dict(r) for r in rows]


def add_cek(data):
    with get_db() as conn:
        default_durum = 'PORTFOYDE' if data.get('cek_turu', 'ALINAN') == 'ALINAN' else 'KESILDI'
        evrak_tipi = data.get('evrak_tipi', 'CEK')
        cur = conn.execute('''
            INSERT INTO cekler (cek_no, firma_kod, firma_ad, kesim_tarih, vade_tarih,
                tutar, tur, durum, cek_turu, kesideci, lehtar, notlar, evrak_tipi)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            RETURNING id
        ''', (
            data.get('cek_no', ''), data.get('firma_kod', ''), data.get('firma_ad', ''),
            data.get('kesim_tarih', ''), data.get('vade_tarih', ''),
            data.get('tutar', 0), data.get('tur', ''), default_durum,
            data.get('cek_turu', 'ALINAN'), data.get('kesideci', ''),
            data.get('lehtar', ''), data.get('notlar', ''), evrak_tipi
        ))
        cek_id = cur.fetchone()['id']
        now = datetime.now().strftime('%Y-%m-%d')
        conn.execute('''
            INSERT INTO cek_hareketleri (cek_id, tarih, eski_durum, yeni_durum, aciklama)
            VALUES (?,?,?,?,?)
        ''', (cek_id, now, None, default_durum, 'Çek oluşturuldu'))
        return cek_id


def change_durum(cek_id, new_durum, aciklama='', ciro_firma_kod='', ciro_firma_ad=''):
    with get_db() as conn:
        cek = conn.execute('SELECT * FROM cekler WHERE id=?', (cek_id,)).fetchone()
        if not cek:
            return False, 'Çek bulunamadı'

        cek_turu = cek['cek_turu'] or 'ALINAN'
        old_durum = cek['durum']
        valid = get_valid_transitions(cek_turu, old_durum)

        if new_durum not in valid:
            return False, f'Geçersiz geçiş: {old_durum} -> {new_durum}'

        now = datetime.now().strftime('%Y-%m-%d')

        conn.execute('UPDATE cekler SET durum=? WHERE id=?', (new_durum, cek_id))

        if new_durum in ('TAHSIL_EDILDI', 'ODENDI'):
            conn.execute('UPDATE cekler SET tahsil_tarih=? WHERE id=?', (now, cek_id))

        if new_durum == 'CIRO_EDILDI' and ciro_firma_kod:
            conn.execute(
                'UPDATE cekler SET ciro_firma_kod=?, ciro_firma_ad=? WHERE id=?',
                (ciro_firma_kod, ciro_firma_ad, cek_id)
            )

        conn.execute('''
            INSERT INTO cek_hareketleri (cek_id, tarih, eski_durum, yeni_durum, aciklama)
            VALUES (?,?,?,?,?)
        ''', (cek_id, now, old_durum, new_durum, aciklama))

        # Kasa entegrasyonu
        if new_durum == 'TAHSIL_EDILDI':
            conn.execute('''
                INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama, cek_id)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (now, cek['firma_kod'], cek['firma_ad'], 'GELIR', cek['tutar'],
                  'CEK', f"Çek tahsilat: {cek['cek_no']}", cek_id))
        elif new_durum == 'ODENDI':
            conn.execute('''
                INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama, cek_id)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (now, cek['firma_kod'], cek['firma_ad'], 'GIDER', cek['tutar'],
                  'CEK', f"Çek ödeme: {cek['cek_no']}", cek_id))

        return True, 'Durum güncellendi'


def update_cek(cek_id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE cekler SET cek_no=?, firma_kod=?, firma_ad=?, kesim_tarih=?, vade_tarih=?,
                tutar=?, notlar=?
            WHERE id=?
        ''', (
            data.get('cek_no', ''), data.get('firma_kod', ''), data.get('firma_ad', ''),
            data.get('kesim_tarih', ''), data.get('vade_tarih', ''),
            data.get('tutar', 0), data.get('notlar', ''),
            cek_id
        ))


def get_cek_by_id(cek_id):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM cekler WHERE id=?', (cek_id,)).fetchone()
        return dict(r) if r else None


def delete_cek(cek_id):
    with get_db() as conn:
        conn.execute('DELETE FROM cek_hareketleri WHERE cek_id=?', (cek_id,))
        conn.execute('DELETE FROM cekler WHERE id=?', (cek_id,))


def get_cek_hareketleri(cek_id):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM cek_hareketleri WHERE cek_id=? ORDER BY tarih, id',
            (cek_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_vade_uyarilari():
    """Dashboard icin vade uyarilari"""
    from datetime import timedelta
    today = datetime.now().date()
    d3 = (today + timedelta(days=3)).strftime('%Y-%m-%d')
    d7 = (today + timedelta(days=7)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    with get_db() as conn:
        bugun = conn.execute(
            "SELECT * FROM cekler WHERE vade_tarih=? AND durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI')",
            (today_str,)
        ).fetchall()
        uc_gun = conn.execute(
            "SELECT * FROM cekler WHERE vade_tarih > ? AND vade_tarih <= ? AND durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI')",
            (today_str, d3)
        ).fetchall()
        yedi_gun = conn.execute(
            "SELECT * FROM cekler WHERE vade_tarih > ? AND vade_tarih <= ? AND durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI')",
            (d3, d7)
        ).fetchall()
        gecmis = conn.execute(
            "SELECT * FROM cekler WHERE vade_tarih < ? AND durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI')",
            (today_str,)
        ).fetchall()

    return {
        'gecmis': [dict(r) for r in gecmis],
        'bugun': [dict(r) for r in bugun],
        'uc_gun': [dict(r) for r in uc_gun],
        'yedi_gun': [dict(r) for r in yedi_gun],
    }


def list_cekler_portfoyde():
    """Portföydeki çekleri döndürür (ciro için)"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cekler WHERE durum='PORTFOYDE' AND cek_turu='ALINAN' ORDER BY vade_tarih"
        ).fetchall()
        return [dict(r) for r in rows]


def generate_firma_cek_no():
    """Firma çeki için otomatik numara"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT cek_no FROM cekler WHERE cek_turu='VERILEN' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row and row['cek_no']:
            try:
                num = int(row['cek_no'].split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'ALSE-{num:04d}'
