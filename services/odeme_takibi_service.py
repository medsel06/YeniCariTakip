"""Ödeme/Tahsilat Takibi — vade planı (gider YARATMAZ).

Bir borç/alacak gerçek gider/satış/alış kaydıyla zaten doğmuştur. Bu modül
sadece "ne zaman ödenecek/tahsil edilecek" takvimini tutar. Ödeme yapılınca
kasa/banka hareketi oluşur (cari/kart kapanır), TEKRAR gider yazılmaz.

tip:    BORC (ödenecek) | ALACAK (tahsil edilecek)
kaynak: CARI | KART | VERGI | SGK | CEK | DIGER
durum:  ACIK | ODENDI | KISMI
"""
from datetime import datetime
from db import get_db


def list_odeme_takibi(durum=None, tip=None):
    sql = "SELECT * FROM odeme_takibi WHERE 1=1"
    params = []
    if durum:
        sql += " AND durum=?"; params.append(durum)
    if tip:
        sql += " AND tip=?"; params.append(tip)
    sql += " ORDER BY CASE WHEN durum='ODENDI' THEN 1 ELSE 0 END, vade_tarih, id"
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_ozet():
    """Acik borc/alacak toplamlari + bu hafta/gecmis vade."""
    bugun = datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        def _sum(tip, extra='', p=None):
            r = conn.execute(
                f"SELECT COALESCE(SUM(tutar-odenen),0) FROM odeme_takibi "
                f"WHERE tip=? AND durum!='ODENDI'{extra}", [tip] + (p or [])
            ).fetchone()
            return float(r[0] or 0)
        return {
            'acik_borc': _sum('BORC'),
            'acik_alacak': _sum('ALACAK'),
            'gecmis_borc': _sum('BORC', ' AND vade_tarih!=\'\' AND vade_tarih < ?', [bugun]),
        }


def _sum_by_firma(conn, where):
    """kasa tablosunda firma bazli tutar toplami -> {firma_kod: toplam}."""
    rows = conn.execute(
        f"SELECT firma_kod, COALESCE(SUM(tutar),0) AS t FROM kasa "
        f"WHERE firma_kod IS NOT NULL AND firma_kod != '' AND {where} GROUP BY firma_kod"
    ).fetchall()
    return {r['firma_kod']: float(r['t'] or 0) for r in rows}


def _cek_sum_by_firma(conn, where):
    """cekler tablosunda firma bazli tutar toplami -> {firma_kod: toplam}."""
    rows = conn.execute(
        f"SELECT firma_kod, COALESCE(SUM(tutar),0) AS t FROM cekler "
        f"WHERE firma_kod IS NOT NULL AND firma_kod != '' AND {where} GROUP BY firma_kod"
    ).fetchall()
    return {r['firma_kod']: float(r['t'] or 0) for r in rows}


