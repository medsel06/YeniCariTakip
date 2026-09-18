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

# Kategori normalize edilirken buyuk kalacak kisaltmalar (SGK -> Sgk olmasin)
_KATEGORI_KISALTMALAR = {'SGK', 'SSK', 'KDV', 'ÖTV', 'ÖİV', 'MTV', 'GVK', 'KKEG', 'TL'}


def _tr_kucuk(s):
    """Turkce kurallariyla kucuk harf (I->ı, İ->i)."""
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def _tr_buyuk(s):
    """Turkce kurallariyla buyuk harf (ı->I, i->İ)."""
    return s.replace('ı', 'I').replace('i', 'İ').upper()


def kategori_normalize(s):
    """Kategori metnini 'Ilk Harf Buyuk' formatina cevirir (Turkce kurallariyla).
    Ornek: 'İŞÇİLİK' -> 'İşçilik', 'KART NAKİT AVANS' -> 'Kart Nakit Avans'.
    Bilinen kisaltmalar (SGK, KDV...) tamamen buyuk kalir."""
    import re
    if not s:
        return s

    def _kelime(m):
        w = m.group(0)
        if _tr_buyuk(w) in _KATEGORI_KISALTMALAR:
            return _tr_buyuk(w)
        return _tr_buyuk(w[0]) + _tr_kucuk(w[1:])

    # Sadece harf dizilerini isle; bosluk / '/' gibi ayiraclar korunur
    return re.sub(r'[^\W\d_]+', _kelime, s, flags=re.UNICODE).strip()


# Kategori -> kucuk emoji ikon (dropdown gorunumunde). Bilinmeyenler icin varsayilan.
KATEGORI_IKON = {
    # Gelir
    'Fason İşçilik': '🧵', 'İşçilik': '🔨', 'Hurda Satış': '♻️',
    'Kira Geliri': '🏠', 'Komisyon': '🤝', 'Faiz': '📈',
    'Kur Farkı Geliri': '💱', 'Vade Farkı Geliri': '⏳',
    # Gider
    'Nakliye': '🚚', 'Ardiye': '📦', 'Kira': '🏠', 'Elektrik': '⚡',
    'Su': '💧', 'Doğalgaz': '🔥', 'Telefon': '📞', 'İnternet': '🌐',
    'Personel Maaş': '👷', 'Masraf': '💸', 'Kart Nakit Avans Komisyon': '💳',
    'SGK': '🏛️', 'Vergi': '🧾', 'Sigorta': '🛡️', 'Akaryakıt': '⛽',
    'Bakım/Onarım': '🔧', 'Kırtasiye': '✏️', 'Banka Masrafı': '🏦',
    'Damga Vergisi': '📜', 'Noter': '📝', 'Yemek/İkram': '🍽️',
    'Diğer': '📌',
}


def kategori_ikon(kat):
    """Kategori icin kucuk emoji ikon. Ozel/bilinmeyen kategoriler icin varsayilan etiket."""
    if not kat:
        return '🏷️'
    return KATEGORI_IKON.get(kat.strip(), '🏷️')


def get_kategori_kullanim(tur=None):
    """Kategorilerin kullanim sayisi (en cok kullanilan once). Donus: [(kategori, adet), ...]."""
    where = "kategori IS NOT NULL AND kategori != ''"
    params = []
    if tur in ('GELIR', 'GIDER'):
        where += " AND tur=?"
        params.append(tur)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT kategori, COUNT(*) AS adet FROM gelir_gider WHERE {where} "
            f"GROUP BY kategori ORDER BY adet DESC, kategori", params
        ).fetchall()
        return [(r['kategori'], r['adet']) for r in rows]


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


# Grubun tum kalemlerinde ortak olan (baslik) alanlar
BASLIK_ALANLAR = ('tarih', 'tur', 'aciklama', 'odeme_sekli', 'firma_kod', 'firma_ad',
                  'odeme_durumu', 'vade_tarih')


