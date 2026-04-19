"""Personel maas/mesai/avans islemleri"""
from datetime import datetime
from db import get_db
from services.gelir_gider_service import _add_gelir_gider_conn
from services.kasa_service import _add_kasa_conn


def get_personel_list():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM personel ORDER BY durum, ad').fetchall()
        return [dict(r) for r in rows]


def get_aktif_personel():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM personel WHERE durum='AKTIF' ORDER BY ad").fetchall()
        return [dict(r) for r in rows]


def get_personel(pid):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM personel WHERE id=?', (pid,)).fetchone()
        return dict(r) if r else None


def add_personel(data):
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            INSERT INTO personel (ad, maas, ucret_tipi, durum, giris_tarih, cikis_tarih, telefon, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (
            data['ad'], float(data.get('maas', 0) or 0),
            data.get('ucret_tipi', 'NET'), data.get('durum', 'AKTIF'),
            data.get('giris_tarih', ''), data.get('cikis_tarih', ''),
            data.get('telefon', ''), now,
        ))


def update_personel(pid, data):
    with get_db() as conn:
        old = conn.execute('SELECT * FROM personel WHERE id=?', (pid,)).fetchone()
        if not old:
            return
        old_maas = float(old['maas'] or 0)
        new_maas = float(data.get('maas', 0) or 0)

        conn.execute('''
            UPDATE personel SET ad=?, maas=?, ucret_tipi=?, durum=?, giris_tarih=?, cikis_tarih=?, telefon=?
            WHERE id=?
        ''', (
            data['ad'], new_maas,
            data.get('ucret_tipi', 'NET'), data.get('durum', 'AKTIF'),
            data.get('giris_tarih', ''), data.get('cikis_tarih', ''),
            data.get('telefon', ''), pid,
        ))

        if old_maas != new_maas:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('''
                INSERT INTO personel_maas_gecmis (personel_id, eski_maas, yeni_maas, gecerlilik_tarih, aciklama, created_at)
                VALUES (?,?,?,?,?,?)
            ''', (pid, old_maas, new_maas, data.get('giris_tarih', now[:10]), 'Maas guncelleme', now))


def delete_personel(pid):
    with get_db() as conn:
        conn.execute('DELETE FROM personel_hareket WHERE personel_id=?', (pid,))
        conn.execute('DELETE FROM personel_aylik WHERE personel_id=?', (pid,))
        conn.execute('DELETE FROM personel_maas_gecmis WHERE personel_id=?', (pid,))
        conn.execute('DELETE FROM personel WHERE id=?', (pid,))


def ensure_donem_kayit(conn, personel_id, yil, ay, hafta=0):
    """Donem kaydi yoksa olustur. hafta=0 -> aylik, hafta>0 -> haftalik."""
    row = conn.execute(
        'SELECT id FROM personel_aylik WHERE personel_id=? AND yil=? AND ay=? AND hafta=?',
        (personel_id, yil, ay, hafta)
    ).fetchone()
    if row:
        return row['id']
    p = conn.execute('SELECT maas FROM personel WHERE id=?', (personel_id,)).fetchone()
    maas = float(p['maas'] or 0) if p else 0
    conn.execute('''
        INSERT INTO personel_aylik (personel_id, yil, ay, hafta, maas, mesai_saat, mesai_tutar, avans_toplam, hakedis, odenen, kalan, kilitli)
        VALUES (?,?,?,?,?,0,0,0,?,0,?,0)
    ''', (personel_id, yil, ay, hafta, maas, maas, maas))
    return conn.execute(
        'SELECT id FROM personel_aylik WHERE personel_id=? AND yil=? AND ay=? AND hafta=?',
        (personel_id, yil, ay, hafta)
    ).fetchone()['id']


# Geriye uyumluluk
def ensure_aylik_kayit(conn, personel_id, yil, ay):
    return ensure_donem_kayit(conn, personel_id, yil, ay, hafta=0)


