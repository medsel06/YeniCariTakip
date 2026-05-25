# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
c = psycopg2.connect(**DB_CONFIG); cur = c.cursor()
cur.execute("SET search_path TO t_6, public")
print("--- TUM FIRMALAR (t_6) ---")
cur.execute("SELECT kod, ad, is_alani, aktif FROM firmalar ORDER BY ad, kod")
for r in cur.fetchall():
    print(f"  kod={r[0]:12s} | ad={r[1]} | alan={r[2]} | aktif={r[3]}")
print("\n--- AYNI AD birden fazla (duplicate) ---")
cur.execute("SELECT ad, COUNT(*), STRING_AGG(kod, ', ') FROM firmalar GROUP BY ad HAVING COUNT(*)>1")
d = cur.fetchall()
if not d:
    print("  (ad bazinda duplicate yok)")
for r in d:
    print(f"  ad='{r[0]}' x{r[1]} -> kodlar: {r[2]}")
c.close()
