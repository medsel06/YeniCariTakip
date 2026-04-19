"""Cari hesap islemleri"""
from db import get_db
from services.audit_service import log_action_conn


def get_firma_list():
    with get_db() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM firmalar ORDER BY ad').fetchall()]


def get_firma(kod):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM firmalar WHERE kod=?', (kod,)).fetchone()
        return dict(r) if r else None


def add_firma(data):
    with get_db() as conn:
        conn.execute(
            '''
            INSERT INTO firmalar
            (kod, ad, tel, adres, vkn_tckn, nace, is_alani, email, risk_limiti)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT (kod) DO UPDATE SET
                ad=EXCLUDED.ad, tel=EXCLUDED.tel, adres=EXCLUDED.adres,
                vkn_tckn=EXCLUDED.vkn_tckn, nace=EXCLUDED.nace,
                is_alani=EXCLUDED.is_alani, email=EXCLUDED.email,
                risk_limiti=EXCLUDED.risk_limiti
            ''',
            (
                data['kod'],
                data['ad'],
                data.get('tel', ''),
                data.get('adres', ''),
                data.get('vkn_tckn', ''),
                data.get('nace', ''),
                data.get('is_alani', ''),
                data.get('email', ''),
                float(data.get('risk_limiti', 0) or 0),
            )
        )
        log_action_conn(
            conn, 'CREATE', 'firmalar', data.get('kod', ''), new_data=data,
            detail=f"Firma eklendi: {data.get('kod', '')} - {data.get('ad', '')}"
        )


def update_firma(kod, data):
    with get_db() as conn:
        old_row = conn.execute('SELECT * FROM firmalar WHERE kod=?', (kod,)).fetchone()
        old_data = dict(old_row) if old_row else {}
        conn.execute(
            '''
            UPDATE firmalar
            SET ad=?, tel=?, adres=?, vkn_tckn=?, nace=?, is_alani=?, email=?, risk_limiti=?
            WHERE kod=?
            ''',
            (
                data['ad'],
                data.get('tel', ''),
                data.get('adres', ''),
                data.get('vkn_tckn', ''),
                data.get('nace', ''),
                data.get('is_alani', ''),
                data.get('email', ''),
                float(data.get('risk_limiti', 0) or 0),
                kod,
            )
        )
        log_action_conn(
            conn, 'UPDATE', 'firmalar', kod, old_data=old_data, new_data=data,
            detail=f"Firma guncellendi: {kod}"
        )


def delete_firma(kod):
    with get_db() as conn:
        old_row = conn.execute('SELECT * FROM firmalar WHERE kod=?', (kod,)).fetchone()
        old_data = dict(old_row) if old_row else {}
        conn.execute('DELETE FROM firmalar WHERE kod=?', (kod,))
        log_action_conn(
            conn, 'DELETE', 'firmalar', kod, old_data=old_data,
            detail=f"Firma silindi: {kod}"
        )


