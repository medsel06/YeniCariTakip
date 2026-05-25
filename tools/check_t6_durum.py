# -*- coding: utf-8 -*-
"""t_6 mevcut durum — neyi koruyacagimizi netlestir."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
c = psycopg2.connect(**DB_CONFIG); cur = c.cursor()
cur.execute("SET search_path TO t_6, public")

print("=== URUNLER (stok kartlari) ===")
cur.execute("SELECT kod, ad, kategori, birim, aktif FROM urunler ORDER BY kod")
for r in cur.fetchall():
    print(f"  {r[0]:14s} | {r[1]} | {r[2]} | {r[3]}")

print("\n=== FIRMALAR (cari) ===")
cur.execute("SELECT kod, ad, is_alani FROM firmalar ORDER BY kod")
for r in cur.fetchall():
    print(f"  {r[0]:18s} | {r[1]} | {r[2]}")

print("\n=== HAREKETLER (urun bazli + created_at araligi) ===")
cur.execute("""SELECT urun_kod, COUNT(*),
  MIN(created_at), MAX(created_at)
  FROM hareketler GROUP BY urun_kod ORDER BY urun_kod""")
for r in cur.fetchall():
    print(f"  urun={r[0] or '(bos)':14s} adet={r[1]:>4} | ilk={str(r[2])[:19]} son={str(r[3])[:19]}")

print("\n=== TABLO SAYILARI ===")
for t in ('hareketler','kasa','gelir_gider','cekler','personel','banka_hesaplari','odeme_takibi'):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t:18s}: {cur.fetchone()[0]}")
c.close()