def get_vadeli_cari():
    """Vadeli alis/satislari FIFO ile kapanma durumu hesaplayip dondurur.

    - Obligasyon: bir firmanin tum alis/satis hareketleri (pesin DAHIL), yon bazinda
      (ALIS=odenecek, SATIS=tahsil edilecek), vade->islem tarihi sirasinda.
    - Odeme havuzu (o yondeki kapanmalar):
        SATIS (tahsilat) = kasa GELIR (cek_id bos, transfer degil) + ALINAN cek (karsiliksiz/iade haric)
        ALIS  (odeme)    = kasa GIDER (cek_id bos, transfer degil) + VERILEN cek (iade haric)
    - Havuz, en eski (vade) hareketten baslayarak FIFO dagitilir. Pesin hareketler de
      havuzu tuketir (vade=islem tarihi sayilir) ki karisik calismada dogru sira cikar.
    - SADECE vade_tarih dolu hareketler 'takip edilen' olarak listelenir.
    - Cari bakiyeyi ETKILEMEZ; bu yalnizca turetilmis bir rapordur.
    """
    with get_db() as conn:
        hrows = conn.execute(
            "SELECT id, tarih, firma_kod, firma_ad, tur, urun_ad, "
            "       COALESCE(kdvli_toplam,0) AS tutar, COALESCE(NULLIF(vade_tarih,''),'') AS vade_tarih "
            "FROM hareketler "
            "WHERE firma_kod IS NOT NULL AND firma_kod != '' AND tur IN ('ALIS','SATIS') "
            "ORDER BY firma_kod, tur, COALESCE(NULLIF(vade_tarih,''), tarih), tarih, id"
        ).fetchall()

        havuz = {
            'SATIS': dict(_sum_by_firma(conn, "tur='GELIR' AND cek_id IS NULL AND COALESCE(is_transfer,0)=0")),
            'ALIS': dict(_sum_by_firma(conn, "tur='GIDER' AND cek_id IS NULL AND COALESCE(is_transfer,0)=0")),
        }
        # Cek ile kapanmalar
        for k, v in _cek_sum_by_firma(conn, "cek_turu='ALINAN' AND durum NOT IN ('KARSILIKSIZ','IADE_EDILDI')").items():
            havuz['SATIS'][k] = havuz['SATIS'].get(k, 0) + v
        for k, v in _cek_sum_by_firma(conn, "cek_turu='VERILEN' AND durum NOT IN ('IADE_EDILDI')").items():
            havuz['ALIS'][k] = havuz['ALIS'].get(k, 0) + v

        # FIFO dagitimi: kalan havuzu firma+yon bazinda takip et
        kalan_havuz = {'SATIS': {}, 'ALIS': {}}
        sonuc = []
        for r in hrows:
            tur = r['tur']
            fk = r['firma_kod']
            if fk not in kalan_havuz[tur]:
                kalan_havuz[tur][fk] = havuz[tur].get(fk, 0.0)
            tutar = float(r['tutar'] or 0)
            kapanan = min(kalan_havuz[tur][fk], tutar)
            if kapanan < 0:
                kapanan = 0
            kalan_havuz[tur][fk] -= kapanan
            # Sadece vadeli olanlari rapora ekle
            if not r['vade_tarih']:
                continue
            kalan = round(tutar - kapanan, 2)
            if kalan <= 0.01:
                durum = 'ODENDI'
            elif kapanan <= 0.01:
                durum = 'ACIK'
            else:
                durum = 'KISMI'
            sonuc.append({
                'kaynak': 'CARI',
                'kaynak_label': 'Vadeli ' + ('Satış' if tur == 'SATIS' else 'Alış'),
                'tip': 'ALACAK' if tur == 'SATIS' else 'BORC',
                'hareket_id': r['id'],
                'firma_kod': fk,
                'firma_ad': r['firma_ad'],
                'aciklama': r['urun_ad'] or '',
                'tutar': tutar,
                'odenen': round(kapanan, 2),
                'kalan': kalan,
                'vade_tarih': r['vade_tarih'],
                'durum': durum,
            })
        return sonuc


