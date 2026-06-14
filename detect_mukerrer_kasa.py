"""SALT-OKUNUR tespit: mukerrer kasa kayitlari (ayni gelir_gider_id ile >1 satir).
Hicbir sey SILMEZ, sadece raporlar. Tum tenant schema'larini tarar.
"""
from db import get_public_db, set_tenant_schema, get_db

with get_public_db() as conn:
    tenants = conn.execute(
        "SELECT id, name, schema_name FROM tenants WHERE is_active=1 ORDER BY name"
    ).fetchall()

print(f"=== {len(tenants)} aktif tenant taraniyor ===\n")

toplam_grup = 0
toplam_fazla = 0

for t in tenants:
    schema = t['schema_name']
    ad = t['name']
    set_tenant_schema(schema)
    with get_db() as conn:
        # mukerrer gruplar: ayni gelir_gider_id ile >1 kasa satiri
        gruplar = conn.execute('''
            SELECT gelir_gider_id, COUNT(*) AS cnt
            FROM kasa
            WHERE gelir_gider_id IS NOT NULL
            GROUP BY gelir_gider_id
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC, gelir_gider_id DESC
        ''').fetchall()

        if not gruplar:
            continue

        grup_sayisi = len(gruplar)
        fazla = sum(g['cnt'] - 1 for g in gruplar)  # silinecek fazla satir sayisi
        toplam_grup += grup_sayisi
        toplam_fazla += fazla

        print(f"### {ad}  (schema: {schema})")
        print(f"    Mukerrer grup: {grup_sayisi} | Silinecek fazla satir: {fazla}")

        # ilk 3 grubu ornek goster
        for g in gruplar[:3]:
            ggid = g['gelir_gider_id']
            satirlar = conn.execute('''
                SELECT id, tarih, tur, tutar, odeme_sekli, aciklama
                FROM kasa WHERE gelir_gider_id=%s ORDER BY id
            ''', (ggid,)).fetchall()
            print(f"    -- gelir_gider_id={ggid} -> {len(satirlar)} kasa satiri:")
            for s in satirlar:
                print(f"        kasa.id={s['id']} | {s['tarih']} | {s['tur']} | "
                      f"{s['tutar']} | {s['odeme_sekli']} | {s['aciklama']}")
        print()

print("=== OZET ===")
print(f"Toplam mukerrer grup: {toplam_grup}")
print(f"Toplam silinecek fazla satir: {toplam_fazla}")
print("(Bu script HICBIR SEY SILMEDI - sadece tespit.)")
