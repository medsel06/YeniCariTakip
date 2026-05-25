# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
c = psycopg2.connect(**DB_CONFIG); cur = c.cursor()
cur.execute("SET search_path TO t_6, public")
print("=== TABLO SAYILARI ===")
for t in ('urunler','firmalar','hareketler','kasa','gelir_gider','personel','banka_hesaplari','odeme_takibi'):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t:16s}: {cur.fetchone()[0]}")
print("\n=== URUNLER korundu mu (Huseyin URN-*) ===")
cur.execute("SELECT COUNT(*) FROM urunler WHERE kod LIKE 'URN-%'")
print(f"  URN-* urun karti: {cur.fetchone()[0]} (24 olmali)")
print("\n=== F00X cari korundu mu ===")
cur.execute("SELECT COUNT(*) FROM firmalar WHERE kod LIKE 'F00%'")
print(f"  F00X cari: {cur.fetchone()[0]} (9 olmali)")
cur.execute("SELECT kod FROM firmalar WHERE kod LIKE 'CARI-i%'")
print(f"  Bozuk CARI-i* kalan: {cur.fetchall()}")
print("\n=== STOK (urun bazli, ilk 12) ===")
cur.execute("""SELECT urun_ad,
  SUM(CASE WHEN tur='ALIS' THEN miktar ELSE 0 END) alis,
  SUM(CASE WHEN tur='SATIS' THEN miktar ELSE 0 END) satis,
  SUM(CASE WHEN tur='ALIS' THEN miktar ELSE -miktar END) stok
  FROM hareketler GROUP BY urun_ad ORDER BY urun_ad""")
for r in cur.fetchall():
    print(f"  {str(r[0])[:22]:22s} alis={r[1]:>9,.0f} satis={r[2]:>9,.0f} stok={r[3]:>9,.0f}")
print("\n=== ODEME TAKIBI ===")
cur.execute("SELECT tip, kaynak, COUNT(*), SUM(tutar) FROM odeme_takibi GROUP BY tip, kaynak ORDER BY tip,kaynak")
for r in cur.fetchall():
    print(f"  {r[0]:7s} {r[1]:6s}: {r[2]} kayit, {r[3]:,.2f} TL")
c.close()
