# -*- coding: utf-8 -*-
"""Codex denetimi sonrasi 2 duzeltme:
  1. Acilis stok fisi tutarini 0 yap (cift maliyet -> karlilik duzelir, stok yine 0)
  2. odeme_takibi'den KART kalemlerini sil (kart borcu zaten kart hesabinda; cift)
KULLANIM: python tools/fix_v2_post.py [--commit]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from db import DB_CONFIG
COMMIT = '--commit' in sys.argv
c = psycopg2.connect(**DB_CONFIG); c.autocommit = False; cur = c.cursor()
cur.execute("SET search_path TO t_6, public")

# --- 1. Acilis stok fisi tutar -> 0 ---
cur.execute("SELECT COUNT(*), COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE tur='ALIS' AND aciklama LIKE 'AÇILIŞ STOĞU%'")
n1, t1 = cur.fetchone()
print(f"1) Açılış stok fişi: {n1} kayıt, mevcut tutar {t1:,.2f} TL -> 0 yapılacak")

# --- 2. odeme_takibi KART sil ---
cur.execute("SELECT COUNT(*), COALESCE(SUM(tutar),0) FROM odeme_takibi WHERE kaynak='KART'")
n2, t2 = cur.fetchone()
print(f"2) Ödeme takibi KART kalemi: {n2} kayıt, {t2:,.2f} TL -> silinecek")
cur.execute("SELECT COUNT(*), COALESCE(SUM(tutar),0) FROM odeme_takibi WHERE kaynak!='KART'")
n3, t3 = cur.fetchone()
print(f"   Kalan ödeme takibi (CARI vb): {n3} kayıt, {t3:,.2f} TL")

if COMMIT:
    cur.execute("UPDATE hareketler SET toplam=0, kdvli_toplam=0, birim_fiyat=0 WHERE tur='ALIS' AND aciklama LIKE 'AÇILIŞ STOĞU%'")
    cur.execute("DELETE FROM odeme_takibi WHERE kaynak='KART'")
    c.commit()
    print("\n✅ COMMIT edildi.")
    # Dogrulama: karlilik (urun bazli kar) ve kart bakiyeleri
    print("\n=== YENI KARLILIK (urun bazli, ilk 12) ===")
    cur.execute("""SELECT urun_ad,
      SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) alis,
      SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END) satis,
      SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END)-SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) kar
      FROM hareketler GROUP BY urun_ad ORDER BY kar DESC""")
    for r in cur.fetchall():
        print(f"  {str(r[0])[:22]:22s} alis={r[1]:>12,.0f} satis={r[2]:>12,.0f} kar={r[3]:>12,.0f}")
    cur.execute("""SELECT SUM(CASE WHEN tur='SATIS' THEN kdvli_toplam ELSE 0 END)-SUM(CASE WHEN tur='ALIS' THEN kdvli_toplam ELSE 0 END) FROM hareketler""")
    print(f"  TOPLAM KAR: {cur.fetchone()[0]:,.2f} TL")
    print("\n=== ODEME TAKIBI (kalan) ===")
    cur.execute("SELECT tip, kaynak, COUNT(*), SUM(tutar) FROM odeme_takibi GROUP BY tip,kaynak ORDER BY tip,kaynak")
    for r in cur.fetchall():
        print(f"  {r[0]:7s} {r[1]:6s}: {r[2]} kayit, {r[3]:,.2f} TL")
else:
    c.rollback()
    print("\n(DRY-RUN — --commit ile uygula)")
c.close()
