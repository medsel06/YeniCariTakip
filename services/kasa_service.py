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
    """NAKIT kasa hareketleri (banka_hesap_id IS NULL). Banka hareketleri
    banka sayfasinda gosterilir."""
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM kasa WHERE banka_hesap_id IS NULL{flt} ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def get_kasa_bakiye(yil=None, ay=None):
    """NAKIT kasa bakiyesi (banka_hesap_id IS NULL). Banka hesaplari haric —
    onlar banka_service.get_banka_bakiye ile hesaplanir. Transfer bacaklari
    (is_transfer=1) nakit bakiyeyi etkiler cunku para gercekten girer/cikar."""
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        giris = conn.execute(f"SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE tur='GELIR' AND banka_hesap_id IS NULL{flt}", params).fetchone()[0]
        cikis = conn.execute(f"SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE tur='GIDER' AND banka_hesap_id IS NULL{flt}", params).fetchone()[0]
        return {'giris': giris, 'cikis': cikis, 'bakiye': giris - cikis}


def _add_kasa_conn(conn, data):
    """Acik bir conn uzerinde kasa kaydi ekler."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    cur = conn.execute('''
        INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama, cek_id, gelir_gider_id, banka, banka_hesap_id, kategori, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        RETURNING id
    ''', (
        data['tarih'], data.get('firma_kod', ''), data.get('firma_ad', ''),
        data['tur'], data['tutar'], data.get('odeme_sekli', ''), data.get('aciklama', ''),
        data.get('cek_id'), data.get('gelir_gider_id'), data.get('banka', ''),
        data.get('banka_hesap_id'),
        data.get('kategori', ''),
        now,
    ))
    return cur.fetchone()['id']


def get_kasa_kategoriler():
    """Kasa'da daha once kullanilmis benzersiz kategoriler (oneri listesi icin)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT kategori FROM kasa WHERE kategori IS NOT NULL AND kategori <> '' ORDER BY kategori"
        ).fetchall()
        return [r['kategori'] for r in rows]


def add_kasa(data):
    with get_db() as conn:
        return _add_kasa_conn(conn, data)


