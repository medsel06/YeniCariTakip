"""Tek seferlik migration: gelir_gider.kategori degerlerini 'Ilk Harf Buyuk'
formatina cevirir (TUM tenantlar). Turkce kurallariyla (İŞÇİLİK -> İşçilik).

Kullanim:
    python tools/normalize_kategori.py            # DRY-RUN (sadece rapor + CSV yedek)
    python tools/normalize_kategori.py --apply    # gercekten uygular

Once eski degerleri tools/kategori_backup.csv dosyasina yazar (geri alinabilir),
sadece FARKLI olan kayitlari gunceller. kategori_normalize idempotent oldugu icin
tekrar calistirmak zararsizdir.
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_all_tenants, set_tenant_schema, get_db
from services.gelir_gider_service import kategori_normalize


def main(apply=False):
    tenants = get_all_tenants()
    backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kategori_backup.csv')
    toplam = 0
    with open(backup_path, 'w', newline='', encoding='utf-8-sig') as bf:
        w = csv.writer(bf)
        w.writerow(['schema', 'id', 'eski_kategori', 'yeni_kategori'])
        for t in tenants:
            schema = t.get('schema_name')
            if not schema:
                continue
            set_tenant_schema(schema)
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, kategori FROM gelir_gider "
                    "WHERE kategori IS NOT NULL AND kategori != ''"
                ).fetchall()
                schema_degisen = 0
                for r in rows:
                    eski = r['kategori']
                    yeni = kategori_normalize(eski)
                    if yeni != eski:
                        w.writerow([schema, r['id'], eski, yeni])
                        toplam += 1
                        schema_degisen += 1
                        if apply:
                            conn.execute(
                                "UPDATE gelir_gider SET kategori=? WHERE id=?",
                                (yeni, r['id'])
                            )
                if schema_degisen:
                    print(f"  {schema}: {schema_degisen} kayit")
    mod = 'UYGULANDI' if apply else 'DRY-RUN (uygulanmadi)'
    print(f"\n{mod}: toplam {toplam} kayit degisecek/degisti.")
    print(f"Yedek: {backup_path}")


if __name__ == '__main__':
    main(apply='--apply' in sys.argv)
