# -*- coding: utf-8 -*-
"""t_6'da Odeme Plani'ndan gelen gelir_gider kayitlarini goster."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
c = psycopg2.connect(**DB_CONFIG); cur = c.cursor()
cur.execute("SET search_path TO t_6, public")
cur.execute("""SELECT COUNT(*),
  COALESCE(SUM(CASE WHEN tur='GIDER' THEN tutar END),0),
  COALESCE(SUM(CASE WHEN tur='GELIR' THEN tutar END),0)
  FROM gelir_gider WHERE kategori='ÖDEME PLANI'""")
n, gid, gel = cur.fetchone()
print(f"ÖDEME PLANI kayitlari: {n} | Borç(GIDER)={gid:,.2f} | Alacak(GELIR)={gel:,.2f}")
print("\n--- odeme_durumu dagilimi ---")
cur.execute("SELECT odeme_durumu, COUNT(*), COALESCE(SUM(tutar),0) FROM gelir_gider WHERE kategori='ÖDEME PLANI' GROUP BY odeme_durumu")
for r in cur.fetchall():
    print(f"  {r[0] or '(bos)':12s}: {r[1]} kayit, {r[2]:,.2f} TL")
print("\n--- ilk 15 kayit ---")
cur.execute("SELECT tarih, tur, aciklama, tutar, odeme_durumu, vade_tarih FROM gelir_gider WHERE kategori='ÖDEME PLANI' ORDER BY tarih LIMIT 15")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]:5s} | {str(r[2])[:35]:35s} | {r[3]:>12,.2f} | {r[4]} | vade={r[5]}")
c.close()