def _add_gelir_gider_conn(conn, data):
    """Acik bir conn uzerinde gelir_gider ekler. Icerideki baska islemlerle ayni transaction'da calisir.
    data['created_at'] verilirse kullanilir (grup kalemleri ayni zaman damgasini paylasir)."""
    now = data.get('created_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    cur = conn.execute('''
        INSERT INTO gelir_gider
            (tarih, tur, kategori, aciklama, tutar, kdv_orani, kdv_tutar, toplam, odeme_sekli,
             firma_kod, firma_ad, odeme_durumu, vade_tarih, created_at, grup_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        RETURNING id
    ''', (
        data['tarih'], data['tur'], kategori_normalize(data.get('kategori', '')),
        data.get('aciklama', ''), data['tutar'],
        data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
        data.get('toplam', data['tutar']),
        data.get('odeme_sekli', ''),
        data.get('firma_kod', ''), data.get('firma_ad', ''),
        data.get('odeme_durumu', 'ODENDI'),
        data.get('vade_tarih', ''),
        now,
        data.get('grup_id', '') or '',
    ))
    return cur.fetchone()['id']


def _update_gelir_gider_conn(conn, rec_id, data):
    conn.execute('''
        UPDATE gelir_gider
        SET tarih=?, tur=?, kategori=?, aciklama=?, tutar=?, kdv_orani=?, kdv_tutar=?, toplam=?, odeme_sekli=?,
            firma_kod=?, firma_ad=?, odeme_durumu=?, vade_tarih=?, grup_id=?
        WHERE id=?
    ''', (
        data['tarih'], data['tur'], kategori_normalize(data.get('kategori', '')),
        data.get('aciklama', ''), data['tutar'],
        data.get('kdv_orani', 0), data.get('kdv_tutar', 0),
        data.get('toplam', data['tutar']),
        data.get('odeme_sekli', ''),
        data.get('firma_kod', ''), data.get('firma_ad', ''),
        data.get('odeme_durumu', 'ODENDI'),
        data.get('vade_tarih', ''),
        data.get('grup_id', '') or '',
        rec_id,
    ))


def _kasa_aciklama(data, kalem_sayisi=1):
    """Bagli kasa kaydinin aciklamasi: 'GG: <aciklama | kategori (+n)>'."""
    metin = data.get('aciklama', '') or data.get('kategori', '')
    if not data.get('aciklama') and kalem_sayisi > 1:
        metin = f"{data.get('kategori', '')} +{kalem_sayisi - 1}"
    return f"GG: {metin}"


ODEME_TAKIBI_ONEK = 'GG ödeme:'   # odeme takibinden (sonradan) yapilan odemelerin kasa aciklama oneki


def _sync_kasa_for_gg(conn, gg_ids, data, toplam, eski_tarih=None):
    """ODENDI gelir/gider icin bagli kasa kayd(lar)ini olusturur/gunceller.
    gg_ids: kaydin (veya grubun tum kalemlerinin) id'leri; kasa ilk id'ye (lider) baglanir.
    - Bagli kasa yoksa: TEK kayit, tutar = toplam (pesin odeme).
    - Tek bagli kasa varsa: gunceller. Tarih, kasa kaydi giderle ayni gun acildiysa (pesin)
      gider tarihini izler; sonradan (odeme takibinden) yapilan odemenin tarihi ve aciklamasi korunur.
    - Birden fazla bagli kasa varsa (taksitli kapanmis): odemeler gercek para hareketleridir,
      tarih/hesap korunur; sadece cari/tur senkronlanir, toplam farki SON odemeye yansitilir."""
    toplam = float(toplam or 0)
    if toplam <= 0 or not gg_ids:
        return
    lead_id = gg_ids[0]
    kasa_tur = data.get('tur', 'GIDER')   # GG GIDER -> kasa GIDER (para cikis), GELIR -> GELIR (giris)
    banka_hesap_id = data.get('banka_hesap_id')
    ph = ','.join('?' * len(gg_ids))
    bagli = [dict(r) for r in conn.execute(
        f'SELECT * FROM kasa WHERE gelir_gider_id IN ({ph}) ORDER BY id', list(gg_ids)
    ).fetchall()]
    aciklama = _kasa_aciklama(data, len(gg_ids))
    if not bagli:
        conn.execute('''
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama, gelir_gider_id, banka_hesap_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (
            data['tarih'], data.get('firma_kod', ''), data.get('firma_ad', ''),
            kasa_tur, toplam, data.get('odeme_sekli', ''), aciklama,
            lead_id, banka_hesap_id,
        ))
        return
    if len(bagli) == 1:
        k = bagli[0]
        sonradan = str(k.get('aciklama') or '').startswith(ODEME_TAKIBI_ONEK)
        pesin = (eski_tarih is None or k.get('tarih') == eski_tarih) and not sonradan
        conn.execute('''
            UPDATE kasa
            SET tarih=?, firma_kod=?, firma_ad=?, tur=?, tutar=?, odeme_sekli=?, aciklama=?,
                banka_hesap_id=?, gelir_gider_id=?
            WHERE id=?
        ''', (
            data['tarih'] if pesin else k.get('tarih'),
            data.get('firma_kod', ''), data.get('firma_ad', ''),
            kasa_tur, toplam,
            data.get('odeme_sekli', '') if pesin else (k.get('odeme_sekli') or ''),
            k.get('aciklama') if sonradan else aciklama,
            banka_hesap_id if pesin else k.get('banka_hesap_id'),
            lead_id, k['id'],
        ))
        return
    for k in bagli:
        conn.execute('UPDATE kasa SET firma_kod=?, firma_ad=?, tur=?, gelir_gider_id=? WHERE id=?',
                     (data.get('firma_kod', ''), data.get('firma_ad', ''), kasa_tur, lead_id, k['id']))
    onceki = sum(float(k.get('tutar') or 0) for k in bagli[:-1])
    son_tutar = round(toplam - onceki, 2)
    if son_tutar > 0.001:
        conn.execute('UPDATE kasa SET tutar=? WHERE id=?', (son_tutar, bagli[-1]['id']))
    else:
        # Toplam, onceki odemelerin altina dustu: son odeme fazlaya dustu -> kaldir
        conn.execute('DELETE FROM kasa WHERE id=?', (bagli[-1]['id'],))


def _create_or_update_kasa_for_gg(conn, rec_id, data):
    """Geriye uyumluluk: tek kayit icin kasa senkronu."""
    _sync_kasa_for_gg(conn, [rec_id], data, float(data.get('toplam', 0) or 0))


def add_gelir_gider(data):
    """Tek kalemli gelir/gider ekler (v3 API + personel bagli giderler). Coklu kalem: save_gelir_gider_grup."""
    with get_db() as conn:
        rec_id = _add_gelir_gider_conn(conn, data)
        # Odendi ise bagli kasa kaydi da olustur (cari kapama icin)
        if data.get('odeme_durumu') == 'ODENDI' and float(data.get('toplam', 0) or 0) > 0:
            _sync_kasa_for_gg(conn, [rec_id], data, float(data.get('toplam', 0) or 0))
        return rec_id


def get_gelir_gider_grup(grup_id):
    """Ayni islemin (grup) tum kalem satirlari (id sirasiyla)."""
    if not grup_id:
        return []
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM gelir_gider WHERE grup_id=? ORDER BY id', (grup_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def _save_grup_conn(conn, kalemler, silinen_idler=None):
    """Coklu kalemli gelir/gider islemini acik conn uzerinde kaydeder/gunceller.
    Birden fazla kalem varsa hepsine ortak grup_id (yoksa uretilir); tek kalem grup_id=''.
    Kasa: ODENDI ise grubun TEK kasa kaydi (ilk kaleme bagli, tutar = grup toplami),
    aksi halde (ODENMEDI/KISMI) bagli kasa silinir (tek kayit davranisiyla ayni).
    Donus: (grup_id, ilk_kalem_id)."""
    import uuid
    kalemler = [k for k in kalemler if k]
    if not kalemler:
        raise ValueError('En az bir kalem gerekli')
    grup_id = next((k['grup_id'] for k in kalemler if k.get('grup_id')), '')
    if len(kalemler) > 1 and not grup_id:
        grup_id = uuid.uuid4().hex
    if len(kalemler) <= 1:
        grup_id = ''
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    # Guncellemede eski islem tarihi: pesin kasa kaydinin tarihi giderle birlikte kayar,
    # sonradan yapilan odemelerin tarihi korunur (_sync_kasa_for_gg)
    eski_tarih = None
    for k in kalemler:
        if k.get('id'):
            eski = conn.execute('SELECT tarih FROM gelir_gider WHERE id=?', (k['id'],)).fetchone()
            eski_tarih = eski['tarih'] if eski else None
            break
    ids = []
    for k in kalemler:
        k = dict(k)
        k['grup_id'] = grup_id
        kid = k.pop('id', None)
        if kid:
            _update_gelir_gider_conn(conn, kid, k)
        else:
            # Ayni created_at: grup kalemleri listede/ekstrede birlikte dursun
            k['created_at'] = k.get('created_at') or now
            kid = _add_gelir_gider_conn(conn, k)
        ids.append(kid)
    # Cikarilan kalemler: bagli kasa varsa lidere tasi (grubun odemesi kaybolmasin), sonra sil
    for sid in (silinen_idler or []):
        conn.execute('UPDATE kasa SET gelir_gider_id=? WHERE gelir_gider_id=?', (ids[0], sid))
        conn.execute('DELETE FROM gelir_gider WHERE id=?', (sid,))
    bas = kalemler[0]
    toplam = sum(float(k.get('toplam', 0) or 0) for k in kalemler)
    if bas.get('odeme_durumu') == 'ODENDI':
        _sync_kasa_for_gg(conn, ids, bas, toplam, eski_tarih=eski_tarih)
    else:
        # ODENMEDI/KISMI: formdan gelen pesin kasa kaydi kaldirilir; odeme takibinden yapilan
        # (sonradan) kismi odemeler gercek para hareketi oldugu icin KORUNUR.
        ph = ','.join('?' * len(ids))
        conn.execute(f"DELETE FROM kasa WHERE gelir_gider_id IN ({ph}) AND COALESCE(aciklama,'') NOT LIKE ?",
                     ids + [ODEME_TAKIBI_ONEK + '%'])
    return grup_id, ids[0]


def save_gelir_gider_grup(kalemler, silinen_idler=None):
    """Coklu kalemli (kategori bazli) gelir/gider islemini tek transaction'da kaydeder/gunceller.

    kalemler: gelir_gider data dict listesi (ortak baslik alanlari + kalem alanlari);
      'id' dolu olan UPDATE, olmayan INSERT edilir. Tumunde odeme_durumu/tarih/cari ayni olmali.
    silinen_idler: duzenlemede cikarilan kalemlerin id'leri (silinir).
    Donus: (grup_id, ilk_kalem_id) — grup_id '' ise tek kalem."""
    with get_db() as conn:
        return _save_grup_conn(conn, kalemler, silinen_idler)


def update_gelir_gider(rec_id, data):
    """Tek kaydi gunceller VE bagli kasa kaydini senkronize eder (v3 API + eski cagrilar).
    Kayit bir grubun parcasiysa baslik alanlari (tarih, cari, odeme durumu...) grubun
    diger kalemlerine de yazilir; kasa tutari grup toplami olur.
    Codex flow audit bulgu 4 fix."""
    with get_db() as conn:
        row = conn.execute('SELECT * FROM gelir_gider WHERE id=?', (rec_id,)).fetchone()
        if not row:
            return
        gid = row['grup_id'] or ''
        if gid:
            rows = [dict(r) for r in conn.execute(
                'SELECT * FROM gelir_gider WHERE grup_id=? ORDER BY id', (gid,)).fetchall()]
        else:
            rows = [dict(row)]
        kalemler = []
        for r in rows:
            k = dict(r)
            if r['id'] == rec_id:
                k.update(data)
            else:
                for f in BASLIK_ALANLAR:
                    if f in data:
                        k[f] = data[f]
                if 'banka_hesap_id' in data:
                    k['banka_hesap_id'] = data['banka_hesap_id']
            k['id'] = r['id']
            kalemler.append(k)
        _save_grup_conn(conn, kalemler)


def delete_gelir_gider(rec_id):
    """Tek kaydi siler. Grup uyesiyse sadece o kalem cikar, grubun kasa tutari yeniden hesaplanir
    (grubun tamami icin delete_gelir_gider_grup)."""
    with get_db() as conn:
        row = conn.execute('SELECT * FROM gelir_gider WHERE id=?', (rec_id,)).fetchone()
        if not row:
            return
        gid = row['grup_id'] or ''
        kalan = []
        if gid:
            kalan = [dict(r) for r in conn.execute(
                'SELECT * FROM gelir_gider WHERE grup_id=? AND id<>? ORDER BY id', (gid, rec_id)).fetchall()]
        if not kalan:
            # Bagli kasa kayitlarini da sil (auto-olusturulanlar)
            conn.execute('DELETE FROM kasa WHERE gelir_gider_id=?', (rec_id,))
            conn.execute('DELETE FROM gelir_gider WHERE id=?', (rec_id,))
            return
        ids = [k['id'] for k in kalan]
        conn.execute('UPDATE kasa SET gelir_gider_id=? WHERE gelir_gider_id=?', (ids[0], rec_id))
        conn.execute('DELETE FROM gelir_gider WHERE id=?', (rec_id,))
        if len(ids) == 1:
            conn.execute("UPDATE gelir_gider SET grup_id='' WHERE id=?", (ids[0],))
        if kalan[0].get('odeme_durumu') == 'ODENDI':
            _sync_kasa_for_gg(conn, ids, kalan[0], sum(float(k.get('toplam') or 0) for k in kalan),
                              eski_tarih=kalan[0].get('tarih'))


def delete_gelir_gider_grup(grup_id):
    """Grubun tum kalemlerini ve bagli kasa kaydini tek transaction'da siler."""
    if not grup_id:
        return
    with get_db() as conn:
        ids = [r['id'] for r in conn.execute(
            'SELECT id FROM gelir_gider WHERE grup_id=?', (grup_id,)).fetchall()]
        if not ids:
            return
        ph = ','.join('?' * len(ids))
        conn.execute(f'DELETE FROM kasa WHERE gelir_gider_id IN ({ph})', ids)
        conn.execute('DELETE FROM gelir_gider WHERE grup_id=?', (grup_id,))


def _gg_grup_satirlari(conn, gg_id):
    """Kaydin ait oldugu grubun tum satirlari (grup yoksa tek satir). Donus: list[dict] (id sirali)."""
    rec = conn.execute('SELECT * FROM gelir_gider WHERE id=?', (gg_id,)).fetchone()
    if not rec:
        return []
    gid = rec['grup_id'] or ''
    if gid:
        return [dict(r) for r in conn.execute(
            'SELECT * FROM gelir_gider WHERE grup_id=? ORDER BY id', (gid,)).fetchall()]
    return [dict(rec)]


def _gg_odenen(conn, ids):
    ph = ','.join('?' * len(ids))
    r = conn.execute(f'SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE gelir_gider_id IN ({ph})', list(ids)).fetchone()
    return float(r[0] or 0)


def gg_odeme_durumu_yenile(conn, gg_id):
    """Bagli kasa (odeme) kayitlarina gore grubun odeme_durumu'nu yeniden hesaplar.
    Odeme takibinden yapilan bir odeme silinince cagrilir (gider kalir, durumu geri doner)."""
    rows = _gg_grup_satirlari(conn, gg_id)
    if not rows:
        return None
    ids = [r['id'] for r in rows]
    toplam = sum(float(r.get('toplam') or 0) for r in rows)
    odenen = _gg_odenen(conn, ids)
    if odenen >= toplam - 0.01 and toplam > 0:
        durum = 'ODENDI'
    elif odenen > 0.01:
        durum = 'KISMI'
    else:
        durum = 'ODENMEDI'
    ph = ','.join('?' * len(ids))
    if durum == 'ODENMEDI':
        conn.execute(f"UPDATE gelir_gider SET odeme_durumu=?, odeme_sekli='' WHERE id IN ({ph})", [durum] + ids)
    else:
        conn.execute(f"UPDATE gelir_gider SET odeme_durumu=? WHERE id IN ({ph})", [durum] + ids)
    return durum


def get_gelir_gider_vadeleri():
    """Odenmemis / kismi odenmis gelir-gider kayitlarini (grup bazinda tek satir) odeme takibi
    formatinda dondurur. GIDER -> BORC (odenecek), GELIR -> ALACAK (tahsil edilecek).
    Odenen = bagli kasa kayitlari toplami. Vade girilmemisse islem tarihi esas alinir
    (vade_varsayilan=True). Cari bakiyeyi ETKILEMEZ; turetilmis rapordur."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, tarih, tur, COALESCE(kategori,'') AS kategori, COALESCE(aciklama,'') AS aciklama, "
            "       COALESCE(toplam,0) AS toplam, odeme_durumu, "
            "       COALESCE(NULLIF(vade_tarih,''),'') AS vade_tarih, "
            "       COALESCE(firma_kod,'') AS firma_kod, COALESCE(firma_ad,'') AS firma_ad, "
            "       COALESCE(grup_id,'') AS grup_id "
            "FROM gelir_gider WHERE odeme_durumu IN ('ODENMEDI','KISMI') "
            "ORDER BY COALESCE(NULLIF(vade_tarih,''), tarih), tarih, id"
        ).fetchall()
        if not rows:
            return []
        ids = [r['id'] for r in rows]
        ph = ','.join('?' * len(ids))
        odenen_map = {r['gelir_gider_id']: float(r['t'] or 0) for r in conn.execute(
            f"SELECT gelir_gider_id, COALESCE(SUM(tutar),0) AS t FROM kasa "
            f"WHERE gelir_gider_id IN ({ph}) GROUP BY gelir_gider_id", ids).fetchall()}
    out, gmap = [], {}
    for r in rows:
        key = r['grup_id'] or f"#{r['id']}"
        if key in gmap:
            g = gmap[key]
            g['tutar'] += float(r['toplam'] or 0)
            g['odenen'] += odenen_map.get(r['id'], 0.0)
            g['_kategoriler'].append(r['kategori'])
            continue
        g = {
            'kaynak': 'GG',
            'kaynak_label': 'Gider' if r['tur'] == 'GIDER' else 'Gelir',
            'tip': 'BORC' if r['tur'] == 'GIDER' else 'ALACAK',
            'gg_id': r['id'],
            'grup_id': r['grup_id'],
            'firma_kod': r['firma_kod'],
            'firma_ad': r['firma_ad'],
            'aciklama': '',
            '_aciklama': r['aciklama'],
            '_kategoriler': [r['kategori']],
            'tutar': float(r['toplam'] or 0),
            'odenen': odenen_map.get(r['id'], 0.0),
            'kalan': 0.0,
            'islem_tarih': r['tarih'] or '',
            'vade_tarih': r['vade_tarih'] or r['tarih'] or '',
            'vade_varsayilan': not r['vade_tarih'],
            'durum': 'ACIK',
        }
        gmap[key] = g
        out.append(g)
    for g in out:
        kats = g.pop('_kategoriler')
        etiket = kats[0] + (f" +{len(kats) - 1}" if len(kats) > 1 else '')
        acik = g.pop('_aciklama')
        g['aciklama'] = f"{etiket}: {acik}" if acik else etiket
        g['tutar'] = round(g['tutar'], 2)
        g['odenen'] = round(g['odenen'], 2)
        g['kalan'] = round(max(g['tutar'] - g['odenen'], 0.0), 2)
        g['durum'] = 'KISMI' if g['odenen'] > 0.01 else 'ACIK'
    return out


def ode_gelir_gider(gg_id, tarih=None, tutar=None, banka_hesap_id=None):
    """Odenmemis/kismi bir gelir-gider kaydini (grubunu) oder / tahsil eder.
    Kasa kaydi olusturur (GIDER -> kasa GIDER, GELIR -> kasa GELIR), lider kaleme baglar
    ('GG ödeme:' onekli — sonradan odeme; silinirse gider kalir, durumu geri doner).
    tutar None ise kalanin tamami. Kalandan fazla odeme reddedilir. Donus: kasa_id."""
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    tarih = tarih or datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        rows = _gg_grup_satirlari(conn, gg_id)
        if not rows:
            raise ValueError('Kayıt bulunamadı')
        ids = [r['id'] for r in rows]
        toplam = sum(float(r.get('toplam') or 0) for r in rows)
        odenen = _gg_odenen(conn, ids)
        kalan = round(toplam - odenen, 2)
        odenecek = round(float(tutar), 2) if tutar else kalan
        if odenecek <= 0:
            raise ValueError('Ödenecek tutar geçersiz')
        if odenecek > kalan + 0.01:
            raise ValueError(f'Kalan tutardan ({kalan:,.2f}) fazla ödenemez')
        bas = rows[0]
        etiket = (bas.get('kategori') or '') + (f" +{len(rows) - 1}" if len(rows) > 1 else '')
        if bas.get('aciklama'):
            etiket += f": {bas['aciklama']}"
        odeme_sekli = 'BANKA' if banka_hesap_id else 'NAKIT'
        cur = conn.execute('''
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama,
                              gelir_gider_id, banka_hesap_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?) RETURNING id
        ''', (
            tarih, bas.get('firma_kod', '') or '', bas.get('firma_ad', '') or '',
            bas.get('tur', 'GIDER'), odenecek, odeme_sekli,
            f"{ODEME_TAKIBI_ONEK} {etiket}"[:200], ids[0], banka_hesap_id, now_ts,
        ))
        kasa_id = cur.fetchone()['id']
        yeni_durum = 'ODENDI' if odenen + odenecek >= toplam - 0.01 else 'KISMI'
        ph = ','.join('?' * len(ids))
        conn.execute(f"UPDATE gelir_gider SET odeme_durumu=?, odeme_sekli=? WHERE id IN ({ph})",
                     [yeni_durum, odeme_sekli] + ids)
        return kasa_id


def gelir_gider_grupla(rows):
    """Liste gosterimi: ayni grup_id'li kalemleri tek satirda birlestirir (Islemler sayfasi gibi).
    Birlesik satir: tutar/kdv_tutar/toplam toplanir, kategori 'Kirtasiye +1',
    'kategori_tum' arama icin tum kategoriler, 'kalemler' = [{id, kategori, tutar, kdv_orani, kdv_tutar, toplam}].
    Tek kalemli kayitlar oldugu gibi kalir."""
    out, gmap = [], {}
    for r in rows:
        gid = r.get('grup_id') or ''
        if not gid:
            out.append(r)
            continue
        kalem = {
            'id': r.get('id'), 'kategori': r.get('kategori', '') or '',
            'tutar': float(r.get('tutar') or 0), 'kdv_orani': float(r.get('kdv_orani') or 0),
            'kdv_tutar': float(r.get('kdv_tutar') or 0), 'toplam': float(r.get('toplam') or 0),
        }
        if gid in gmap:
            p = gmap[gid]
            p['kalemler'].append(kalem)
            p['tutar'] += kalem['tutar']
            p['kdv_tutar'] += kalem['kdv_tutar']
            p['toplam'] += kalem['toplam']
            continue
        p = dict(r)
        p.update({'tutar': kalem['tutar'], 'kdv_tutar': kalem['kdv_tutar'], 'toplam': kalem['toplam']})
        p['kalemler'] = [kalem]
        gmap[gid] = p
        out.append(p)
    for p in gmap.values():
        p['kalemler'].sort(key=lambda k: k['id'] or 0)
        if len(p['kalemler']) > 1:
            p['kategori'] = f"{p['kalemler'][0]['kategori']} +{len(p['kalemler']) - 1}"
            p['kategori_tum'] = ', '.join(k['kategori'] for k in p['kalemler'])
            p['kdv_orani'] = None   # karma oran
        else:
            p.pop('kalemler', None)
    return out


def get_gelir_gider_rapor(baslangic=None, bitis=None, tur=None):
    """Rapor icin tarih araligi + tur filtresiyle kayitlar.
    baslangic/bitis: 'YYYY-MM-DD' (dahil) veya bos/None. tur: 'GELIR'/'GIDER' veya None (hepsi)."""
    where = ["tarih IS NOT NULL AND tarih != ''"]
    params = []
    if baslangic:
        where.append("tarih >= ?"); params.append(str(baslangic)[:10])
    if bitis:
        where.append("tarih <= ?"); params.append(str(bitis)[:10])
    if tur in ('GELIR', 'GIDER'):
        where.append("tur = ?"); params.append(tur)
    # Yeni tarih en ustte (azalan) — ekran listesiyle ayni
    sql = "SELECT * FROM gelir_gider WHERE " + " AND ".join(where) + \
          " ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC"
    with get_db() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def kategori_ozet(rows):
    """Kayitlari tur -> kategori bazinda toplar. Donus:
    {'GIDER': [{kategori, adet, matrah, kdv, toplam}, ...], 'GELIR': [...]}
    Her tur listesi TOPLAMA gore buyukten kucuge sirali. Ayrica her satirda kayitlar da tutulur ('kayitlar')."""
    from collections import OrderedDict
    grp = {'GIDER': OrderedDict(), 'GELIR': OrderedDict()}
    for r in rows:
        tur = r.get('tur', '')
        if tur not in grp:
            continue
        kat = (r.get('kategori') or '').strip() or '(Kategorisiz)'
        g = grp[tur].get(kat)
        if g is None:
            g = {'kategori': kat, 'adet': 0, 'matrah': 0.0, 'kdv': 0.0, 'toplam': 0.0, 'kayitlar': []}
            grp[tur][kat] = g
        g['adet'] += 1
        g['matrah'] += float(r.get('tutar', 0) or 0)
        g['kdv'] += float(r.get('kdv_tutar', 0) or 0)
        g['toplam'] += float(r.get('toplam', 0) or 0)
        g['kayitlar'].append(r)
    out = {}
    for tur, kats in grp.items():
        lst = list(kats.values())
        lst.sort(key=lambda x: x['toplam'], reverse=True)   # tutara gore buyukten kucuge
        out[tur] = lst
    return out
