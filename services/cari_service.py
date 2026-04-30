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
    """Firma silme — Paket 8 soft-delete:
    - Hareket varsa pasife al (aktif=0), gecmis korunur
    - Hareket yoksa fiziksel sil
    Mali muhasebe: hareketi olan firma kaydi asla silinmemeli."""
    with get_db() as conn:
        old_row = conn.execute('SELECT * FROM firmalar WHERE kod=?', (kod,)).fetchone()
        old_data = dict(old_row) if old_row else {}
        # Hareket var mi kontrol et
        _hv_row = conn.execute('''
            SELECT (
                (SELECT COUNT(*) FROM hareketler WHERE firma_kod=?) +
                (SELECT COUNT(*) FROM kasa WHERE firma_kod=?) +
                (SELECT COUNT(*) FROM gelir_gider WHERE firma_kod=?) +
                (SELECT COUNT(*) FROM cekler WHERE firma_kod=?)
            ) AS cnt
        ''', (kod, kod, kod, kod)).fetchone()
        hareket_var = int(_hv_row['cnt'] or 0) if _hv_row else 0
        if hareket_var > 0:
            # Soft-delete: pasife al
            conn.execute('UPDATE firmalar SET aktif=0 WHERE kod=?', (kod,))
            log_action_conn(
                conn, 'UPDATE', 'firmalar', kod, old_data=old_data, new_data={'aktif': 0},
                detail=f"Firma pasife alindi (hareket var, fiziksel silme yapilmadi): {kod}"
            )
            return {'mode': 'pasif', 'hareket_sayisi': hareket_var}
        # Hareket yoksa fiziksel sil
        conn.execute('DELETE FROM firmalar WHERE kod=?', (kod,))
        log_action_conn(
            conn, 'DELETE', 'firmalar', kod, old_data=old_data,
            detail=f"Firma silindi (hareket yok): {kod}"
        )
        return {'mode': 'silindi'}


def reactivate_firma(kod):
    """Pasife alinmis firmayi tekrar aktif et."""
    with get_db() as conn:
        old = conn.execute('SELECT * FROM firmalar WHERE kod=?', (kod,)).fetchone()
        if not old:
            return False
        conn.execute('UPDATE firmalar SET aktif=1 WHERE kod=?', (kod,))
        log_action_conn(
            conn, 'UPDATE', 'firmalar', kod, old_data=dict(old), new_data={'aktif': 1},
            detail=f"Firma tekrar aktif: {kod}"
        )
        return True


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
    """Firmanin risk limiti ve mevcut bakiye durumunu dondur — merkezi ledger uzerinden."""
    with get_db() as conn:
        firma = conn.execute('SELECT risk_limiti FROM firmalar WHERE kod=?', (firma_kod,)).fetchone()
        limit = float(firma['risk_limiti']) if firma and firma['risk_limiti'] else 0
        if limit <= 0:
            return {'risk_limiti': 0, 'bakiye': 0, 'risk_yuzdesi': 0, 'limit_asimi': False}
        # Cari liste ile ayni bakiye formulu (cek dahil)
        rows = get_cari_ledger(firma_kod=None)
        bakiye = 0
        for r in rows:
            if r['kod'] == firma_kod:
                bakiye = r['bakiye']
                break
        risk_yuzde = (bakiye / limit * 100) if limit > 0 else 0
        return {
            'risk_limiti': limit,
            'bakiye': bakiye,
            'risk_yuzdesi': round(risk_yuzde, 1),
            'limit_asimi': bakiye > limit,
        }


