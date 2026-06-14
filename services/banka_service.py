"""Banka hesaplari ve banka hareketleri.

Tasarim:
- banka_hesaplari = master tablo (her banka/kredi karti = bir kayit).
- Banka hareketleri AYRI tablo degil: tum para hareketleri 'kasa' tablosunda.
  kasa.banka_hesap_id NULL  -> nakit kasa
  kasa.banka_hesap_id dolu  -> o banka hesabi
- Banka bakiyesi = acilis_bakiye + SUM(GELIR) - SUM(GIDER)  (o hesabin kayitlari)
- Transfer (nakit<->banka, banka<->banka): iki kasa kaydi, ayni transfer_id,
  is_transfer=1, firma_kod='' (cari/gelir-gider raporlarina sizmaz).
"""
import uuid
from datetime import datetime
from db import get_db


# --- MASTER CRUD ---

def list_banka_hesaplari(sadece_aktif=False):
    with get_db() as conn:
        sql = "SELECT * FROM banka_hesaplari"
        if sadece_aktif:
            sql += " WHERE aktif=1"
        sql += " ORDER BY ad"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def get_banka_hesap(hesap_id):
    with get_db() as conn:
        r = conn.execute("SELECT * FROM banka_hesaplari WHERE id=?", (hesap_id,)).fetchone()
        return dict(r) if r else None


def add_banka_hesap(data):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cur = conn.execute('''
            INSERT INTO banka_hesaplari (ad, tip, iban, hesap_no, acilis_bakiye, kart_limiti, aktif, created_at)
            VALUES (?,?,?,?,?,?,?,?) RETURNING id
        ''', (
            data['ad'].strip(),
            data.get('tip', 'BANKA'),
            data.get('iban', '').strip(),
            data.get('hesap_no', '').strip(),
            float(data.get('acilis_bakiye', 0) or 0),
            float(data.get('kart_limiti', 0) or 0),
            1 if data.get('aktif', True) else 0,
            now,
        ))
        return cur.fetchone()['id']


def update_banka_hesap(hesap_id, data):
    with get_db() as conn:
        conn.execute('''
            UPDATE banka_hesaplari SET ad=?, tip=?, iban=?, hesap_no=?, acilis_bakiye=?, kart_limiti=?, aktif=?
            WHERE id=?
        ''', (
            data['ad'].strip(),
            data.get('tip', 'BANKA'),
            data.get('iban', '').strip(),
            data.get('hesap_no', '').strip(),
            float(data.get('acilis_bakiye', 0) or 0),
            float(data.get('kart_limiti', 0) or 0),
            1 if data.get('aktif', True) else 0,
            hesap_id,
        ))


def delete_banka_hesap(hesap_id):
    """Bagli kasa hareketi varsa silmeyi engelle (veri butunlugu)."""
    with get_db() as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM kasa WHERE banka_hesap_id=?", (hesap_id,)
        ).fetchone()[0]
        if cnt and int(cnt) > 0:
            raise ValueError(f"Bu hesaba bagli {int(cnt)} hareket var. Once hesabi pasife alin.")
        conn.execute("DELETE FROM banka_hesaplari WHERE id=?", (hesap_id,))


# --- BAKIYE ---

def get_banka_bakiye(hesap_id):
    """Tek bir banka hesabinin guncel bakiyesi."""
    with get_db() as conn:
        h = conn.execute("SELECT acilis_bakiye FROM banka_hesaplari WHERE id=?", (hesap_id,)).fetchone()
        if not h:
            return 0.0
        acilis = float(h['acilis_bakiye'] or 0)
        giris = conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE banka_hesap_id=? AND tur='GELIR'", (hesap_id,)
        ).fetchone()[0]
        cikis = conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE banka_hesap_id=? AND tur='GIDER'", (hesap_id,)
        ).fetchone()[0]
        return acilis + float(giris or 0) - float(cikis or 0)


def get_tum_banka_bakiyeler(sadece_aktif=False):
    """Her hesap icin {hesap dict + 'bakiye', 'giris', 'cikis'} dondur."""
    hesaplar = list_banka_hesaplari(sadece_aktif=sadece_aktif)
    with get_db() as conn:
        out = []
        for h in hesaplar:
            giris = conn.execute(
                "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE banka_hesap_id=? AND tur='GELIR'", (h['id'],)
            ).fetchone()[0]
            cikis = conn.execute(
                "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE banka_hesap_id=? AND tur='GIDER'", (h['id'],)
            ).fetchone()[0]
            acilis = float(h.get('acilis_bakiye', 0) or 0)
            h['giris'] = float(giris or 0)
            h['cikis'] = float(cikis or 0)
            h['bakiye'] = acilis + h['giris'] - h['cikis']
            out.append(h)
        return out


def get_banka_hareketler(hesap_id, yil=None, ay=None):
    """Bir banka hesabinin hareket dokumu (tarih sirali)."""
    from services.kasa_service import _date_filter
    flt, params = _date_filter(yil, ay)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM kasa WHERE banka_hesap_id=?{flt} "
            f"ORDER BY tarih DESC, COALESCE(created_at, tarih || ' 00:00:00.000000') DESC, id DESC",
            [hesap_id] + params
        ).fetchall()
        return [dict(r) for r in rows]


# --- TRANSFER (cift bacakli) ---

def transfer(kaynak_hesap_id, hedef_hesap_id, tutar, tarih, aciklama=''):
    """Hesaplar arasi para transferi. None = nakit kasa.
    Iki kasa kaydi olusur (ayni transfer_id, is_transfer=1, firma_kod='').
    Returns: transfer_id (str)
    """
    if kaynak_hesap_id == hedef_hesap_id:
        raise ValueError("Kaynak ve hedef ayni olamaz")
    tutar = float(tutar or 0)
    if tutar <= 0:
        raise ValueError("Tutar 0'dan buyuk olmali")
    tid = uuid.uuid4().hex
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    def _ad(hid):
        if hid is None:
            return "NAKIT KASA"
        h = get_banka_hesap(hid)
        return h['ad'] if h else f"Hesap {hid}"

    kaynak_ad = _ad(kaynak_hesap_id)
    hedef_ad = _ad(hedef_hesap_id)
    acik_cikis = aciklama or f"Transfer: {kaynak_ad} -> {hedef_ad}"
    acik_giris = aciklama or f"Transfer: {kaynak_ad} -> {hedef_ad}"

    with get_db() as conn:
        # Kaynaktan cikis (GIDER)
        conn.execute('''
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama,
                              banka_hesap_id, transfer_id, is_transfer, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            tarih, '', '', 'GIDER', tutar,
            'NAKIT' if kaynak_hesap_id is None else 'BANKA',
            acik_cikis, kaynak_hesap_id, tid, 1, now,
        ))
        # Hedefe giris (GELIR)
        conn.execute('''
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli, aciklama,
                              banka_hesap_id, transfer_id, is_transfer, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            tarih, '', '', 'GELIR', tutar,
            'NAKIT' if hedef_hesap_id is None else 'BANKA',
            acik_giris, hedef_hesap_id, tid, 1, now,
        ))
    return tid


def delete_transfer(transfer_id):
    """Bir transferin iki bacagini birlikte sil (atomik)."""
    if not transfer_id:
        return
    with get_db() as conn:
        conn.execute("DELETE FROM kasa WHERE transfer_id=? AND is_transfer=1", (transfer_id,))
