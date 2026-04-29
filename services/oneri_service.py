"""Tahsilat onerisi ve karlilik hesaplari."""
from datetime import datetime

from db import get_db
from services import cari_service


def get_tahsilat_onerileri():
    """Cari liste ile ayni bakiye formulu (cek dahil) — merkezi ledger uzerinden.
    Risk uyarisi, cari liste ve tahsilat onerisi tutarli sonuclar uretir."""
    bakiyeler = cari_service.get_cari_ledger(firma_kod=None)
    with get_db() as conn:
        risk_map = {}
        for f in conn.execute('SELECT kod, risk_limiti FROM firmalar').fetchall():
            risk_map[f['kod']] = float(f['risk_limiti'] or 0)

        out = []
        for b in bakiyeler:
            bakiye = b['bakiye']
            if bakiye <= 0:
                continue
            kod = b['kod']
            risk_limiti = risk_map.get(kod, 0)
            oldest_sale = conn.execute(
                "SELECT MIN(tarih) FROM hareketler WHERE firma_kod=? AND tur='SATIS' AND tarih IS NOT NULL AND tarih != ''",
                (kod,),
            ).fetchone()[0]
            gun = 0
            if oldest_sale:
                try:
                    gun = (datetime.now().date() - datetime.strptime(oldest_sale, '%Y-%m-%d').date()).days
                except Exception:
                    gun = 0

            risk_yuzde = (float(bakiye) / risk_limiti * 100) if risk_limiti > 0 else 0
            if risk_limiti > 0 and float(bakiye) > risk_limiti:
                risk_carpan = 10
            elif risk_yuzde >= 80:
                risk_carpan = 3
            else:
                risk_carpan = 1

            oncelik = (gun * 1000 + float(bakiye)) * risk_carpan
            out.append({
                'firma_kod': kod,
                'firma_ad': b['ad'],
                'onerilen_tahsilat': float(bakiye),
                'en_eski_satis': oldest_sale or '',
                'gecikme_gun': gun,
                'oncelik_skoru': oncelik,
                'risk_limiti': risk_limiti,
                'risk_yuzdesi': round(risk_yuzde, 1),
            })

        out.sort(key=lambda x: x['oncelik_skoru'], reverse=True)
        return out


def get_urun_karlilik_ozeti():
    with get_db() as conn:
        rows = conn.execute(
            '''
            SELECT
                urun_kod,
                urun_ad,
                SUM(CASE WHEN tur='ALIS' THEN miktar ELSE 0 END) AS alis_miktar,
                SUM(CASE WHEN tur='SATIS' THEN miktar ELSE 0 END) AS satis_miktar,
                SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) AS alis_tutar,
                SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) AS satis_tutar
            FROM hareketler
            GROUP BY urun_kod, urun_ad
            ORDER BY urun_ad
            '''
        ).fetchall()
        result = []
        for r in rows:
            alis_t = float(r['alis_tutar'] or 0)
            satis_t = float(r['satis_tutar'] or 0)
            kar = satis_t - alis_t
            marj = (kar / satis_t * 100.0) if satis_t > 0 else 0.0
            result.append({
                'urun_kod': r['urun_kod'],
                'urun_ad': r['urun_ad'],
                'alis_miktar': float(r['alis_miktar'] or 0),
                'satis_miktar': float(r['satis_miktar'] or 0),
                'alis_tutar': alis_t,
                'satis_tutar': satis_t,
                'kar': kar,
                'marj': marj,
            })
        result.sort(key=lambda x: x['kar'], reverse=True)
        return result
