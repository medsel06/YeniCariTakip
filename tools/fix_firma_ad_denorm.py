"""Tek seferlik bakim: kopyalanmis (denormalized) firma adlarini Title Case yapar.

İşlemler/Cari vb. ekranlar firma adini hareketler.firma_ad / kasa.firma_ad gibi
kopya sutunlardan gosterir. firmalar.ad duzeltildi ama bu kopyalar eski kaldi.
Bu script tum tenant'larda firma_ad / ciro_firma_ad sutunlarini gunceller.

Calistir (proje kokunden):  python tools/fix_firma_ad_denorm.py
"""
import os
import sys
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _load_env():
    path = os.path.join(_ROOT, '.env')
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

from db import get_db, set_tenant_schema, get_all_tenants  # noqa: E402
from services.cari_service import firma_unvan_duzelt  # noqa: E402

_COLS = ('firma_ad', 'ciro_firma_ad')


def main():
    bak_path = os.path.join(_ROOT, 'tools', f"firma_ad_denorm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv")
    bak = open(bak_path, 'w', encoding='utf-8')
    bak.write("schema\ttablo\tkolon\teski\tyeni\n")
    toplam = 0
    for t in get_all_tenants():
        schema = t.get('schema_name')
        if not schema:
            continue
        set_tenant_schema(schema)
        with get_db() as conn:
            cols = conn.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema=? AND column_name IN ('firma_ad','ciro_firma_ad')",
                (schema,)
            ).fetchall()
            t_degisen = 0
            for c in cols:
                tbl = c['table_name']
                col = c['column_name']
                vals = conn.execute(
                    f"SELECT DISTINCT {col} AS v FROM {tbl} WHERE {col} IS NOT NULL AND {col} <> ''"
                ).fetchall()
                for row in vals:
                    eski = row['v']
                    yeni = firma_unvan_duzelt(eski)
                    if yeni != eski:
                        bak.write(f"{schema}\t{tbl}\t{col}\t{eski}\t{yeni}\n")
                        conn.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (yeni, eski))
                        t_degisen += 1
            print(f"[{schema}] {t.get('name', '')}: {t_degisen} farkli ad guncellendi")
            toplam += t_degisen
    bak.close()
    print(f"TOPLAM: {toplam} farkli firma adi (denormalized) guncellendi")
    print(f"YEDEK: {bak_path}")


if __name__ == '__main__':
    main()
