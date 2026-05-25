# -*- coding: utf-8 -*-
"""Banka modulu migration: tum tenant schema'larina banka_hesaplari tablosu
+ kasa.banka_hesap_id/transfer_id/is_transfer kolonlarini ekler (idempotent)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import init_db, init_tenant_schema, get_public_db


def main():
    print("[public] init_db...")
    init_db()
    with get_public_db() as conn:
        tenants = conn.execute("SELECT id, name, schema_name FROM tenants ORDER BY id").fetchall()
    for t in tenants:
        sch = t['schema_name']
        if not sch:
            continue
        print(f"[{sch}] {t['name']} -> init_tenant_schema (idempotent)")
        init_tenant_schema(sch)
    print()
    # Dogrulama
    with get_public_db() as conn:
        for t in tenants:
            sch = t['schema_name']
            if not sch:
                continue
            cols = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name='kasa' "
                "AND column_name IN ('banka_hesap_id','transfer_id','is_transfer')",
                (sch,)
            ).fetchall()
            tbl = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name='banka_hesaplari'",
                (sch,)
            ).fetchone()
            colset = sorted([c['column_name'] for c in cols])
            print(f"  {sch}: kasa kolonlari={colset}  banka_hesaplari_tablosu={'VAR' if tbl else 'YOK'}")
    print("OK migration tamamlandi.")


if __name__ == "__main__":
    main()
