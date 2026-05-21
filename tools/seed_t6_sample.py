# -*- coding: utf-8 -*-
"""t_6 (Murat Baysal) icin ornek veri seti.

Senaryo:
  18.05.2026  ALIS    PARS PLASTIK  1000 kg ATIK PE  @12 TL = 12.000 + %1 KDV   (nakit/banka)
  20.05.2026  SATIS   DEMIR GERI K. 500 kg ATIK PE   @15 TL = 7.500  + %1 KDV   (tahsilat)
  20.05.2026  GIDER   Elektrik faturasi 850 TL (nakit kasadan)
  21.05.2026  ALIS    EROL HURDA    800 kg KARTON   @6 TL  = 4.800 + %1 KDV   (3 ay vadeli cek)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import psycopg2
from db import DB_CONFIG

SCHEMA = "t_6"
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public")

        # --- URUNLER ---
        cur.execute("""
            INSERT INTO urunler (kod, ad, kategori, birim, desi_degeri, aktif)
            VALUES ('PE001', 'ATIK PE (POLIETILEN)', 'PLASTIK', 'KG', 0, 1),
                   ('KRT01', 'KARISIK KARTON', 'KAGIT', 'KG', 0, 1)
            ON CONFLICT (kod) DO NOTHING
        """)
        print("urunler eklendi: PE001, KRT01")

        # --- FIRMALAR ---
        cur.execute("""
            INSERT INTO firmalar (kod, ad, tel, adres, vkn_tckn, aktif)
            VALUES
              ('TED001', 'PARS PLASTIK A.S.',     '0532 111 22 33', 'ANKARA',    '1234567890', 1),
              ('TED002', 'EROL HURDA TIC.',       '0532 222 33 44', 'KIRIKKALE', '2345678901', 1),
              ('MUS001', 'DEMIR GERI KAZANIM',    '0532 333 44 55', 'ISTANBUL',  '3456789012', 1)
            ON CONFLICT (kod) DO NOTHING
        """)
        print("firmalar eklendi: TED001, TED002, MUS001")

        # --- 1) 18.05.2026 ALIS: PARS PLASTIK'ten 1000 kg ATIK PE @12 TL ---
        net1 = 1000 * 12  # 12.000
        kdv1 = round(net1 * 0.01, 2)  # 120
        top1 = net1 + kdv1  # 12.120
        cur.execute("""
            INSERT INTO hareketler (tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad,
                                    miktar, birim_fiyat, toplam, kdv_orani, kdv_tutar,
                                    kdvli_toplam, tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv,
                                    aciklama, created_at, belge_no)
            VALUES ('2026-05-18', 'TED001', 'PARS PLASTIK A.S.', 'ALIS',
                    'PE001', 'ATIK PE (POLIETILEN)',
                    1000, 12, %s, 1, %s, %s, '0', 0, %s,
                    'Atik PE alimi - irsaliye no 2025/001', %s, 'IRS-2025-001')
            RETURNING id
        """, (net1, kdv1, top1, kdv1, NOW))
        hid1 = cur.fetchone()[0]
        # Kasa: nakit odeme
        cur.execute("""
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli,
                              aciklama, banka, created_at, kategori)
            VALUES ('2026-05-18', 'TED001', 'PARS PLASTIK A.S.', 'ODEME', %s, 'NAKIT',
                    'Atik PE alim odemesi', '', %s, '')
        """, (top1, NOW))
        print(f"1) ALIS  18.05.2026  PE001 1000kg @12  net={net1} kdv={kdv1} top={top1}  (hareket_id={hid1})")

        # --- 2) 20.05.2026 SATIS: DEMIR'e 500 kg ATIK PE @15 TL ---
        net2 = 500 * 15  # 7.500
        kdv2 = round(net2 * 0.01, 2)  # 75
        top2 = net2 + kdv2  # 7.575
        cur.execute("""
            INSERT INTO hareketler (tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad,
                                    miktar, birim_fiyat, toplam, kdv_orani, kdv_tutar,
                                    kdvli_toplam, tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv,
                                    aciklama, created_at, belge_no)
            VALUES ('2026-05-20', 'MUS001', 'DEMIR GERI KAZANIM', 'SATIS',
                    'PE001', 'ATIK PE (POLIETILEN)',
                    500, 15, %s, 1, %s, %s, '0', 0, %s,
                    'Atik PE satisi - fatura no 2026/A12', %s, 'FTR-2026-A12')
            RETURNING id
        """, (net2, kdv2, top2, kdv2, NOW))
        hid2 = cur.fetchone()[0]
        # Kasa: tahsilat (Garanti banka EFT)
        cur.execute("""
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli,
                              aciklama, banka, created_at, kategori)
            VALUES ('2026-05-20', 'MUS001', 'DEMIR GERI KAZANIM', 'TAHSIL', %s, 'BANKA',
                    'Atik PE satis tahsilati', 'Garanti BBVA', %s, '')
        """, (top2, NOW))
        print(f"2) SATIS 20.05.2026  PE001  500kg @15  net={net2} kdv={kdv2} top={top2}  (hareket_id={hid2})")

        # --- 3) 20.05.2026 GIDER: elektrik faturasi 850 TL nakit ---
        gider_tutar = 850
        kdv_gider = 153  # %18
        top_gider = gider_tutar + kdv_gider
        cur.execute("""
            INSERT INTO gelir_gider (tarih, tur, kategori, aciklama, tutar, kdv_orani,
                                     kdv_tutar, toplam, odeme_sekli, created_at,
                                     firma_kod, firma_ad, odeme_durumu, vade_tarih)
            VALUES ('2026-05-20', 'GIDER', 'ELEKTRIK', 'Mayis 2026 elektrik faturasi',
                    %s, 18, %s, %s, 'NAKIT', %s, '', 'ENERJISA', 'ODENDI', '')
            RETURNING id
        """, (gider_tutar, kdv_gider, top_gider, NOW))
        gg_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO kasa (tarih, firma_kod, firma_ad, tur, tutar, odeme_sekli,
                              aciklama, gelir_gider_id, banka, created_at, kategori)
            VALUES ('2026-05-20', '', 'ENERJISA', 'GIDER', %s, 'NAKIT',
                    'Mayis 2026 elektrik faturasi', %s, '', %s, 'ELEKTRIK')
        """, (top_gider, gg_id, NOW))
        print(f"3) GIDER 20.05.2026  Elektrik  net={gider_tutar} kdv={kdv_gider} top={top_gider}  (gg_id={gg_id})")

        # --- 4) 21.05.2026 ALIS: EROL HURDA'dan 800 kg KARTON @6 TL, 3 ay vadeli CEK ---
        net4 = 800 * 6  # 4.800
        kdv4 = round(net4 * 0.01, 2)  # 48
        top4 = net4 + kdv4  # 4.848
        cur.execute("""
            INSERT INTO hareketler (tarih, firma_kod, firma_ad, tur, urun_kod, urun_ad,
                                    miktar, birim_fiyat, toplam, kdv_orani, kdv_tutar,
                                    kdvli_toplam, tevkifat_orani, tevkifat_tutar, tevkifatsiz_kdv,
                                    aciklama, created_at, belge_no)
            VALUES ('2026-05-21', 'TED002', 'EROL HURDA TIC.', 'ALIS',
                    'KRT01', 'KARISIK KARTON',
                    800, 6, %s, 1, %s, %s, '0', 0, %s,
                    'Karton alimi - cekli odeme', %s, 'IRS-2025-002')
            RETURNING id
        """, (net4, kdv4, top4, kdv4, NOW))
        hid4 = cur.fetchone()[0]
        # CEK: 3 ay vadeli, VERILEN
        cur.execute("""
            INSERT INTO cekler (cek_no, firma_kod, firma_ad, kesim_tarih, vade_tarih,
                                tutar, durum, cek_turu, kesideci, lehtar, notlar, evrak_tipi)
            VALUES ('1234567', 'TED002', 'EROL HURDA TIC.', '2026-05-21', '2026-08-21',
                    %s, 'PORTFOYDE', 'VERILEN', 'MURAT BAYSAL CEVRE GERI DONUSUM',
                    'EROL HURDA TIC.', 'Karton alimi karsiligi 3 ay vadeli', 'CEK')
            RETURNING id
        """, (top4,))
        cek_id = cur.fetchone()[0]
        print(f"4) ALIS  21.05.2026  KRT01  800kg @6   net={net4} kdv={kdv4} top={top4}  (hareket_id={hid4}, cek_id={cek_id})")

        conn.commit()

        # --- OZET ---
        print()
        print("=" * 60)
        print("OZET")
        print("=" * 60)
        cur.execute("SELECT COUNT(*) FROM hareketler")
        print(f"  hareketler  : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM kasa")
        print(f"  kasa        : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM gelir_gider")
        print(f"  gelir_gider : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM cekler")
        print(f"  cekler      : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM urunler")
        print(f"  urunler     : {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM firmalar")
        print(f"  firmalar    : {cur.fetchone()[0]}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