def recalc_donem(conn, personel_id, yil, ay, hafta=0):
    """Donem yeniden hesapla. hafta=0 -> aylik, hafta>0 -> haftalik."""
    ensure_donem_kayit(conn, personel_id, yil, ay, hafta)
    row = conn.execute(
        'SELECT * FROM personel_aylik WHERE personel_id=? AND yil=? AND ay=? AND hafta=?',
        (personel_id, yil, ay, hafta)
    ).fetchone()
    if not row:
        return

    if int(row['kilitli'] or 0):
        return

    p = conn.execute('SELECT maas FROM personel WHERE id=?', (personel_id,)).fetchone()
    maas = float(p['maas'] or 0) if p else 0

    conn.execute('UPDATE personel_aylik SET maas=? WHERE personel_id=? AND yil=? AND ay=? AND hafta=?',
                 (maas, personel_id, yil, ay, hafta))

    mesai_row = conn.execute(
        "SELECT COALESCE(SUM(saat),0) as toplam_saat, COALESCE(SUM(tutar),0) as toplam_tutar "
        "FROM personel_hareket WHERE personel_id=? AND yil=? AND ay=? AND hafta=? AND tur='MESAI'",
        (personel_id, yil, ay, hafta)
    ).fetchone()
    mesai_saat = float(mesai_row['toplam_saat'] or 0)
    mesai_tutar = float(mesai_row['toplam_tutar'] or 0)

    avans_row = conn.execute(
        "SELECT COALESCE(SUM(tutar),0) as toplam FROM personel_hareket WHERE personel_id=? AND yil=? AND ay=? AND hafta=? AND tur='AVANS'",
        (personel_id, yil, ay, hafta)
    ).fetchone()
    avans_toplam = float(avans_row['toplam'] or 0)

    odeme_row = conn.execute(
        "SELECT COALESCE(SUM(tutar),0) as toplam FROM personel_hareket WHERE personel_id=? AND yil=? AND ay=? AND hafta=? AND tur='MAAS_ODEME'",
        (personel_id, yil, ay, hafta)
    ).fetchone()
    odenen = float(odeme_row['toplam'] or 0)

    hakedis = maas + mesai_tutar
    kalan = hakedis - avans_toplam - odenen

    conn.execute('''
        UPDATE personel_aylik
        SET mesai_saat=?, mesai_tutar=?, avans_toplam=?, hakedis=?, odenen=?, kalan=?
        WHERE personel_id=? AND yil=? AND ay=? AND hafta=?
    ''', (mesai_saat, mesai_tutar, avans_toplam, hakedis, odenen, kalan, personel_id, yil, ay, hafta))


# Geriye uyumluluk
def recalc_aylik(conn, personel_id, yil, ay):
    return recalc_donem(conn, personel_id, yil, ay, hafta=0)


def get_donem_ozet(yil, ay, hafta=0):
    """Donem ozeti. hafta=0 -> aylik, hafta>0 -> haftalik."""
    with get_db() as conn:
        aktif = conn.execute("SELECT * FROM personel WHERE durum='AKTIF' ORDER BY ad").fetchall()
        result = []
        for p in aktif:
            ensure_donem_kayit(conn, p['id'], yil, ay, hafta)
            recalc_donem(conn, p['id'], yil, ay, hafta)
        conn.commit()

        for p in aktif:
            donem = conn.execute(
                'SELECT * FROM personel_aylik WHERE personel_id=? AND yil=? AND ay=? AND hafta=?',
                (p['id'], yil, ay, hafta)
            ).fetchone()
            if donem:
                result.append({
                    'personel_id': p['id'],
                    'ad': p['ad'],
                    'maas': float(donem['maas'] or 0),
                    'mesai_saat': float(donem['mesai_saat'] or 0),
                    'mesai_tutar': float(donem['mesai_tutar'] or 0),
                    'avans_toplam': float(donem['avans_toplam'] or 0),
                    'hakedis': float(donem['hakedis'] or 0),
                    'odenen': float(donem['odenen'] or 0),
                    'kalan': float(donem['kalan'] or 0),
                    'kilitli': int(donem['kilitli'] or 0),
                })
        return result


# Geriye uyumluluk
def get_aylik_ozet(yil, ay):
    return get_donem_ozet(yil, ay, hafta=0)


