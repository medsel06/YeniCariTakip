"""Stok islemleri"""
from db import get_db
from services.audit_service import log_action_conn


def get_stok_list():
    sql = """
    SELECT
        u.kod, u.ad, u.kategori, u.birim,
        COALESCE(h.alis, 0) AS alis,
        COALESCE(h.satis, 0) AS satis,
        COALESCE(h.alis_tutar, 0) AS alis_tutar,
        COALESCE(h.satis_tutar, 0) AS satis_tutar,
        COALESCE(ug.toplam, 0) AS uretim_girdi,
        COALESCE(uc.toplam, 0) AS uretim_cikti
    FROM urunler u
    LEFT JOIN (
        SELECT urun_kod,
            SUM(CASE WHEN tur='ALIS' THEN miktar ELSE 0 END) AS alis,
            SUM(CASE WHEN tur='SATIS' THEN miktar ELSE 0 END) AS satis,
            SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) AS alis_tutar,
            SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) AS satis_tutar
        FROM hareketler GROUP BY urun_kod
    ) h ON h.urun_kod = u.kod
    LEFT JOIN (
        SELECT urun_kod, SUM(miktar) AS toplam FROM uretim_girdi GROUP BY urun_kod
    ) ug ON ug.urun_kod = u.kod
    LEFT JOIN (
        SELECT urun_kod, SUM(miktar) AS toplam FROM uretim_cikti GROUP BY urun_kod
    ) uc ON uc.urun_kod = u.kod
    ORDER BY u.kod
    """
    with get_db() as conn:
        rows = conn.execute(sql).fetchall()
        result = []
        for r in rows:
            alis = float(r['alis'])
            satis = float(r['satis'])
            ug = float(r['uretim_girdi'])
            uc = float(r['uretim_cikti'])
            net = alis + uc - satis - ug
            result.append({
                'kod': r['kod'], 'ad': r['ad'], 'kategori': r['kategori'], 'birim': r['birim'],
                'alis': alis, 'satis': satis, 'stok': net,
                'alis_tutar': float(r['alis_tutar']), 'satis_tutar': float(r['satis_tutar']),
                'uretim_girdi': ug, 'uretim_cikti': uc
            })
        return result


def get_urun_list():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM urunler ORDER BY ad').fetchall()]


def add_urun(data):
    with get_db() as conn:
        try:
            conn.execute(
                'INSERT INTO urunler (kod, ad, kategori, birim, desi_degeri) VALUES (?,?,?,?,?)',
                (data['kod'], data['ad'], data.get('kategori', '').strip(), data.get('birim', 'KG'), float(data.get('desi_degeri', 0) or 0))
            )
            log_action_conn(
                conn, 'CREATE', 'urunler', data.get('kod', ''), new_data=data,
                detail=f"Urun eklendi: {data.get('kod', '')} - {data.get('ad', '')}"
            )
        except Exception as e:
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                raise ValueError(f'Bu urun kodu zaten mevcut: {data["kod"]}')
            raise


def update_urun(kod, data):
    with get_db() as conn:
        old_row = conn.execute('SELECT * FROM urunler WHERE kod=?', (kod,)).fetchone()
        old_data = dict(old_row) if old_row else {}
        conn.execute(
            'UPDATE urunler SET ad=?, kategori=?, birim=?, desi_degeri=? WHERE kod=?',
            (data['ad'], data.get('kategori', ''), data.get('birim', 'KG'), float(data.get('desi_degeri', 0) or 0), kod)
        )
        log_action_conn(
            conn, 'UPDATE', 'urunler', kod, old_data=old_data, new_data=data,
            detail=f"Urun guncellendi: {kod}"
        )


