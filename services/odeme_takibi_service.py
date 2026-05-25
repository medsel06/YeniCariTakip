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
