# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
c = psycopg2.connect(**DB_CONFIG); cur = c.cursor()
cur.execute("SET search_path TO t_6, public")
for t in ('hareketler','kasa','gelir_gider','personel','personel_hareket','banka_hesaplari','firmalar','urunler'):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t:20s}: {cur.fetchone()[0]}")
print("\n--- NAKIT KASA bakiye (banka_hesap_id IS NULL) ---")
cur.execute("SELECT COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar END),0), COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar END),0) FROM kasa WHERE banka_hesap_id IS NULL")
g,ci = cur.fetchone(); print(f"  giris={g:,.2f} cikis={ci:,.2f} bakiye={g-ci:,.2f}")
print("\n--- BANKA/KART bakiyeleri ---")
cur.execute("SELECT id, ad, tip FROM banka_hesaplari ORDER BY id")
for bid, ad, tip in cur.fetchall():
    cur.execute("SELECT COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar END),0)-COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar END),0) FROM kasa WHERE banka_hesap_id=%s",(bid,))
    print(f"  [{tip}] {ad}: {cur.fetchone()[0]:,.2f}")
print("\n--- ORTAK CARI net (kasa GELIR-GIDER) ---")
cur.execute("SELECT firma_kod, COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar END),0)-COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar END),0) FROM kasa WHERE firma_kod LIKE 'ORT-%' GROUP BY firma_kod ORDER BY firma_kod")
for k,net in cur.fetchall(): print(f"  {k}: {net:,.2f}")
print("\n--- STOK: MOTOSIKLET PARCASI ---")
cur.execute("SELECT COALESCE(SUM(CASE WHEN tur='ALIS' THEN miktar END),0), COALESCE(SUM(CASE WHEN tur='SATIS' THEN miktar END),0) FROM hareketler WHERE urun_kod='MOTO-PARCA'")
al,sa = cur.fetchone(); print(f"  alis={al:,.2f} kg  satis={sa:,.2f} kg  kalan={al-sa:,.2f} kg")
c.close()