def delete_urun(kod):
    """Urun silme — Paket 8 soft-delete:
    - Hareket varsa pasife al (aktif=0), gecmis korunur
    - Hareket yoksa fiziksel sil"""
    with get_db() as conn:
        old_row = conn.execute('SELECT * FROM urunler WHERE kod=?', (kod,)).fetchone()
        old_data = dict(old_row) if old_row else {}
        hareket_var = conn.execute(
            "SELECT COUNT(*) AS cnt FROM hareketler WHERE urun_kod=?", (kod,)
        ).fetchone()['cnt']
        if hareket_var > 0:
            conn.execute('UPDATE urunler SET aktif=0 WHERE kod=?', (kod,))
            log_action_conn(
                conn, 'UPDATE', 'urunler', kod, old_data=old_data, new_data={'aktif': 0},
                detail=f"Urun pasife alindi (hareket var): {kod}"
            )
            return {'mode': 'pasif', 'hareket_sayisi': hareket_var}
        conn.execute('DELETE FROM urunler WHERE kod=?', (kod,))
        log_action_conn(
            conn, 'DELETE', 'urunler', kod, old_data=old_data,
            detail=f"Urun silindi: {kod}"
        )
        return {'mode': 'silindi'}


def reactivate_urun(kod):
    """Pasife alinmis urunu tekrar aktif et."""
    with get_db() as conn:
        conn.execute('UPDATE urunler SET aktif=1 WHERE kod=?', (kod,))


def get_urun_stok(urun_kod):
    """Tek bir urunun stok bilgilerini dondurur"""
    with get_db() as conn:
        u = conn.execute('SELECT * FROM urunler WHERE kod=?', (urun_kod,)).fetchone()
        if not u:
            return None
        row = conn.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN tur='ALIS' THEN miktar ELSE 0 END),0) as alis,
                COALESCE(SUM(CASE WHEN tur='SATIS' THEN miktar ELSE 0 END),0) as satis,
                COALESCE(SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END),0) as alis_tutar,
                COALESCE(SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END),0) as satis_tutar
            FROM hareketler WHERE urun_kod=?
        ''', (urun_kod,)).fetchone()
        ug = conn.execute(
            'SELECT COALESCE(SUM(miktar),0) FROM uretim_girdi WHERE urun_kod=?', (urun_kod,)
        ).fetchone()[0]
        uc = conn.execute(
            'SELECT COALESCE(SUM(miktar),0) FROM uretim_cikti WHERE urun_kod=?', (urun_kod,)
        ).fetchone()[0]
        net = row['alis'] + uc - row['satis'] - ug
        return {
            'kod': u['kod'], 'ad': u['ad'], 'kategori': u['kategori'], 'birim': u['birim'],
            'alis': row['alis'], 'satis': row['satis'], 'stok': net,
            'alis_tutar': row['alis_tutar'], 'satis_tutar': row['satis_tutar'],
            'uretim_girdi': ug, 'uretim_cikti': uc
        }


def get_urun_hareketleri(urun_kod):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM hareketler WHERE urun_kod=? ORDER BY tarih DESC, id DESC',
            (urun_kod,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_urun_uretim_hareketleri(urun_kod):
    with get_db() as conn:
        girdiler = conn.execute(
            '''SELECT ug.*, u.tarih, u.aciklama as uretim_aciklama, 'GIRDI' as tip
               FROM uretim_girdi ug JOIN uretim u ON ug.uretim_id=u.id
               WHERE ug.urun_kod=? ORDER BY u.tarih DESC''',
            (urun_kod,)
        ).fetchall()
        ciktilar = conn.execute(
            '''SELECT uc.*, u.tarih, u.aciklama as uretim_aciklama, 'CIKTI' as tip
               FROM uretim_cikti uc JOIN uretim u ON uc.uretim_id=u.id
               WHERE uc.urun_kod=? ORDER BY u.tarih DESC''',
            (urun_kod,)
        ).fetchall()
        result = [dict(r) for r in girdiler] + [dict(r) for r in ciktilar]
        result.sort(key=lambda x: x.get('tarih') or '', reverse=True)
        return result


def generate_urun_kod():
    """URN-001, URN-002, ... seklinde otomatik kod uretir"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT kod FROM urunler WHERE kod LIKE 'URN-%' ORDER BY kod DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                num = int(row['kod'].split('-')[1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'URN-{num:03d}'


def get_kategori_list():
    """Mevcut kategorileri dondurur"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT kategori FROM urunler WHERE kategori IS NOT NULL AND kategori != '' ORDER BY kategori"
        ).fetchall()
        return [r['kategori'] for r in rows]
