"""Kasa ve hareket işlemleri"""
import json
from datetime import datetime
from db import get_db


def _date_filter(yil=None, ay=None, col='tarih'):
    """Donem filtresi (3 modlu): aylik / yillik / tum zamanlar.
    Yil/ay seciliyse bos tarih ('') ve NULL kayitlari dislar (mali dogruluk).
    Tum zamanlar modunda tarihsiz kayitlar DAHIL — kullanici listede gorup
    duzeltebilsin (kirmizi satir UI uyarisi pages tarafinda eklenir)."""
    yil = int(yil) if yil else None
    ay = int(ay) if ay else None
    if ay is not None and ay not in range(1, 13):
        ay = None
    if yil and ay:
        return f" AND {col} IS NOT NULL AND {col} != '' AND {col} LIKE ?", [f'{yil:04d}-{ay:02d}%']
    elif yil:
        return f" AND {col} IS NOT NULL AND {col} != '' AND {col} LIKE ?", [f'{yil:04d}-%']
    # Tum zamanlar — tarihsizler dahil
    return "", []


def get_kasa_list(yil=None, ay=None):
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM kasa WHERE 1=1{flt} ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def get_kasa_bakiye(yil=None, ay=None):
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        giris = conn.execute(f"SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE tur='GELIR'{flt}", params).fetchone()[0]
        cikis = conn.execute(f"SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE tur='GIDER'{flt}", params).fetchone()[0]
        return {'giris': giris, 'cikis': cikis, 'bakiye': giris - cikis}


