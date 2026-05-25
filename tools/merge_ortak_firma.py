# -*- coding: utf-8 -*-
"""Migration'da olusan ORT-* ortak cari duplicate'lerini mevcut F00X kartlarina birlestir.
  ORT-MURAT  -> F008 (Murat Baykal)
  ORT-OZKAN  -> F007 (Özkan Bulut)
  ORT-HUSEYIN-> F009 (Hüseyin Eyitutun)
Kasa hareketlerini tasir, sonra bos ORT-* kartlari siler.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG

COMMIT = '--commit' in sys.argv
ESLEME = [('ORT-MURAT', 'F008', 'Murat Baykal'),
          ('ORT-OZKAN', 'F007', 'Özkan Bulut'),
          ('ORT-HUSEYIN', 'F009', 'Hüseyin Eyitutun')]

c = psycopg2.connect(**DB_CONFIG); c.autocommit = False; cur = c.cursor()
cur.execute("SET search_path TO t_6, public")

# Hedef F kodlari gercekten var mi dogrula
for eski, yeni, ad in ESLEME:
    cur.execute("SELECT ad FROM firmalar WHERE kod=%s", (yeni,))
    r = cur.fetchone()
    print(f"{eski} -> {yeni}: hedef kart {'VAR (' + r[0] + ')' if r else 'YOK!'}")
    cur.execute("SELECT COUNT(*) FROM kasa WHERE firma_kod=%s", (eski,))
    print(f"    tasinacak kasa kaydi: {cur.fetchone()[0]}")

if COMMIT:
    for eski, yeni, ad in ESLEME:
        cur.execute("UPDATE kasa SET firma_kod=%s, firma_ad=%s WHERE firma_kod=%s", (yeni, ad, eski))
        # gelir_gider/hareketler de olabilir (guvenlik)
        cur.execute("UPDATE gelir_gider SET firma_kod=%s, firma_ad=%s WHERE firma_kod=%s", (yeni, ad, eski))
        cur.execute("UPDATE hareketler SET firma_kod=%s, firma_ad=%s WHERE firma_kod=%s", (yeni, ad, eski))
        cur.execute("DELETE FROM firmalar WHERE kod=%s", (eski,))
    c.commit()
    print("\n✅ COMMIT: ORT-* birlestirildi ve silindi.")
    cur.execute("SELECT ad, COUNT(*) FROM firmalar GROUP BY ad HAVING COUNT(*)>1")
    dup = cur.fetchall()
    print(f"Kalan duplicate: {dup if dup else 'YOK ✓'}")
else:
    c.rollback()
    print("\n(DRY-RUN — --commit ile uygula)")
c.close()
