"""Tek seferlik bakim: tum aktif tenant'larda firmalar.ad -> Title Case.

Noktali kisaltmalar (A.Ş., Ltd., Şti.) korunur (firma_unvan_duzelt).
Calistir (proje kokunden):  python tools/fix_firma_titlecase.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def _load_env():
    """db.py os.environ kullaniyor; .env'i elle yukle (dotenv yoksa)."""
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


def main():
    from datetime import datetime
    bak_path = os.path.join(_ROOT, 'tools', f"firma_titlecase_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv")
    bak = open(bak_path, 'w', encoding='utf-8')
    bak.write("schema\tkod\teski_ad\tyeni_ad\n")
    toplam = 0
    for t in get_all_tenants():
        schema = t.get('schema_name')
        if not schema:
            continue
        set_tenant_schema(schema)
        with get_db() as conn:
            rows = conn.execute("SELECT kod, ad FROM firmalar").fetchall()
            degisen = 0
            for r in rows:
                eski = r['ad'] or ''
                yeni = firma_unvan_duzelt(eski)
                if yeni != eski:
                    bak.write(f"{schema}\t{r['kod']}\t{eski}\t{yeni}\n")
                    conn.execute("UPDATE firmalar SET ad=? WHERE kod=?", (yeni, r['kod']))
                    degisen += 1
            print(f"[{schema}] {t.get('name', '')}: {degisen}/{len(rows)} firma duzeltildi")
            toplam += degisen
    bak.close()
    print(f"TOPLAM: {toplam} firma adi guncellendi")
    print(f"YEDEK: {bak_path}")


if __name__ == '__main__':
    main()
