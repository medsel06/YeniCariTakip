# -*- coding: utf-8 -*-
"""t_6 schema'sina eksik migration kolonlarini ekle.

Bug: db.py:_col_exists() schema filtresi yapmadigi icin yeni tenant'larda
ALTER TABLE ADD COLUMN atlanmis. Bu script PostgreSQL'in
ADD COLUMN IF NOT EXISTS syntax'i ile idempotent olarak duzeltir.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from db import DB_CONFIG

SCHEMA = "t_6"

MIGRATIONS = [
    # (table, column, type_default)
    ("settings_company", "ucret_periyodu",  "TEXT DEFAULT 'AYLIK'"),
    ("settings_company", "uretim_takibi",   "INTEGER DEFAULT 0"),
    ("personel_aylik",   "hafta",           "INTEGER DEFAULT 0"),
    ("personel_hareket", "hafta",           "INTEGER DEFAULT 0"),
    ("cekler",           "evrak_tipi",      "TEXT DEFAULT 'CEK'"),
    ("urunler",          "desi_degeri",     "NUMERIC(10,2) DEFAULT 0"),
    ("hareketler",       "belge_no",        "TEXT DEFAULT ''"),
    ("firmalar",         "aktif",           "INTEGER DEFAULT 1"),
    ("urunler",          "aktif",           "INTEGER DEFAULT 1"),
    ("kasa",             "kategori",        "TEXT DEFAULT ''"),
]


def main():
    print(f"Migrating schema: {SCHEMA}")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public")
        for table, column, type_default in MIGRATIONS:
            # Once schema-aware kontrol
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
                (SCHEMA, table, column),
            )
            exists = cur.fetchone() is not None
            if exists:
                print(f"  - {table}.{column}: zaten var, atlandi")
                continue
            sql = f"ALTER TABLE {SCHEMA}.{table} ADD COLUMN IF NOT EXISTS {column} {type_default}"
            cur.execute(sql)
            print(f"  + {table}.{column}: EKLENDI")
        conn.commit()
        print("OK migration tamamlandi.")

        # Dogrulama: hareketler kolonlari
        print()
        print(f"--- {SCHEMA}.hareketler kolonlari ---")
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name='hareketler' ORDER BY ordinal_position",
            (SCHEMA,),
        )
        for r in cur.fetchall():
            print(f"  {r[0]:20s} {r[1]}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