def update_kasa(id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE kasa SET tarih=?, firma_kod=?, firma_ad=?, tur=?, tutar=?, odeme_sekli=?, aciklama=?, banka_hesap_id=?, kategori=?
            WHERE id=?
        ''', (
            data['tarih'], data.get('firma_kod', ''), data.get('firma_ad', ''),
            data['tur'], data['tutar'], data.get('odeme_sekli', ''), data.get('aciklama', ''),
            data.get('banka_hesap_id'),
            data.get('kategori', ''),
            id
        ))


def delete_kasa(id):
    """Kasa silme — kaynak baglantisina gore kademeli davranir:
    - gelir_gider_id NOT NULL: ilgili gider/gelir kaydi DA silinir
      (ayni anda yaratildiklari varsayilir — pesin odeme akisi)
    - cek_id NOT NULL ve odeme_sekli='CEK' ve cek CIRO_EDILDI: cek portfoye geri doner
    - Diger durumlar: sadece kasa silinir (cariye atilmis gider'in odemesi gibi —
      odeme geri alinir, gider/cari borcu yerinde durur)
    """
    with get_db() as conn:
        rec = conn.execute('SELECT * FROM kasa WHERE id=?', (id,)).fetchone()
        if not rec:
            return

        # 1) Cek bagli ise — cirolanmis cek portfoye geri doner
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

        # 2) Gelir-gider bagli ise — gider/gelir satirini DA sil (kullanici karari)
        gg_id = rec['gelir_gider_id']
        if gg_id:
            conn.execute('DELETE FROM gelir_gider WHERE id=?', (gg_id,))

        # 3) Transfer bacagi ise — diger bacagi DA sil (atomik, Codex #7)
        tid = rec.get('transfer_id') if isinstance(rec, dict) else rec['transfer_id']
        if tid:
            conn.execute('DELETE FROM kasa WHERE transfer_id=?', (tid,))
            return

        # 4) Kasa kaydini sil
        conn.execute('DELETE FROM kasa WHERE id=?', (id,))


def get_kasa_silme_etkisi(id):
    """Kasa silinmeden once kullaniciya gosterilecek etki analizi.
    Donus dict: {ok: bool, kasa: dict, etkiler: [str], detay: dict}
    """
    with get_db() as conn:
        rec = conn.execute('SELECT * FROM kasa WHERE id=?', (id,)).fetchone()
        if not rec:
            return {'ok': False, 'kasa': None, 'etkiler': ['Kayit bulunamadi'], 'detay': {}}
        rec_d = dict(rec)
        etkiler = ['Kasa kaydi silinecek']
        detay = {}

        # Gelir-gider baglantisi
        gg_id = rec_d.get('gelir_gider_id')
        if gg_id:
            gg = conn.execute('SELECT * FROM gelir_gider WHERE id=?', (gg_id,)).fetchone()
            if gg:
                gg_d = dict(gg)
                tip_ad = 'Gider' if gg_d.get('tur') == 'GIDER' else 'Gelir'
                etkiler.append(f"⚠ Bagli {tip_ad} kaydi DA silinecek (gelir_gider id={gg_id})")
                detay['gelir_gider'] = gg_d

        # Cek baglantisi
        cek_id = rec_d.get('cek_id')
        if cek_id and rec_d.get('odeme_sekli') == 'CEK':
            cek = conn.execute('SELECT * FROM cekler WHERE id=?', (cek_id,)).fetchone()
            if cek:
                cek_d = dict(cek)
                if cek_d.get('durum') == 'CIRO_EDILDI':
                    etkiler.append(f"⚠ Bagli cek (No: {cek_d.get('cek_no', '-')}) PORTFOYE geri donecek")
                else:
                    etkiler.append(f"ℹ Bagli cek (No: {cek_d.get('cek_no', '-')}) — cek durumu degismeyecek")
                detay['cek'] = cek_d

        # Cari etkisi (firma'ya ait ise borc/alacak ortaya cikar)
        firma_kod = rec_d.get('firma_kod')
        tur = rec_d.get('tur')  # GELIR (tahsilat) veya GIDER (odeme)
        tutar = float(rec_d.get('tutar') or 0)
        if firma_kod and not gg_id:
            if tur == 'GELIR':
                etkiler.append(f"ℹ Cari etkisi: Tahsilat geri alinacak — firmanin borcu {tutar:,.2f} TL artar")
            elif tur == 'GIDER':
                etkiler.append(f"ℹ Cari etkisi: Odeme geri alinacak — firmaya borcunuz {tutar:,.2f} TL artar")

        return {'ok': True, 'kasa': rec_d, 'etkiler': etkiler, 'detay': detay}


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
            vade_tarih,
            COALESCE(grup_id, '') AS grup_id,
            'STOK' AS source,
            NULL::INTEGER AS kasa_id,
            NULL::INTEGER AS gelir_gider_id,
            NULL::INTEGER AS cek_id,
            NULL::TEXT AS odeme_sekli,
            NULL::TEXT AS banka,
            NULL::TEXT AS kategori,
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
            '' AS vade_tarih,
            '' AS grup_id,
            'KASA' AS source,
            id AS kasa_id,
            gelir_gider_id,
            cek_id,
            odeme_sekli,
            banka,
            kategori,
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
            # kasa kaynak etiketi (UI tooltipi/chip icin)
            if row.get('source') == 'KASA':
                if row.get('gelir_gider_id'):
                    row['kasa_kaynak'] = 'gelir_gider'
                elif row.get('cek_id'):
                    row['kasa_kaynak'] = 'cek'
                else:
                    row['kasa_kaynak'] = 'serbest'
            else:
                row['kasa_kaynak'] = None
            result.append(row)
        return result


# --- Islemler listesi: sunucu tarafli sayfalama ------------------------------
# Tarayiciya SADECE acik sayfadaki satirlar gider. Coklu kalem gruplari (grup_id)
# tek gorunum satiri oldugu icin sayfalama satir degil GRUP bazinda yapilir:
#   1) donem+tur+arama filtreli grup anahtarlarinin istenen sayfasi (SQL, LIMIT/OFFSET)
#   2) o gruplarin tum satirlari cekilir -> grupla_hareketler() ile birlestirilir.
# Ayni fonksiyon Kasa sayfasi ve v3 API icin de kullanilabilir.

_HRK_UNION_SQL = """
        SELECT
            CAST(id AS TEXT) AS unified_id,
            CASE WHEN COALESCE(grup_id, '') <> '' THEN 'G:' || grup_id ELSE CAST(id AS TEXT) END AS gkey,
            tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad, miktar, birim_fiyat, toplam,
            kdv_orani, kdv_tutar, kdvli_toplam, tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv,
            aciklama, belge_no, vade_tarih,
            COALESCE(grup_id, '') AS grup_id,
            'STOK' AS source,
            NULL::INTEGER AS kasa_id, NULL::INTEGER AS gelir_gider_id, NULL::INTEGER AS cek_id,
            NULL::TEXT AS odeme_sekli, NULL::TEXT AS banka, NULL::TEXT AS kategori,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts
        FROM hareketler WHERE 1=1{flt}
        UNION ALL
        SELECT
            'K-' || CAST(id AS TEXT) AS unified_id,
            'K-' || CAST(id AS TEXT) AS gkey,
            tarih, firma_kod, firma_ad,
            CASE WHEN tur='GELIR' THEN 'TAHSILAT' ELSE 'ODEME' END AS tur,
            '' AS urun_kod,
            'Kasa: ' || COALESCE(NULLIF(aciklama, ''), '-') AS urun_ad,
            0 AS miktar, 0 AS birim_fiyat, tutar AS toplam,
            0 AS kdv_orani, 0 AS kdv_tutar, tutar AS kdvli_toplam,
            '0' AS tevkifat_orani, 0 AS tevkifat_tutar, 0 AS tevkifatsiz_kdv,
            aciklama, '' AS belge_no, '' AS vade_tarih, '' AS grup_id,
            'KASA' AS source,
            id AS kasa_id, gelir_gider_id, cek_id, odeme_sekli, banka, kategori,
            COALESCE(NULLIF(created_at, ''), tarih || ' 00:00:00.000000') AS sort_ts
        FROM kasa WHERE 1=1{flt}
"""

# layout.normalize_search ile ayni etki: Turkce harfler ASCII'ye, sonra kucuk harf.
# translate() lower()'dan ONCE: 'I' -> 'I' -> 'i' (lower('I') bazi collation'larda
# 'i' + birlesik nokta uretir, LIKE eslesmez).
_HRK_NORM = "lower(translate(COALESCE({c}, ''), 'ÇĞİÖŞÜÂÎÛçğıöşüâîû', 'CGIOSUAIUcgiosuaiu'))"

# Siralanabilir kolon -> grup bazli SQL ifadesi (g CTE'si uzerinde)
# Metin kolonlari Turkce-normalize anahtarla siralanir (c/ç, s/ş, i/ı ayni kabul);
# aksi halde PG collation 'Arçimed'i 'Arz'dan SONRA koyar. NULLIF: bos/NULL degerler
# NULLS LAST ile her iki yonde de listenin SONUNA gider (kasa satirlarinin firmasi yok).
def _hrk_metin_sirala(c):
    return f"NULLIF({_HRK_NORM.format(c=c)}, '')"


_HRK_SORT_COLS = {
    'tarih': 'tarih',
    'belge_no': _hrk_metin_sirala('belge_no'), 'firma_ad': _hrk_metin_sirala('firma_ad'),
    'tur': _hrk_metin_sirala('tur'), 'urun_ad': _hrk_metin_sirala('urun_ad'),
    'miktar': 'miktar', 'birim_fiyat': 'birim_fiyat',
    'toplam': 'toplam', 'kdvli_toplam': 'kdvli_toplam', 'tevkifat_orani': 'tevkifat_orani',
}


def _hrk_row_postprocess(r):
    """get_hareketler ile ayni satir sekli (id, kasa_kaynak)."""
    row = dict(r)
    row['id'] = row.pop('unified_id')
    row.pop('sort_ts', None)
    row.pop('gkey', None)
    if row.get('source') == 'KASA':
        if row.get('gelir_gider_id'):
            row['kasa_kaynak'] = 'gelir_gider'
        elif row.get('cek_id'):
            row['kasa_kaynak'] = 'cek'
        else:
            row['kasa_kaynak'] = 'serbest'
    else:
        row['kasa_kaynak'] = None
    return row


def grupla_hareketler(rows):
    """Ayni grup_id'li STOK satirlarini tek gorunum satirinda birlestir (kalemler ile).
    Toplamlar gruba gore toplanir; tek kalemli/kasa satirlari aynen kalir.
    (pages/hareketler.py icindeki _grupla'nin servis katmanina tasinmis hali.)"""
    out = []
    gmap = {}
    for r in rows:
        gid = (r.get('grup_id') or '') if r.get('source') == 'STOK' else ''
        if not gid:
            out.append(r)
            continue
        kalem = {
            'urun_ad': r.get('urun_ad', ''),
            'miktar': r.get('miktar'),
            'birim_fiyat': r.get('birim_fiyat'),
            'kdvli_toplam': r.get('kdvli_toplam', 0),
        }
        if gid in gmap:
            p = gmap[gid]
            p['kalemler'].append(kalem)
            p['miktar'] = None
            p['birim_fiyat'] = None
            p['toplam'] = (p['toplam'] or 0) + (r.get('toplam') or 0)
            p['kdv_tutar'] = (p['kdv_tutar'] or 0) + (r.get('kdv_tutar') or 0)
            p['kdvli_toplam'] = (p['kdvli_toplam'] or 0) + (r.get('kdvli_toplam') or 0)
            p['tevkifat_tutar'] = (p['tevkifat_tutar'] or 0) + (r.get('tevkifat_tutar') or 0)
            p['urun_ad'] = f"{len(p['kalemler'])} kalem: {p['kalemler'][0]['urun_ad']} +{len(p['kalemler']) - 1}"
            continue
        p = dict(r)
        p['kalemler'] = [kalem]
        gmap[gid] = p
        out.append(p)
    return out


def get_hareketler_sayfa(yil=None, ay=None, q='', tur=None, sort_by='tarih', descending=True,
                         page=1, per_page=50):
    """Islemler listesinin TEK SAYFASI (stok + kasa birlesik, gruplu).
    q: arama (firma, urun, tur — Turkce duyarsiz), tur: ALIS/SATIS/TAHSILAT/ODEME veya None.
    Donus: {'rows': [gorunum satirlari], 'total': toplam gorunum satiri, 'page', 'per_page'}
    rows sekli get_hareketler()+grupla_hareketler() ile birebir aynidir."""
    flt, dparams = _date_filter(yil, ay)
    union_sql = _HRK_UNION_SQL.format(flt=flt)
    params = list(dparams) + list(dparams)

    # DIKKAT: psycopg2 parametreleri SQL METNINDEKI sirayla eslestirir. g CTE'sinde
    # once SELECT listesindeki arama (LIKE) parametreleri, sonra WHERE'deki tur gelir.
    q_norm = ''
    if q:
        from layout import normalize_search
        q_norm = normalize_search(q)
    if q_norm:
        like = '%' + q_norm.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        eslesen_sql = (
            f"BOOL_OR({_HRK_NORM.format(c='firma_ad')} LIKE %s OR "
            f"{_HRK_NORM.format(c='urun_ad')} LIKE %s OR "
            f"{_HRK_NORM.format(c='tur')} LIKE %s)"
        )
        params += [like, like, like]
    else:
        eslesen_sql = "TRUE"

    where_sql = ""
    if tur:
        where_sql = " WHERE tur = %s"
        params.append(tur)

    col = _HRK_SORT_COLS.get(sort_by or 'tarih', 'tarih')
    yon = 'DESC' if descending else 'ASC'
    # Ikincil anahtarlar eski siralamayla (tarih DESC, sort_ts DESC, unified_id DESC) ayni
    order_sql = f"{col} {yon} NULLS LAST, tarih DESC, sort_ts DESC, uid DESC"
    if col == 'tarih':
        order_sql = f"tarih {yon} NULLS LAST, sort_ts {yon}, uid {yon}"

    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(per_page or 50)
    except (TypeError, ValueError):
        per_page = 50
    if per_page <= 0:          # Quasar: 0 = "hepsi"
        per_page = 100000
    offset = (page - 1) * per_page

    keys_sql = f"""
    WITH u AS ({union_sql}),
    g AS (
        SELECT gkey,
               MAX(tarih) AS tarih, MAX(sort_ts) AS sort_ts, MAX(unified_id) AS uid,
               MAX(firma_ad) AS firma_ad, MAX(belge_no) AS belge_no, MAX(tur) AS tur,
               MIN(urun_ad) AS urun_ad, SUM(miktar) AS miktar, SUM(birim_fiyat) AS birim_fiyat,
               SUM(toplam) AS toplam, SUM(kdvli_toplam) AS kdvli_toplam,
               MAX(tevkifat_orani) AS tevkifat_orani,
               {eslesen_sql} AS eslesen
        FROM u{where_sql}
        GROUP BY gkey
    )
    SELECT gkey, COUNT(*) OVER () AS total
    FROM g WHERE eslesen
    ORDER BY {order_sql}
    LIMIT %s OFFSET %s
    """
    with get_db() as conn:
        key_rows = conn.execute(keys_sql, params + [per_page, offset]).fetchall()
        if key_rows:
            total = int(key_rows[0]['total'])
        else:
            # Sayfa bos (orn. son sayfadan sonrasi) — toplami ayri say
            cnt_sql = f"""
            WITH u AS ({union_sql}),
            g AS (SELECT gkey, {eslesen_sql} AS eslesen FROM u{where_sql} GROUP BY gkey)
            SELECT COUNT(*) AS n FROM g WHERE eslesen
            """
            total = int(conn.execute(cnt_sql, params).fetchone()['n'])
            return {'rows': [], 'total': total, 'page': page, 'per_page': per_page}

        keys = [k['gkey'] for k in key_rows]
        rows_sql = f"""
        WITH u AS ({union_sql})
        SELECT * FROM u WHERE gkey IN %s
        ORDER BY tarih DESC, sort_ts DESC, unified_id DESC
        """
        raw = conn.execute(rows_sql, list(dparams) + list(dparams) + [tuple(keys)]).fetchall()

    # Satirlari grup anahtarina gore topla, gorunum satirlarini SQL'deki sayfa sirasinda dizi
    by_key = {}
    for r in raw:
        by_key.setdefault(r['gkey'], []).append(_hrk_row_postprocess(r))
    rows = []
    for k in keys:
        grp = grupla_hareketler(by_key.get(k, []))
        rows.extend(grp)
    return {'rows': rows, 'total': total, 'page': page, 'per_page': per_page}


def get_hareket_by_id(id):
    with get_db() as conn:
        r = conn.execute('SELECT * FROM hareketler WHERE id=?', (id,)).fetchone()
        return dict(r) if r else None


def _insert_hareket(conn, data, created_at):
    cur = conn.execute('''
        INSERT INTO hareketler
            (tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad, miktar, birim_fiyat,
             toplam, kdv_orani, kdv_tutar, kdvli_toplam,
             tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv, aciklama, belge_no, vade_tarih,
             grup_id, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        RETURNING id
    ''', (
        data['tarih'], data['firma_kod'], data['firma_ad'], data['tur'],
        data['urun_kod'], data['urun_ad'], data['miktar'], data['birim_fiyat'],
        data['toplam'], data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
        data.get('kdvli_toplam', data['toplam']),
        data.get('tevkifat_orani', '0'), data.get('tevkifat_tutar', 0),
        data.get('tevkifatsiz_kdv', 0), data.get('aciklama', ''),
        data.get('belge_no', ''), data.get('vade_tarih', ''),
        data.get('grup_id', ''),
        created_at,
    ))
    hareket_id = cur.fetchone()['id']
    _log_hareket(conn, hareket_id, 'EKLEME', json.dumps(data, ensure_ascii=False))
    return hareket_id


def _update_hareket_conn(conn, id, data):
    old = conn.execute('SELECT * FROM hareketler WHERE id=?', (id,)).fetchone()
    old_dict = dict(old) if old else {}
    conn.execute('''
        UPDATE hareketler SET tarih=?, firma_kod=?, firma_ad=?, tur=?, urun_kod=?, urun_ad=?,
            miktar=?, birim_fiyat=?, toplam=?, kdv_orani=?, kdv_tutar=?, kdvli_toplam=?,
            tevkifat_orani=?, tevkifat_tutar=?, tevkifatsiz_kdv=?, aciklama=?, belge_no=?, vade_tarih=?,
            grup_id=?
        WHERE id=?
    ''', (
        data['tarih'], data['firma_kod'], data['firma_ad'], data['tur'],
        data['urun_kod'], data['urun_ad'], data['miktar'], data['birim_fiyat'],
        data['toplam'], data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
        data.get('kdvli_toplam', data['toplam']),
        data.get('tevkifat_orani', '0'), data.get('tevkifat_tutar', 0),
        data.get('tevkifatsiz_kdv', 0), data.get('aciklama', ''),
        data.get('belge_no', ''), data.get('vade_tarih', ''),
        # grup_id verilmediyse mevcut degeri koru (v3 API gibi eski cagiranlar bozulmasin)
        data.get('grup_id', old_dict.get('grup_id', '') or ''),
        id
    ))
    detay = json.dumps({'eski': old_dict, 'yeni': data}, ensure_ascii=False, default=str)
    _log_hareket(conn, id, 'DUZENLEME', detay)


def add_hareket(data):
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        return _insert_hareket(conn, data, now)


def update_hareket(id, data):
    with get_db() as conn:
        _update_hareket_conn(conn, id, data)


def get_hareket_grup(grup_id):
    """Ayni islemin (grup) tum kalem satirlari."""
    if not grup_id:
        return []
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM hareketler WHERE grup_id=? ORDER BY id', (grup_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def save_hareket_grup(kalemler, silinen_idler=None):
    """Coklu kalemli islemi tek transaction'da kaydeder/gunceller.

    kalemler: hareket data dict listesi; 'id' dolu olan UPDATE, olmayan INSERT edilir.
    silinen_idler: duzenlemede cikarilan kalemlerin hareket id'leri (silinir).
    Birden fazla kalem varsa hepsine ortak grup_id atanir (mevcut yoksa uretilir);
    tek kalemli islem grup_id='' ile eski davranista kalir.
    Donus: grup_id ('' = tek kalem).
    """
    import uuid
    kalemler = [k for k in kalemler if k]
    grup_id = ''
    for k in kalemler:
        if k.get('grup_id'):
            grup_id = k['grup_id']
            break
    if len(kalemler) > 1 and not grup_id:
        grup_id = uuid.uuid4().hex
    if len(kalemler) <= 1:
        grup_id = ''
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        for hid in (silinen_idler or []):
            old = conn.execute('SELECT * FROM hareketler WHERE id=?', (hid,)).fetchone()
            conn.execute('DELETE FROM hareketler WHERE id=?', (hid,))
            _log_hareket(conn, hid, 'SILME',
                         json.dumps(dict(old) if old else {}, ensure_ascii=False, default=str))
        for k in kalemler:
            k = dict(k)
            k['grup_id'] = grup_id
            hid = k.pop('id', None)
            if hid:
                _update_hareket_conn(conn, hid, k)
            else:
                # Ayni created_at: grup kalemleri ekstre siralamasinda birlikte dursun
                _insert_hareket(conn, k, k.pop('created_at', None) or now)
    return grup_id


def delete_hareket_grup(grup_id):
    """Grubun tum kalemlerini tek transaction'da siler."""
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM hareketler WHERE grup_id=?', (grup_id,)).fetchall()
        for r in rows:
            conn.execute('DELETE FROM hareketler WHERE id=?', (r['id'],))
            _log_hareket(conn, r['id'], 'SILME', json.dumps(dict(r), ensure_ascii=False, default=str))


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
