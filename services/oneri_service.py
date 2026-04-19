"""Tahsilat onerisi ve karlilik hesaplari."""
from datetime import datetime

from db import get_db


def get_tahsilat_onerileri():
    with get_db() as conn:
        firms = conn.execute('SELECT kod, ad, risk_limiti FROM firmalar ORDER BY ad').fetchall()
        out = []
        for f in firms:
            kod = f['kod']
            risk_limiti = float(f['risk_limiti'] or 0)
            alis = conn.execute(
                "SELECT COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE firma_kod=? AND tur='ALIS'",
                (kod,),
            ).fetchone()[0]
            satis = conn.execute(
                "SELECT COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE firma_kod=? AND tur='SATIS'",
                (kod,),
            ).fetchone()[0]
            odeme = conn.execute(
                "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE firma_kod=? AND tur='GIDER'",
                (kod,),
            ).fetchone()[0]
            tahsilat = conn.execute(
                "SELECT COALESCE(SUM(tutar),0) FROM kasa WHERE firma_kod=? AND tur='GELIR'",
                (kod,),
            ).fetchone()[0]
            bakiye = (satis - tahsilat) - (alis - odeme)
            if bakiye <= 0:
                continue

            oldest_sale = conn.execute(
                "SELECT MIN(tarih) FROM hareketler WHERE firma_kod=? AND tur='SATIS'",
                (kod,),
            ).fetchone()[0]
            gun = 0
            if oldest_sale:
                try:
                    gun = (datetime.now().date() - datetime.strptime(oldest_sale, '%Y-%m-%d').date()).days
                except Exception:
                    gun = 0

            # Risk limiti carpani
            risk_yuzde = (float(bakiye) / risk_limiti * 100) if risk_limiti > 0 else 0
            if risk_limiti > 0 and float(bakiye) > risk_limiti:
                risk_carpan = 10  # Limit asimi - en yuksek oncelik
            elif risk_yuzde >= 80:
                risk_carpan = 3  # Limitin %80+ - yuksek oncelik
            else:
                risk_carpan = 1

            oncelik = (gun * 1000 + float(bakiye)) * risk_carpan
            out.append({
                'firma_kod': kod,
                'firma_ad': f['ad'],
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