def get_risk_uyarilari():
    """Risk limiti tanimli tum firmalarin risk durumu — merkezi ledger uzerinden."""
    with get_db() as conn:
        risk_map = {}
        for f in conn.execute('SELECT kod, ad, risk_limiti FROM firmalar WHERE risk_limiti > 0').fetchall():
            risk_map[f['kod']] = (f['ad'], float(f['risk_limiti']))
    if not risk_map:
        return []

    bakiyeler = get_cari_ledger(firma_kod=None)
    result = []
    for b in bakiyeler:
        if b['kod'] not in risk_map:
            continue
        ad, limit = risk_map[b['kod']]
        bakiye = b['bakiye']
        risk_yuzde = (bakiye / limit * 100) if limit > 0 else 0
        if risk_yuzde >= 50:
            result.append({
                'kod': b['kod'], 'ad': ad, 'risk_limiti': limit,
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
    """yil/ay'i int'e normalize eder. Yil-only mod desteklenir.
    - yil ve ay verilirse: aylik mod
    - sadece yil verilirse: yillik mod (devir = onceki yil sonu)
    - hicbiri yoksa: tum zamanlar
    """
    yil = int(yil) if yil else None
    ay = int(ay) if ay else None
    if ay is not None and ay not in range(1, 13):
        ay = None
    return yil, ay


def _build_date_filter(yil, ay):
    """Donem icin (date_flt, devir_flt) ciftini uretir.
    Bos tarih ('') ve NULL kayitlar her durumda dislanir (mali dogruluk).
    """
    if yil and ay:
        prefix = f'{yil:04d}-{ay:02d}'
        date_flt = f" AND tarih IS NOT NULL AND tarih != '' AND tarih >= '{prefix}-01' AND tarih < '{prefix}-32'"
        devir_flt = f" AND tarih IS NOT NULL AND tarih != '' AND tarih < '{prefix}-01'"
    elif yil:
        # Yillik mod: devir = onceki yil sonu bakiyesi, donem = secili yil hareketleri
        date_flt = f" AND tarih IS NOT NULL AND tarih != '' AND tarih >= '{yil:04d}-01-01' AND tarih < '{yil + 1:04d}-01-01'"
        devir_flt = f" AND tarih IS NOT NULL AND tarih != '' AND tarih < '{yil:04d}-01-01'"
    else:
        # Tum zamanlar: devir kavrami yok
        date_flt = " AND tarih IS NOT NULL AND tarih != ''"
        devir_flt = None
    return date_flt, devir_flt


def get_cari_bakiye_list(yil=None, ay=None):
    """Tum firmalar icin cari bakiye listesi.
    Mali doğruluk için merkezi get_cari_ledger() üzerinde çalışır (Paket 4 — Codex önerisi).

    Cek/senet event'leri (ALINAN/VERILEN/CIRO) dahildir — eski kod cek'i göz ardı ediyordu.
    Çift sayım engeli: kasa.cek_id IS NOT NULL satırlar ledger'da gösterilmez.
    GG firma_kod IS NULL kayıtlar cariye etkilemez.

    Geriye uyumluluk için eski sayfalarda kullanılan key'ler korunur:
    - alis = saf alış (gg_gider hariç)  — eski kod karıştırıyordu
    - satis = saf satış (gg_gelir hariç)
    - odeme/tahsilat = sadece kasa
    - bakiye = devir + tüm ledger net (cek dahil)
    """
    return get_cari_ledger(firma_kod=None, yil=yil, ay=ay)


def _donem_label(yil, ay):
    """Donem etiketi: '2026 Yili', 'Nisan 2026', 'Tum Zamanlar'."""
    AY_AD = {1:'Ocak',2:'Subat',3:'Mart',4:'Nisan',5:'Mayis',6:'Haziran',
             7:'Temmuz',8:'Agustos',9:'Eylul',10:'Ekim',11:'Kasim',12:'Aralik'}
    if yil and ay:
        return f"{AY_AD.get(ay, ay)} {yil}"
    elif yil:
        return f"{yil} Yili"
    return "Tum Zamanlar"


def get_cari_ekstre(firma_kod, yil=None, ay=None, with_meta=False):
    """Cari ekstre - merkezi ledger uzerinden, cek event'leri dahil.
    - yil+ay: aylik mod, devir = onceki ay sonu
    - yil only: yillik mod, devir = onceki yil sonu
    - tumu: tum zamanlar, devir = 0

    with_meta=True ise dict doner: {donem_label, devir, satirlar, donem_borc, donem_alacak, kapanis_bakiye}
    with_meta=False (default) ise eski davranis: flat list (geriye uyumlu)
    """
    ledger = get_cari_ledger(firma_kod=firma_kod, yil=yil, ay=ay)

    # ledger.satirlar formatini eski format'a cevir (aciklama string olarak compose et)
    items = []
    for s in ledger['satirlar']:
        kaynak = s.get('kaynak')
        tip = s.get('tip')
        ack_raw = s.get('aciklama') or ''
        if kaynak == 'H':  # hareketler
            label = 'Alış' if tip == 'ALIS' else 'Satış'
            ack = f"{label}: {ack_raw}" if ack_raw else label
        elif kaynak == 'G':  # gelir_gider
            label = 'Gider' if tip == 'GIDER' else 'Gelir'
            ack = f"{label}: {ack_raw}" if ack_raw else label
        elif kaynak == 'K':  # kasa
            label = 'Ödeme' if tip == 'GIDER' else 'Tahsilat'
            ack = f"{label}: {ack_raw}" if ack_raw else label
        elif kaynak == 'C':  # cek
            if tip == 'CIRO':
                ack = f"Çek (ciro alındı): {ack_raw}"
            elif tip == 'ALINAN':
                ack = f"Alınan Çek: {ack_raw}"
            elif tip == 'VERILEN':
                ack = f"Verilen Çek: {ack_raw}"
            else:
                ack = f"Çek: {ack_raw}"
        else:
            ack = ack_raw

        items.append({
            'tarih': s.get('tarih'),
            'aciklama': ack,
            'borc': s.get('borc', 0),
            'alacak': s.get('alacak', 0),
            'bakiye': s.get('bakiye', 0),
            'tip': tip,
            'kaynak': kaynak,
        })

    if with_meta:
        return {
            'donem_label': ledger['donem_label'],
            'devir': ledger['devir'],
            'satirlar': items,
            'donem_borc': ledger['donem_borc'],
            'donem_alacak': ledger['donem_alacak'],
            'kapanis_bakiye': ledger['kapanis_bakiye'],
        }
    return items


def get_cari_ledger(firma_kod=None, yil=None, ay=None, include_devir=True):
    """Tek-kaynak cari defter. Tum cari hesaplari bunun ustune kurulur.

    Kaynaklar:
    - hareketler: ALIS (borc) / SATIS (alacak), kdvli_toplam
    - gelir_gider: GIDER (borc) / GELIR (alacak), toplam — sadece firma_kod doluysa
    - kasa: GELIR (alacak/tahsilat) / GIDER (borc/odeme), tutar — cek kapanis kayitlari haric
    - cekler: ALINAN (alacak/tahsilat) / VERILEN (borc/odeme) — portfoyde/tahsil/odendi
                CIRO_EDILDI -> ciro firmasina borc (ek satir)
                KARSILIKSIZ/IADE_EDILDI -> ters kayit

    Cift sayim engeli: kasa.cek_id IS NOT NULL satirlar ledger'da gosterilmez
    (cek tahsil/odeme kasa kaydi cariye 2. kez yansimaz, cari etki cekler tablosundan gelir).

    Args:
        firma_kod: None ise tum firmalar; verilirse o firmanin satirlari
        yil/ay: donem filtresi (3 modlu)
        include_devir: True ise donem oncesi devir hesaplanir

    Returns:
        firma_kod=None: liste, her item bir firma -> {
            kod, ad, tel, devir, donem_borc, donem_alacak, bakiye,
            alis, satis, odeme, tahsilat, gg_gider, gg_gelir, cek_alacak, cek_borc
        }
        firma_kod verilirse: dict {donem_label, devir, satirlar, donem_borc, donem_alacak, kapanis_bakiye}
    """
    yil, ay = _safe_date_parts(yil, ay)
    date_flt, devir_flt = _build_date_filter(yil, ay)

    firma_clause = "AND firma_kod=?" if firma_kod else ""
    firma_args = (firma_kod,) if firma_kod else ()

    # Donem hareketleri SQL: 4 kaynak union (cekler Paket 7'de tam olacak)
    # NOT: kasa'da cek kapanis kayitlari (cek_id IS NOT NULL) ledger'a girmez
    period_subqueries = [
        # 1. hareketler (ALIS/SATIS)
        f"""
        SELECT
            firma_kod,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            tarih, tur AS tip, 'H' AS kaynak, id AS ref_id,
            CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END AS borc,
            CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END AS alacak,
            urun_ad AS aciklama, NULL AS belge_no
        FROM hareketler WHERE 1=1 {firma_clause}{date_flt}
        """,
        # 2. gelir_gider (sadece firma_kod doluysa cariyi etkiler)
        f"""
        SELECT
            firma_kod,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            tarih, tur AS tip, 'G' AS kaynak, id AS ref_id,
            CASE WHEN tur='GIDER' THEN toplam ELSE 0 END AS borc,
            CASE WHEN tur='GELIR' THEN toplam ELSE 0 END AS alacak,
            COALESCE(aciklama, kategori) AS aciklama, NULL AS belge_no
        FROM gelir_gider
        WHERE firma_kod IS NOT NULL AND firma_kod != '' {firma_clause}{date_flt}
        """,
        # 3. kasa (cek kapanis satirlari haric — cift sayim engeli)
        f"""
        SELECT
            firma_kod,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts,
            tarih, tur AS tip, 'K' AS kaynak, id AS ref_id,
            CASE WHEN tur='GELIR' THEN tutar ELSE 0 END AS borc,
            CASE WHEN tur='GIDER' THEN tutar ELSE 0 END AS alacak,
            aciklama, NULL AS belge_no
        FROM kasa
        WHERE firma_kod IS NOT NULL AND firma_kod != '' AND cek_id IS NULL {firma_clause}{date_flt}
        """,
    ]

    # 4. cekler (event-based cari etkisi) — Paket 7'de tam aktif olur
    # ALINAN cek portfoyde/ciro/tahsil → tahsilat (cariye alacak); KARSILIKSIZ/IADE → ters kayit
    # VERILEN cek portfoyde/odendi → odeme (cariye borc); IADE → ters kayit
    # CIRO_EDILDI: ciro firmasina ek borc satiri (yeni firma)
    period_subqueries.append(f"""
        SELECT
            firma_kod,
            COALESCE(NULLIF(kesim_tarih, ''), vade_tarih, '') || ' 00:00:00.000000' AS sort_ts,
            COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) AS tarih,
            cek_turu AS tip, 'C' AS kaynak, id AS ref_id,
            CASE
              WHEN cek_turu='ALINAN' AND durum NOT IN ('KARSILIKSIZ','IADE_EDILDI') THEN tutar
              WHEN cek_turu='VERILEN' AND durum='IADE_EDILDI' THEN tutar
              ELSE 0
            END AS borc,
            CASE
              WHEN cek_turu='VERILEN' AND durum NOT IN ('IADE_EDILDI') THEN tutar
              WHEN cek_turu='ALINAN' AND durum IN ('KARSILIKSIZ','IADE_EDILDI') THEN tutar
              ELSE 0
            END AS alacak,
            cek_no AS aciklama, cek_no AS belge_no
        FROM cekler
        WHERE firma_kod IS NOT NULL AND firma_kod != '' {firma_clause}
          AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) IS NOT NULL
          AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) != ''
          {date_flt.replace('tarih', "COALESCE(NULLIF(kesim_tarih, ''), vade_tarih)")}
    """)

    # CIRO_EDILDI: ciro firmasina ek satir (alinan cek -> ciro firmasi borcunu kapatti)
    period_subqueries.append(f"""
        SELECT
            ciro_firma_kod AS firma_kod,
            COALESCE(NULLIF(kesim_tarih, ''), vade_tarih, '') || ' 00:00:00.000000' AS sort_ts,
            COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) AS tarih,
            'CIRO' AS tip, 'C' AS kaynak, id AS ref_id,
            0 AS borc,
            tutar AS alacak,
            cek_no AS aciklama, cek_no AS belge_no
        FROM cekler
        WHERE durum='CIRO_EDILDI'
          AND ciro_firma_kod IS NOT NULL AND ciro_firma_kod != ''
          {firma_clause.replace('firma_kod', 'ciro_firma_kod')}
          AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) IS NOT NULL
          AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) != ''
          {date_flt.replace('tarih', "COALESCE(NULLIF(kesim_tarih, ''), vade_tarih)")}
    """)

    period_sql = " UNION ALL ".join(period_subqueries)

    # Devir SQL: aynı kaynaklardan ama devir_flt ile
    devir_subqueries = []
    if devir_flt:
        # hareketler devir
        devir_subqueries.append(f"""
            SELECT firma_kod,
                   SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END
                       - CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) AS net
            FROM hareketler WHERE 1=1 {firma_clause}{devir_flt} GROUP BY firma_kod
        """)
        devir_subqueries.append(f"""
            SELECT firma_kod,
                   SUM(CASE WHEN tur='GELIR' THEN toplam ELSE 0 END
                       - CASE WHEN tur='GIDER' THEN toplam ELSE 0 END) AS net
            FROM gelir_gider WHERE firma_kod IS NOT NULL AND firma_kod != '' {firma_clause}{devir_flt} GROUP BY firma_kod
        """)
        devir_subqueries.append(f"""
            SELECT firma_kod,
                    SUM(CASE WHEN tur='GIDER' THEN tutar ELSE 0 END
                        - CASE WHEN tur='GELIR' THEN tutar ELSE 0 END) AS net
            FROM kasa WHERE firma_kod IS NOT NULL AND firma_kod != '' AND cek_id IS NULL {firma_clause}{devir_flt} GROUP BY firma_kod
        """)
        # cekler devir (durum'a gore net hesap)
        cek_devir_flt = devir_flt.replace('tarih', "COALESCE(NULLIF(kesim_tarih, ''), vade_tarih)")
        devir_subqueries.append(f"""
            SELECT firma_kod,
                    SUM(CASE
                        WHEN cek_turu='VERILEN' AND durum NOT IN ('IADE_EDILDI') THEN tutar
                        WHEN cek_turu='ALINAN' AND durum IN ('KARSILIKSIZ','IADE_EDILDI') THEN tutar
                        WHEN cek_turu='ALINAN' AND durum NOT IN ('KARSILIKSIZ','IADE_EDILDI') THEN -tutar
                        WHEN cek_turu='VERILEN' AND durum='IADE_EDILDI' THEN -tutar
                        ELSE 0
                    END) AS net
            FROM cekler
            WHERE firma_kod IS NOT NULL AND firma_kod != '' {firma_clause}
              AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) IS NOT NULL
              AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) != ''
              {cek_devir_flt}
            GROUP BY firma_kod
        """)
        devir_subqueries.append(f"""
            SELECT ciro_firma_kod AS firma_kod, SUM(tutar) AS net
            FROM cekler
            WHERE durum='CIRO_EDILDI'
              AND ciro_firma_kod IS NOT NULL AND ciro_firma_kod != ''
              {firma_clause.replace('firma_kod', 'ciro_firma_kod')}
              AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) IS NOT NULL
              AND COALESCE(NULLIF(kesim_tarih, ''), vade_tarih) != ''
              {cek_devir_flt}
            GROUP BY ciro_firma_kod
        """)

    with get_db() as conn:
        # Devir hesabi
        devir_map = {}
        if devir_subqueries and include_devir:
            devir_sql = f"""
                SELECT firma_kod, SUM(net) AS devir FROM (
                    {' UNION ALL '.join(devir_subqueries)}
                ) sub GROUP BY firma_kod
            """
            args = firma_args * 5  # 5 alt sorgu, her biri firma_kod parametresi (varsa)
            rows = conn.execute(devir_sql, args).fetchall()
            for r in rows:
                if r['firma_kod']:
                    devir_map[r['firma_kod']] = float(r['devir'] or 0)

        # Tek firma icin detayli ekstre
        if firma_kod:
            sql = f"SELECT * FROM ({period_sql}) ORDER BY tarih, sort_ts, ref_id"
            args = firma_args * 5
            satirlar = []
            devir = devir_map.get(firma_kod, 0.0)
            kumul = devir
            for r in conn.execute(sql, args).fetchall():
                kumul += float(r['alacak'] or 0) - float(r['borc'] or 0)
                satirlar.append({
                    'tarih': r['tarih'],
                    'tip': r['tip'],
                    'kaynak': r['kaynak'],
                    'belge_no': r['belge_no'],
                    'aciklama': r['aciklama'],
                    'borc': float(r['borc'] or 0),
                    'alacak': float(r['alacak'] or 0),
                    'bakiye': kumul,
                })
            return {
                'donem_label': _donem_label(yil, ay),
                'devir': devir,
                'satirlar': satirlar,
                'donem_borc': sum(s['borc'] for s in satirlar),
                'donem_alacak': sum(s['alacak'] for s in satirlar),
                'kapanis_bakiye': kumul,
            }

        # Tum firmalar icin GROUP BY
        sql = f"""
            SELECT firma_kod,
                SUM(CASE WHEN kaynak='H' AND tip='ALIS' THEN borc ELSE 0 END) AS alis,
                SUM(CASE WHEN kaynak='H' AND tip='SATIS' THEN alacak ELSE 0 END) AS satis,
                SUM(CASE WHEN kaynak='G' AND tip='GIDER' THEN borc ELSE 0 END) AS gg_gider,
                SUM(CASE WHEN kaynak='G' AND tip='GELIR' THEN alacak ELSE 0 END) AS gg_gelir,
                SUM(CASE WHEN kaynak='K' AND tip='GIDER' THEN alacak ELSE 0 END) AS odeme,
                SUM(CASE WHEN kaynak='K' AND tip='GELIR' THEN borc ELSE 0 END) AS tahsilat,
                SUM(CASE WHEN kaynak='C' THEN alacak ELSE 0 END) AS cek_alacak,
                SUM(CASE WHEN kaynak='C' THEN borc ELSE 0 END) AS cek_borc,
                SUM(borc) AS donem_borc,
                SUM(alacak) AS donem_alacak
            FROM ({period_sql}) sub
            WHERE firma_kod IS NOT NULL AND firma_kod != ''
            GROUP BY firma_kod
        """
        args = firma_args * 5
        result = []
        seen = set()
        for r in conn.execute(sql, args).fetchall():
            kod = r['firma_kod']
            seen.add(kod)
            devir = devir_map.get(kod, 0.0)
            donem_alacak = float(r['donem_alacak'] or 0)
            donem_borc = float(r['donem_borc'] or 0)
            bakiye = devir + donem_alacak - donem_borc
            # Firma master'dan ad/tel cek (firmalar tablosu silinmis olsa da kayit var ise)
            firma = conn.execute("SELECT ad, tel FROM firmalar WHERE kod=?", (kod,)).fetchone()
            result.append({
                'kod': kod,
                'ad': firma['ad'] if firma else f'(silinmis: {kod})',
                'tel': firma['tel'] if firma else '',
                'devir': devir,
                'alis': float(r['alis'] or 0),
                'satis': float(r['satis'] or 0),
                'gg_gider': float(r['gg_gider'] or 0),
                'gg_gelir': float(r['gg_gelir'] or 0),
                'odeme': float(r['odeme'] or 0),
                'tahsilat': float(r['tahsilat'] or 0),
                'cek_alacak': float(r['cek_alacak'] or 0),
                'cek_borc': float(r['cek_borc'] or 0),
                'donem_borc': donem_borc,
                'donem_alacak': donem_alacak,
                'bakiye': bakiye,
            })

        # Sadece devir'i olan ama donem hareketi olmayan firmalar (ledger'a eklenmemiş ama bakiye var)
        for kod, devir in devir_map.items():
            if kod and kod not in seen and abs(devir) > 0.005:
                firma = conn.execute("SELECT ad, tel FROM firmalar WHERE kod=?", (kod,)).fetchone()
                result.append({
                    'kod': kod,
                    'ad': firma['ad'] if firma else f'(silinmis: {kod})',
                    'tel': firma['tel'] if firma else '',
                    'devir': devir,
                    'alis': 0, 'satis': 0, 'gg_gider': 0, 'gg_gelir': 0,
                    'odeme': 0, 'tahsilat': 0, 'cek_alacak': 0, 'cek_borc': 0,
                    'donem_borc': 0, 'donem_alacak': 0,
                    'bakiye': devir,
                })

        # Bakiyesi/hareketi olmayan firmalari da ekle (sadece firma_kod=None modunda)
        result.sort(key=lambda x: abs(x['bakiye']), reverse=True)
        return result


def get_orphan_date_records():
    """Tum tablolarda bos/NULL tarihli kayitlari listeler — kullanici duzeltsin diye.
    Mali muhasebe doneminde 'tarih belirsiz' kayit olamaz."""
    result = {}
    with get_db() as conn:
        for tbl, col in [
            ('hareketler', 'tarih'),
            ('kasa', 'tarih'),
            ('gelir_gider', 'tarih'),
            ('cekler', 'kesim_tarih'),
            ('cekler', 'vade_tarih'),
        ]:
            try:
                rows = conn.execute(
                    f"SELECT * FROM {tbl} WHERE {col} IS NULL OR {col} = '' ORDER BY id DESC LIMIT 100"
                ).fetchall()
                if rows:
                    key = f'{tbl}.{col}' if tbl == 'cekler' else tbl
                    result[key] = [dict(r) for r in rows]
            except Exception:
                pass
    return result


def get_orphan_date_count():
    """Tum tablolarda bos tarihli kayit sayisi (dashboard widget icin)."""
    counts = {}
    with get_db() as conn:
        for tbl, col in [
            ('hareketler', 'tarih'),
            ('kasa', 'tarih'),
            ('gelir_gider', 'tarih'),
            ('cekler', 'kesim_tarih'),
            ('cekler', 'vade_tarih'),
        ]:
            try:
                cnt = conn.execute(
                    f"SELECT COUNT(*) AS c FROM {tbl} WHERE {col} IS NULL OR {col} = ''"
                ).fetchone()['c']
                if cnt > 0:
                    key = f'{tbl}.{col}' if tbl == 'cekler' else tbl
                    counts[key] = cnt
            except Exception:
                pass
    return counts


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