def add_hareket(data):
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pid = data['personel_id']
        yil = data['yil']
        ay = data['ay']
        hafta = data.get('hafta', 0)
        tur = data['tur']

        ensure_donem_kayit(conn, pid, yil, ay, hafta)

        gelir_gider_id = None

        if tur in ('AVANS', 'MAAS_ODEME'):
            tutar = float(data.get('tutar', 0) or 0)
            p = conn.execute('SELECT ad FROM personel WHERE id=?', (pid,)).fetchone()
            p_ad = p['ad'] if p else ''

            if tur == 'AVANS':
                kat = 'Personel Maaş'
                aciklama = f"Avans: {p_ad} - {data.get('aciklama', '')}"
            else:
                kat = 'Personel Maaş'
                aciklama = f"Maaş Ödeme: {p_ad} - {data.get('aciklama', '')}"

            gelir_gider_id = _add_gelir_gider_conn(conn, {
                'tarih': data.get('tarih', now[:10]),
                'tur': 'GIDER',
                'kategori': kat,
                'aciklama': aciklama,
                'tutar': tutar,
                'kdv_orani': 0,
                'kdv_tutar': 0,
                'toplam': tutar,
                'odeme_sekli': data.get('odeme_sekli', 'NAKIT'),
            })

            _add_kasa_conn(conn, {
                'tarih': data.get('tarih', now[:10]),
                'firma_kod': '',
                'firma_ad': '',
                'tur': 'GIDER',
                'tutar': tutar,
                'odeme_sekli': data.get('odeme_sekli', 'NAKIT'),
                'aciklama': aciklama,
                'gelir_gider_id': gelir_gider_id,
            })

        conn.execute('''
            INSERT INTO personel_hareket (personel_id, yil, ay, hafta, tur, tutar, saat, tarih, aciklama, gelir_gider_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            pid, yil, ay, hafta, tur,
            float(data.get('tutar', 0) or 0),
            float(data.get('saat', 0) or 0),
            data.get('tarih', now[:10]),
            data.get('aciklama', ''),
            gelir_gider_id, now,
        ))

        recalc_donem(conn, pid, yil, ay, hafta)


def delete_hareket(hareket_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM personel_hareket WHERE id=?', (hareket_id,)).fetchone()
        if not row:
            return
        conn.execute('DELETE FROM personel_hareket WHERE id=?', (hareket_id,))
        recalc_donem(conn, row['personel_id'], row['yil'], row['ay'], int(row.get('hafta', 0) or 0))


def get_hareketler(personel_id, yil, ay, hafta=0):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM personel_hareket WHERE personel_id=? AND yil=? AND ay=? AND hafta=? ORDER BY tarih DESC, id DESC',
            (personel_id, yil, ay, hafta)
        ).fetchall()
        return [dict(r) for r in rows]


def get_son_mesai_ucreti(personel_id):
    """Personelin son mesai kaydindaki saat ucretini dondurur.
    Yoksa None doner, caller maas/225*1.5 hesabini yapar.
    """
    with get_db() as conn:
        r = conn.execute(
            "SELECT tutar, saat FROM personel_hareket "
            "WHERE personel_id=? AND tur='MESAI' AND saat > 0 "
            "ORDER BY COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') DESC, id DESC LIMIT 1",
            (personel_id,)
        ).fetchone()
        if not r:
            return None
        saat = float(r['saat'] or 0)
        if saat <= 0:
            return None
        return float(r['tutar'] or 0) / saat


def get_personel_dashboard_ozet():
    with get_db() as conn:
        aktif = conn.execute("SELECT COUNT(*) FROM personel WHERE durum='AKTIF'").fetchone()[0]
        toplam_maas = conn.execute("SELECT COALESCE(SUM(maas),0) FROM personel WHERE durum='AKTIF'").fetchone()[0]
        return {'aktif_sayi': aktif, 'aylik_maas': toplam_maas}


def get_rapor_ozet(yil, ay_baslangic=None, ay_bitis=None):
    """Personel bazli toplu rapor. Tum donemleri (hafta/ay) birlestirir.
    ay_baslangic/ay_bitis None ise tum yil.
    Returns: [{personel_id, ad, maas, toplam_mesai_saat, toplam_mesai_tutar,
               toplam_avans, toplam_hakedis, toplam_odenen, toplam_kalan, donemler:[...]}]
    """
    ay1 = ay_baslangic or 1
    ay2 = ay_bitis or 12
    with get_db() as conn:
        personeller = conn.execute("SELECT * FROM personel ORDER BY ad").fetchall()
        result = []
        for p in personeller:
            pid = p['id']
            # Tum donemleri topla (hafta farketmez)
            rows = conn.execute(
                "SELECT ay, hafta, maas, mesai_saat, mesai_tutar, avans_toplam, hakedis, odenen, kalan "
                "FROM personel_aylik WHERE personel_id=%s AND yil=%s AND ay>=%s AND ay<=%s ORDER BY ay, hafta",
                (pid, yil, ay1, ay2)
            ).fetchall()
            donemler = [dict(r) for r in rows]
            t_mesai_saat = sum(float(r.get('mesai_saat', 0) or 0) for r in donemler)
            t_mesai_tutar = sum(float(r.get('mesai_tutar', 0) or 0) for r in donemler)
            t_avans = sum(float(r.get('avans_toplam', 0) or 0) for r in donemler)
            t_hakedis = sum(float(r.get('hakedis', 0) or 0) for r in donemler)
            t_odenen = sum(float(r.get('odenen', 0) or 0) for r in donemler)
            t_kalan = sum(float(r.get('kalan', 0) or 0) for r in donemler)
            result.append({
                'personel_id': pid,
                'ad': p['ad'],
                'maas': float(p['maas'] or 0),
                'durum': p['durum'],
                'toplam_mesai_saat': t_mesai_saat,
                'toplam_mesai_tutar': t_mesai_tutar,
                'toplam_avans': t_avans,
                'toplam_hakedis': t_hakedis,
                'toplam_odenen': t_odenen,
                'toplam_kalan': t_kalan,
                'donemler': donemler,
            })
        return result