def generate_firma_kod():
    """F001, F002 ... seklinde otomatik firma kodu uretir."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT kod FROM firmalar WHERE kod LIKE 'F%' ORDER BY CAST(SUBSTRING(kod FROM 2) AS INTEGER) DESC LIMIT 1"
        ).fetchone()
        if row and row['kod']:
            try:
                num = int(str(row['kod'])[1:]) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        return f'F{num:03d}'


def get_firma_risk_durumu(firma_kod):
    """Firmanin risk limiti ve mevcut bakiye durumunu dondur."""
    with get_db() as conn:
        firma = conn.execute('SELECT risk_limiti FROM firmalar WHERE kod=?', (firma_kod,)).fetchone()
        if not firma:
            return {'risk_limiti': 0, 'bakiye': 0, 'risk_yuzdesi': 0, 'limit_asimi': False}
        limit = float(firma['risk_limiti'] or 0)
        if limit <= 0:
            return {'risk_limiti': 0, 'bakiye': 0, 'risk_yuzdesi': 0, 'limit_asimi': False}
        # Bakiye hesapla (alacak = pozitif, borc = negatif)
        h = conn.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END),0) -
                COALESCE(SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END),0) AS net
            FROM hareketler WHERE firma_kod=?
        ''', (firma_kod,)).fetchone()
        k = conn.execute('''
            SELECT
                COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar ELSE 0 END),0) -
                COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END),0) AS net
            FROM kasa WHERE firma_kod=?
        ''', (firma_kod,)).fetchone()
        bakiye = float(h['net'] or 0) - float(k['net'] or 0)
        risk_yuzde = (bakiye / limit * 100) if limit > 0 else 0
        return {
            'risk_limiti': limit,
            'bakiye': bakiye,
            'risk_yuzdesi': round(risk_yuzde, 1),
            'limit_asimi': bakiye > limit,
        }


def get_risk_uyarilari():
    """Risk limiti tanimli tum firmalarin risk durumu. Dashboard ve raporlar icin."""
    with get_db() as conn:
        firmalar = conn.execute('SELECT kod, ad, risk_limiti FROM firmalar WHERE risk_limiti > 0 ORDER BY ad').fetchall()
        if not firmalar:
            return []
        result = []
        for f in firmalar:
            kod = f['kod']
            limit = float(f['risk_limiti'] or 0)
            h = conn.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END),0) -
                    COALESCE(SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END),0) AS net
                FROM hareketler WHERE firma_kod=?
            ''', (kod,)).fetchone()
            k = conn.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar ELSE 0 END),0) -
                    COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END),0) AS net
                FROM kasa WHERE firma_kod=?
            ''', (kod,)).fetchone()
            bakiye = float(h['net'] or 0) - float(k['net'] or 0)
            risk_yuzde = (bakiye / limit * 100) if limit > 0 else 0
            if risk_yuzde >= 50:
                result.append({
                    'kod': kod, 'ad': f['ad'], 'risk_limiti': limit,
                    'bakiye': bakiye, 'risk_yuzdesi': round(risk_yuzde, 1),
                    'limit_asimi': bakiye > limit,
                })
        result.sort(key=lambda x: x['risk_yuzdesi'], reverse=True)
        return result


def get_alacak_yaslandirma():
    """Firma bazli alacak yaslandirma raporu. 0-30, 31-60, 61-90, 90+ gun kovalari."""
    from datetime import datetime, timedelta
    bugun = datetime.now().date()
    with get_db() as conn:
        firmalar = conn.execute('SELECT kod, ad, risk_limiti FROM firmalar ORDER BY ad').fetchall()
        result = []
        for f in firmalar:
            kod = f['kod']
            # Toplam alacak (bakiye > 0 olan firmalar)
            h = conn.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END),0) -
                    COALESCE(SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END),0) AS net
                FROM hareketler WHERE firma_kod=?
            ''', (kod,)).fetchone()
            k = conn.execute('''
                SELECT
                    COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar ELSE 0 END),0) -
                    COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END),0) AS net
                FROM kasa WHERE firma_kod=?
            ''', (kod,)).fetchone()
            bakiye = float(h['net'] or 0) - float(k['net'] or 0)
            if bakiye <= 0.01:
                continue

            # Yaslandirma: satislari tarihe gore grupla
            satislar = conn.execute('''
                SELECT tarih, kdvli_toplam FROM hareketler
                WHERE firma_kod=? AND tur='SATIS' ORDER BY tarih
            ''', (kod,)).fetchall()

            b_0_30 = 0
            b_31_60 = 0
            b_61_90 = 0
            b_90_plus = 0
            kalan = bakiye  # Odenmemis tutar

            # En eski satislardan baslayarak kalan bakiyeyi dagit
            for s in satislar:
                if kalan <= 0:
                    break
                tutar = float(s['kdvli_toplam'] or 0)
                dagitilacak = min(tutar, kalan)
                try:
                    s_tarih = datetime.strptime(s['tarih'], '%Y-%m-%d').date()
                    gun = (bugun - s_tarih).days
                except Exception:
                    gun = 0
                if gun <= 30:
                    b_0_30 += dagitilacak
                elif gun <= 60:
                    b_31_60 += dagitilacak
                elif gun <= 90:
                    b_61_90 += dagitilacak
                else:
                    b_90_plus += dagitilacak
                kalan -= dagitilacak

            risk_limiti = float(f['risk_limiti'] or 0)
            risk_yuzde = (bakiye / risk_limiti * 100) if risk_limiti > 0 else 0
            result.append({
                'kod': kod, 'ad': f['ad'],
                'toplam': bakiye,
                'b_0_30': b_0_30, 'b_31_60': b_31_60,
                'b_61_90': b_61_90, 'b_90_plus': b_90_plus,
                'risk_limiti': risk_limiti,
                'risk_yuzdesi': round(risk_yuzde, 1),
            })
        result.sort(key=lambda x: x['toplam'], reverse=True)
        return result


def _safe_date_parts(yil, ay):
    """yil/ay'i kesinlikle int'e zorla, SQL injection onle."""
    if not yil or not ay:
        return None, None
    return int(yil), int(ay)


def get_cari_bakiye_list(yil=None, ay=None):
    """Tum firmalar icin bakiyeleri tek SQL ile getirir (N+1 query fix).
    yil/ay verilirse: devir (onceki donem) + secili ay hareketi + bakiye.
    """
    yil, ay = _safe_date_parts(yil, ay)
    if yil and ay:
        prefix = f'{yil:04d}-{ay:02d}'
        date_flt = f" AND tarih >= '{prefix}-01' AND tarih < '{prefix}-32'"
        devir_flt = f" AND tarih < '{prefix}-01'"
    else:
        date_flt = ''
        devir_flt = None

    # Secili donem
    sql = f"""
    SELECT
        f.kod, f.ad, f.tel,
        COALESCE(h.alis, 0) AS alis, COALESCE(h.satis, 0) AS satis,
        COALESCE(k.odeme, 0) AS odeme, COALESCE(k.tahsilat, 0) AS tahsilat,
        COALESCE(g.gg_gider, 0) AS gg_gider, COALESCE(g.gg_gelir, 0) AS gg_gelir
    FROM firmalar f
    LEFT JOIN (
        SELECT firma_kod,
            SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) AS alis,
            SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) AS satis
        FROM hareketler WHERE 1=1{date_flt} GROUP BY firma_kod
    ) h ON h.firma_kod = f.kod
    LEFT JOIN (
        SELECT firma_kod,
            SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END) AS odeme,
            SUM(CASE WHEN tur='GELIR' THEN tutar ELSE 0 END) AS tahsilat
        FROM kasa WHERE 1=1{date_flt} GROUP BY firma_kod
    ) k ON k.firma_kod = f.kod
    LEFT JOIN (
        SELECT firma_kod,
            SUM(CASE WHEN tur='GIDER' THEN toplam ELSE 0 END) AS gg_gider,
            SUM(CASE WHEN tur='GELIR' THEN toplam ELSE 0 END) AS gg_gelir
        FROM gelir_gider WHERE 1=1{date_flt} GROUP BY firma_kod
    ) g ON g.firma_kod = f.kod
    """
    # Devir (onceki donemler toplami)
    devir_map = {}
    with get_db() as conn:
        if devir_flt:
            devir_sql = f"""
            SELECT f.kod,
                COALESCE(h.alis, 0) AS alis, COALESCE(h.satis, 0) AS satis,
                COALESCE(k.odeme, 0) AS odeme, COALESCE(k.tahsilat, 0) AS tahsilat,
                COALESCE(g.gg_gider, 0) AS gg_gider, COALESCE(g.gg_gelir, 0) AS gg_gelir
            FROM firmalar f
            LEFT JOIN (
                SELECT firma_kod,
                    SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) AS alis,
                    SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) AS satis
                FROM hareketler WHERE 1=1{devir_flt} GROUP BY firma_kod
            ) h ON h.firma_kod = f.kod
            LEFT JOIN (
                SELECT firma_kod,
                    SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END) AS odeme,
                    SUM(CASE WHEN tur='GELIR' THEN tutar ELSE 0 END) AS tahsilat
                FROM kasa WHERE 1=1{devir_flt} GROUP BY firma_kod
            ) k ON k.firma_kod = f.kod
            LEFT JOIN (
                SELECT firma_kod,
                    SUM(CASE WHEN tur='GIDER' THEN toplam ELSE 0 END) AS gg_gider,
                    SUM(CASE WHEN tur='GELIR' THEN toplam ELSE 0 END) AS gg_gelir
                FROM gelir_gider WHERE 1=1{devir_flt} GROUP BY firma_kod
            ) g ON g.firma_kod = f.kod
            """
            for dr in conn.execute(devir_sql).fetchall():
                d_alis = float(dr['alis'] or 0) + float(dr['gg_gider'] or 0)
                d_satis = float(dr['satis'] or 0) + float(dr['gg_gelir'] or 0)
                d_odeme = float(dr['odeme'] or 0)
                d_tahsilat = float(dr['tahsilat'] or 0)
                devir = (d_satis - d_tahsilat) - (d_alis - d_odeme)
                if abs(devir) > 0.01:
                    devir_map[dr['kod']] = devir

        rows = conn.execute(sql).fetchall()
        result = []
        for r in rows:
            alis = float(r['alis'] or 0)
            satis = float(r['satis'] or 0)
            odeme = float(r['odeme'] or 0)
            tahsilat = float(r['tahsilat'] or 0)
            gg_gider = float(r['gg_gider'] or 0)
            gg_gelir = float(r['gg_gelir'] or 0)
            devir = devir_map.get(r['kod'], 0)
            donem_net = (satis + gg_gelir - tahsilat) - (alis + gg_gider - odeme)
            bakiye = devir + donem_net
            if alis or satis or odeme or tahsilat or gg_gider or gg_gelir or abs(devir) > 0.01:
                result.append({
                    'kod': r['kod'], 'ad': r['ad'], 'tel': r['tel'],
                    'alis': alis + gg_gider,
                    'satis': satis + gg_gelir,
                    'odeme': odeme, 'tahsilat': tahsilat,
                    'devir': devir, 'bakiye': bakiye,
                })
        result.sort(key=lambda x: abs(x['bakiye']), reverse=True)
        return result


def get_cari_ekstre(firma_kod, yil=None, ay=None):
    """Cari ekstre - gercek islem sirasinda (insertion order), bakiye kumulatif.
    yil/ay verilirse: onceki donem devir + secili ay hareketleri.
    """
    yil, ay = _safe_date_parts(yil, ay)
    if yil and ay:
        prefix = f'{yil:04d}-{ay:02d}'
        date_flt = f" AND tarih >= '{prefix}-01' AND tarih < '{prefix}-32'"
        devir_flt = f" AND tarih < '{prefix}-01'"
    else:
        date_flt = ''
        devir_flt = None

    sql = f"""
    SELECT * FROM (
        SELECT
            tarih,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            id AS ref_id,
            'H' AS src,
            tur AS tip,
            urun_ad,
            miktar,
            birim_fiyat,
            tevkifat_orani,
            NULL AS kategori,
            NULL AS ext_aciklama,
            NULL AS odeme_sekli,
            CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END AS borc,
            CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END AS alacak
        FROM hareketler
        WHERE firma_kod=?{date_flt}

        UNION ALL

        SELECT
            tarih,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            id AS ref_id,
            'G' AS src,
            tur AS tip,
            NULL AS urun_ad,
            0 AS miktar,
            0 AS birim_fiyat,
            NULL AS tevkifat_orani,
            kategori,
            aciklama AS ext_aciklama,
            NULL AS odeme_sekli,
            CASE WHEN tur='GIDER' THEN toplam ELSE 0 END AS borc,
            CASE WHEN tur='GELIR' THEN toplam ELSE 0 END AS alacak
        FROM gelir_gider
        WHERE firma_kod=?{date_flt}

        UNION ALL

        SELECT
            tarih,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            id AS ref_id,
            'K' AS src,
            tur AS tip,
            NULL AS urun_ad,
            0 AS miktar,
            0 AS birim_fiyat,
            NULL AS tevkifat_orani,
            NULL AS kategori,
            aciklama AS ext_aciklama,
            odeme_sekli,
            CASE WHEN tur='GELIR' THEN tutar ELSE 0 END AS borc,
            CASE WHEN tur='GIDER' THEN tutar ELSE 0 END AS alacak
        FROM kasa
        WHERE firma_kod=?{date_flt}
    )
    ORDER BY tarih, sort_ts, ref_id
    """
    with get_db() as conn:
        # Devir hesapla
        devir = 0
        if devir_flt:
            devir_sql = f"""
            SELECT COALESCE(SUM(alacak - borc), 0) AS devir FROM (
                SELECT CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END AS alacak,
                       CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END AS borc
                FROM hareketler WHERE firma_kod=?{devir_flt}
                UNION ALL
                SELECT CASE WHEN tur='GELIR' THEN toplam ELSE 0 END, CASE WHEN tur='GIDER' THEN toplam ELSE 0 END
                FROM gelir_gider WHERE firma_kod=?{devir_flt}
                UNION ALL
                SELECT CASE WHEN tur='GELIR' THEN tutar ELSE 0 END, CASE WHEN tur='GIDER' THEN tutar ELSE 0 END
                FROM kasa WHERE firma_kod=?{devir_flt}
            ) sub
            """
            devir = float(conn.execute(devir_sql, (firma_kod, firma_kod, firma_kod)).fetchone()['devir'] or 0)

        rows = conn.execute(sql, (firma_kod, firma_kod, firma_kod)).fetchall()

        items = []
        # Devir satiri kaldirildi (kullanici talebi) - bakiye sadece secili donemin toplamidir

        for r in rows:
            src = r['src']
            tip = r['tip']
            if src == 'H':
                tevk = r['tevkifat_orani'] or '0'
                tevk_notu = f' (Tevkifat: {tevk})' if tevk and tevk != '0' else ''
                ack = f"{'Alış' if tip=='ALIS' else 'Satış'}: {r['urun_ad']} - {r['miktar']} KG x {r['birim_fiyat']}{tevk_notu}"
            elif src == 'G':
                kat = r['kategori'] or ''
                acik = r['ext_aciklama'] or ''
                if tip == 'GIDER':
                    ack = f"Gider ({kat}): {acik}" if acik else f"Gider: {kat}"
                else:
                    ack = f"Gelir ({kat}): {acik}" if acik else f"Gelir: {kat}"
            else:  # 'K'
                ack = f"{'Ödeme' if tip=='GIDER' else 'Tahsilat'}: {r['odeme_sekli'] or ''} - {r['ext_aciklama'] or ''}"

            items.append({
                'tarih': r['tarih'],
                'aciklama': ack,
                'borc': float(r['borc'] or 0),
                'alacak': float(r['alacak'] or 0),
            })

        bakiye = 0
        for i in items:
            bakiye += i['alacak'] - i['borc']
            i['bakiye'] = bakiye
        return items


def get_firma_hareketler(firma_kod):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM hareketler WHERE firma_kod=? ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            (firma_kod,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_firma_kasa(firma_kod):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM kasa WHERE firma_kod=? ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            (firma_kod,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_firma_master_list():
    with get_db() as conn:
        rows = conn.execute(
            '''
            SELECT kod, ad, tel, adres, vkn_tckn, nace, is_alani, email, risk_limiti
            FROM firmalar
            ORDER BY ad
            '''
        ).fetchall()
        return [dict(r) for r in rows]


def get_firma_cekler(firma_kod):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM cekler WHERE firma_kod=? ORDER BY vade_tarih DESC, id DESC',
            (firma_kod,)
        ).fetchall()
        return [dict(r) for r in rows]