def _add_kasa_conn(conn, data):
    """Acik bir conn uzerinde kasa kaydi ekler."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    cur = conn.execute('''
        INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama, cek_id, gelir_gider_id, banka, kategori, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        RETURNING id
    ''', (
        data['tarih'], data.get('firma_kod', ''), data.get('firma_ad', ''),
        data['tur'], data['tutar'], data.get('odeme_sekli', ''), data.get('aciklama', ''),
        data.get('cek_id'), data.get('gelir_gider_id'), data.get('banka', ''),
        data.get('kategori', ''),
        now,
    ))
    return cur.fetchone()['id']


def add_kasa(data):
    with get_db() as conn:
        return _add_kasa_conn(conn, data)


def update_kasa(id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE kasa SET tarih=?, firma_kod=?, firma_ad=?, tur=?, tutar=?, odeme_sekli=?, aciklama=?, kategori=?
            WHERE id=?
        ''', (
            data['tarih'], data.get('firma_kod', ''), data.get('firma_ad', ''),
            data['tur'], data['tutar'], data.get('odeme_sekli', ''), data.get('aciklama', ''),
            data.get('kategori', ''),
            id
        ))


def delete_kasa(id):
    with get_db() as conn:
        rec = conn.execute('SELECT * FROM kasa WHERE id=?', (id,)).fetchone()
        if not rec:
            return

        # Ciro ile olusmus kasa kaydi silinirse cek tekrar portfoye alinmali.
        cek_id = rec['cek_id']
        if rec['odeme_sekli'] == 'CEK' and cek_id:
            cek = conn.execute('SELECT * FROM cekler WHERE id=?', (cek_id,)).fetchone()
            if cek and cek['durum'] == 'CIRO_EDILDI':
                now = datetime.now().strftime('%Y-%m-%d')
                conn.execute(
                    '''
                    UPDATE cekler
                    SET durum='PORTFOYDE',
                        ciro_firma_kod='',
                        ciro_firma_ad=''
                    WHERE id=?
                    ''',
                    (cek_id,),
                )
                conn.execute(
                    '''
                    INSERT INTO cek_hareketleri (cek_id, tarih, eski_durum, yeni_durum, aciklama)
                    VALUES (?,?,?,?,?)
                    ''',
                    (
                        cek_id,
                        now,
                        'CIRO_EDILDI',
                        'PORTFOYDE',
                        f'Ciro geri alma: bagli kasa kaydi silindi (kasa_id={id})',
                    ),
                )

        conn.execute('DELETE FROM kasa WHERE id=?', (id,))


def get_kasa_by_id(id):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM kasa WHERE id=?', (id,)).fetchone()
        return dict(r) if r else None


# --- Hareket İşlemleri ---

def get_hareketler(yil=None, ay=None):
    """Tum hareketler (stok + kasa) - DB tarafinda birlesik sirayla cekilir."""
    flt, params = _date_filter(yil, ay)
    sql = f"""
    SELECT * FROM (
        SELECT
            CAST(id AS TEXT) AS unified_id,
            tarih,
            firma_kod,
            firma_ad,
            tur,
            urun_kod,
            urun_ad,
            miktar,
            birim_fiyat,
            toplam,
            kdv_orani,
            kdv_tutar,
            kdvli_toplam,
            tevkifat_orani,
            tevkifat_tutar,
            tevkifatsiz_kdv,
            aciklama,
            belge_no,
            'STOK' AS source,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts
        FROM hareketler WHERE 1=1{flt}

        UNION ALL

        SELECT
            'K-' || CAST(id AS TEXT) AS unified_id,
            tarih,
            firma_kod,
            firma_ad,
            CASE WHEN tur='GELIR' THEN 'TAHSILAT' ELSE 'ODEME' END AS tur,
            '' AS urun_kod,
            'Kasa: ' || COALESCE(NULLIF(aciklama, ''), '-') AS urun_ad,
            0 AS miktar,
            0 AS birim_fiyat,
            tutar AS toplam,
            0 AS kdv_orani,
            0 AS kdv_tutar,
            tutar AS kdvli_toplam,
            '0' AS tevkifat_orani,
            0 AS tevkifat_tutar,
            0 AS tevkifatsiz_kdv,
            aciklama,
            '' AS belge_no,
            'KASA' AS source,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts
        FROM kasa WHERE 1=1{flt}
    )
    ORDER BY tarih DESC, sort_ts DESC, unified_id DESC
    """
    with get_db() as conn:
        rows = conn.execute(sql, params + params).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            row['id'] = row.pop('unified_id')
            row.pop('sort_ts', None)
            result.append(row)
        return result


def get_hareket_by_id(id):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM hareketler WHERE id=?', (id,)).fetchone()
        return dict(r) if r else None


def add_hareket(data):
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        cur = conn.execute('''
            INSERT INTO hareketler
                (tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad, miktar, birim_fiyat,
                 toplam, kdv_orani, kdv_tutar, kdvli_toplam,
                 tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv, aciklama, belge_no, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            RETURNING id
        ''', (
            data['tarih'], data['firma_kod'], data['firma_ad'], data['tur'],
            data['urun_kod'], data['urun_ad'], data['miktar'], data['birim_fiyat'],
            data['toplam'], data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
            data.get('kdvli_toplam', data['toplam']),
            data.get('tevkifat_orani', '0'), data.get('tevkifat_tutar', 0),
            data.get('tevkifatsiz_kdv', 0), data.get('aciklama', ''),
            data.get('belge_no', ''),
            now,
        ))
        hareket_id = cur.fetchone()['id']
        _log_hareket(conn, hareket_id, 'EKLEME', json.dumps(data, ensure_ascii=False))
        return hareket_id


def update_hareket(id, data):
    with get_db() as conn:
        old = conn.execute('SELECT * FROM hareketler WHERE id=?', (id,)).fetchone()
        old_dict = dict(old) if old else {}
        conn.execute('''
            UPDATE hareketler SET tarih=?, firma_kod=?, firma_ad=?, tur=?, urun_kod=?, urun_ad=?,
                miktar=?, birim_fiyat=?, toplam=?, kdv_orani=?, kdv_tutar=?, kdvli_toplam=?,
                tevkifat_orani=?, tevkifat_tutar=?, tevkifatsiz_kdv=?, aciklama=?, belge_no=?
            WHERE id=?
        ''', (
            data['tarih'], data['firma_kod'], data['firma_ad'], data['tur'],
            data['urun_kod'], data['urun_ad'], data['miktar'], data['birim_fiyat'],
            data['toplam'], data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
            data.get('kdvli_toplam', data['toplam']),
            data.get('tevkifat_orani', '0'), data.get('tevkifat_tutar', 0),
            data.get('tevkifatsiz_kdv', 0), data.get('aciklama', ''),
            data.get('belge_no', ''),
            id
        ))
        detay = json.dumps({'eski': old_dict, 'yeni': data}, ensure_ascii=False, default=str)
        _log_hareket(conn, id, 'DUZENLEME', detay)


def delete_hareket(id):
    with get_db() as conn:
        old = conn.execute('SELECT * FROM hareketler WHERE id=?', (id,)).fetchone()
        old_dict = dict(old) if old else {}
        conn.execute('DELETE FROM hareketler WHERE id=?', (id,))
        _log_hareket(conn, id, 'SILME', json.dumps(old_dict, ensure_ascii=False, default=str))


def _log_hareket(conn, hareket_id, islem, detay=''):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        INSERT INTO hareket_log (hareket_id, islem, tarih, detay)
        VALUES (?,?,?,?)
    ''', (hareket_id, islem, now, detay))
