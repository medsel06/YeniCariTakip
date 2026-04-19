"""KDV beyanname ozet hesaplama."""
from db import get_db


def get_kdv_ozet(yil, ay):
    """Secilen ay icin KDV ozeti hesapla."""
    prefix = f'{int(yil):04d}-{int(ay):02d}'
    with get_db() as conn:
        # Alis KDV (indirilecek)
        alis = conn.execute('''
            SELECT
                COALESCE(SUM(toplam), 0) AS matrah,
                COALESCE(SUM(kdv_tutar), 0) AS kdv,
                COALESCE(SUM(tevkifat_tutar), 0) AS tevkifat
            FROM hareketler
            WHERE tur='ALIS' AND tarih >= ? AND tarih < ?
        ''', (f'{prefix}-01', f'{prefix}-32')).fetchone()

        # Satis KDV (hesaplanan)
        satis = conn.execute('''
            SELECT
                COALESCE(SUM(toplam), 0) AS matrah,
                COALESCE(SUM(kdv_tutar), 0) AS kdv,
                COALESCE(SUM(tevkifat_tutar), 0) AS tevkifat
            FROM hareketler
            WHERE tur='SATIS' AND tarih >= ? AND tarih < ?
        ''', (f'{prefix}-01', f'{prefix}-32')).fetchone()

        hesaplanan = float(satis['kdv'] or 0)
        indirilecek = float(alis['kdv'] or 0)
        tevkifat = float(satis['tevkifat'] or 0)
        odenecek = hesaplanan - indirilecek - tevkifat

        return {
            'alis_matrah': float(alis['matrah'] or 0),
            'alis_kdv': indirilecek,
            'satis_matrah': float(satis['matrah'] or 0),
            'satis_kdv': hesaplanan,
            'tevkifat': tevkifat,
            'odenecek_kdv': odenecek,
        }