def get_cek_vadeleri():
    """Acik cek/senet vadelerini (salt-okunur) odeme takibi formatinda dondurur.
    ALINAN -> tahsil edilecek (ALACAK), VERILEN -> odenecek (BORC).
    Odeme buradan YAPILMAZ; cek modulunden yapilir."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, cek_no, evrak_tipi, cek_turu, firma_ad, COALESCE(tutar,0) AS tutar, vade_tarih, durum "
            "FROM cekler "
            "WHERE durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI') "
            "AND vade_tarih IS NOT NULL AND vade_tarih != '' "
            "ORDER BY vade_tarih, id"
        ).fetchall()
        out = []
        for r in rows:
            evrak = 'Senet' if r['evrak_tipi'] == 'SENET' else 'Çek'
            out.append({
                'kaynak': 'CEK',
                'kaynak_label': f"{evrak} ({'Alınan' if r['cek_turu'] == 'ALINAN' else 'Verilen'})",
                'tip': 'ALACAK' if r['cek_turu'] == 'ALINAN' else 'BORC',
                'cek_id': r['id'],
                'firma_kod': '',
                'firma_ad': r['firma_ad'],
                'aciklama': f"{evrak} No: {r['cek_no']}",
                'tutar': float(r['tutar'] or 0),
                'odenen': 0.0,
                'kalan': float(r['tutar'] or 0),
                'vade_tarih': r['vade_tarih'],
                'durum': 'ACIK',
            })
        return out


def add_odeme_takibi(data):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cur = conn.execute('''
            INSERT INTO odeme_takibi (tip, kaynak, firma_kod, firma_ad, banka_hesap_id,
                                      aciklama, tutar, odenen, vade_tarih, durum, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id
        ''', (
            data.get('tip', 'BORC'), data.get('kaynak', 'DIGER'),
            data.get('firma_kod', ''), data.get('firma_ad', ''),
            data.get('banka_hesap_id'), data.get('aciklama', ''),
            float(data.get('tutar', 0) or 0), float(data.get('odenen', 0) or 0),
            data.get('vade_tarih', ''), data.get('durum', 'ACIK'), now,
        ))
        return cur.fetchone()['id']


def update_odeme_takibi(rec_id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE odeme_takibi SET tip=?, kaynak=?, firma_kod=?, firma_ad=?, banka_hesap_id=?,
                                    aciklama=?, tutar=?, vade_tarih=? WHERE id=?
        ''', (
            data.get('tip', 'BORC'), data.get('kaynak', 'DIGER'),
            data.get('firma_kod', ''), data.get('firma_ad', ''),
            data.get('banka_hesap_id'), data.get('aciklama', ''),
            float(data.get('tutar', 0) or 0), data.get('vade_tarih', ''), rec_id,
        ))


def delete_odeme_takibi(rec_id):
    with get_db() as conn:
        # Odendi ise olusan kasa kaydini da sil
        rec = conn.execute("SELECT kasa_id FROM odeme_takibi WHERE id=?", (rec_id,)).fetchone()
        if rec and rec['kasa_id']:
            conn.execute("DELETE FROM kasa WHERE id=?", (rec['kasa_id'],))
        conn.execute("DELETE FROM odeme_takibi WHERE id=?", (rec_id,))


def ode(rec_id, tarih=None, tutar=None, banka_hesap_id=None):
    """Bir takip kaydini ode/tahsil et. Para hareketi (kasa) olusturur.
    BORC -> kasa GIDER (para cikar, cari/kart borc kapanir)
    ALACAK -> kasa GELIR (para girer, cari alacak kapanir)
    banka_hesap_id None ise nakit, dolu ise o banka/kart hesabi."""
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    tarih = tarih or datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        rec = conn.execute("SELECT * FROM odeme_takibi WHERE id=?", (rec_id,)).fetchone()
        if not rec:
            raise ValueError("Kayit bulunamadi")
        kalan = float(rec['tutar'] or 0) - float(rec['odenen'] or 0)
        odenecek = float(tutar) if tutar else kalan
        if odenecek <= 0:
            raise ValueError("Odenecek tutar gecersiz")
        kasa_tur = 'GIDER' if rec['tip'] == 'BORC' else 'GELIR'
        cur = conn.execute('''
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama,
                              banka_hesap_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?) RETURNING id
        ''', (
            tarih, rec['firma_kod'], rec['firma_ad'], kasa_tur, odenecek,
            'BANKA' if banka_hesap_id else 'NAKIT',
            f"Ödeme takibi: {rec['aciklama']}"[:200], banka_hesap_id, now_ts,
        ))
        kasa_id = cur.fetchone()['id']
        yeni_odenen = float(rec['odenen'] or 0) + odenecek
        yeni_durum = 'ODENDI' if yeni_odenen >= float(rec['tutar'] or 0) - 0.01 else 'KISMI'
        conn.execute(
            "UPDATE odeme_takibi SET odenen=?, durum=?, kasa_id=? WHERE id=?",
            (yeni_odenen, yeni_durum, kasa_id, rec_id))
        return kasa_id
