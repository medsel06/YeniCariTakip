# -*- coding: utf-8 -*-
"""MKE motor maliyetini satilan urunlere dagit (zarar yok).
  1. MKE ALIS kayitlarini (MOTOSIKLET PARCASI'ndaki MKE) hareketlerden kaldir
  2. Her acilis stok fisi tutarini = o urunun satis tutarina esitle (kar 0)
  -> her urun maliyet=satis, kar 0, stok 0; MKE para cikisi kasa'da kalir.
KULLANIM: python tools/fix_mke_maliyet.py [--commit]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
COMMIT = '--commit' in sys.argv
c = psycopg2.connect(**DB_CONFIG); c.autocommit = False; cur = c.cursor()
cur.execute("SET search_path TO t_6, public")

# 1. MKE ALIS kayitlari
cur.execute("SELECT COUNT(*), COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE tur='ALIS' AND aciklama ILIKE '%MKE%'")
n1, t1 = cur.fetchone()
print(f"1) MKE ALIS kaydı: {n1} kayıt, {t1:,.2f} TL -> hareketlerden silinecek (para kasa'da kalır)")

# 2. Acilis fisleri (urun bazli satisa esitlenecek)
cur.execute("SELECT COUNT(*) FROM hareketler WHERE tur='ALIS' AND aciklama LIKE 'AÇILIŞ STOĞU%'")
print(f"2) Açılış fişi: {cur.fetchone()[0]} kayıt -> tutar = ürün satış tutarı (kâr 0)")

if COMMIT:
    # 1. MKE alis sil
    cur.execute("DELETE FROM hareketler WHERE tur='ALIS' AND aciklama ILIKE '%MKE%'")
    # 2. Her acilis fisini o urunun satis tutarina esitle
    cur.execute("""
        UPDATE hareketler h SET
            toplam = s.satis, kdvli_toplam = s.satis,
            birim_fiyat = CASE WHEN h.miktar>0 THEN s.satis/h.miktar ELSE 0 END
        FROM (SELECT urun_kod, SUM(kdvli_toplam) satis FROM hareketler WHERE tur='SATIS' GROUP BY urun_kod) s
        WHERE h.tur='ALIS' AND h.aciklama LIKE 'AÇILIŞ STOĞU%' AND h.urun_kod = s.urun_kod
    """)
    c.commit()
    print("\n✅ COMMIT edildi.")
    print("\n=== YENI KARLILIK (urun bazli) ===")
    cur.execute("""SELECT urun_ad,
      SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) alis,
      SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) satis,
      SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END)-SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) kar,
      SUM(CASE WHEN tur='ALIS' THEN miktar ELSE -miktar END) stok
      FROM hareketler GROUP BY urun_ad ORDER BY satis DESC""")
    for r in cur.fetchall():
        print(f"  {str(r[0])[:22]:22s} maliyet={r[1]:>11,.0f} satis={r[2]:>11,.0f} kar={r[3]:>10,.0f} stok={r[4]:>9,.0f}")
    cur.execute("SELECT SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END)-SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END), SUM(CASE WHEN tur='ALIS' THEN miktar ELSE -miktar END) FROM hareketler")
    k, stok = cur.fetchone()
    print(f"  TOPLAM KAR: {k:,.2f} TL | TOPLAM STOK: {stok:,.0f} kg")
    # Nakit/banka degismedi dogrula
    cur.execute("SELECT SUM(CASE WHEN tur='GELIR' THEN tutar ELSE -tutar END) FROM kasa WHERE banka_hesap_id IS NULL")
    print(f"  NAKIT (degismemeli): {cur.fetchone()[0]:,.2f} TL")
else:
    c.rollback()
    print("\n(DRY-RUN — --commit ile uygula)")
c.close()
