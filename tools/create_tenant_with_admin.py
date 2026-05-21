# -*- coding: utf-8 -*-
"""Yeni tenant (firma) + admin kullanici olusturma scripti.

Kullanim:
    python tools/create_tenant_with_admin.py

Uygulama kok dizininde calistirilmali (db.py'ye erisim icin).
"""
import os
import sys
from datetime import datetime

# Proje kok dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_public_db, create_tenant, init_db
from services.auth_service import hash_password


# -*- coding: utf-8 -*-
# --- KULLANICI / FIRMA BILGILERI ---
TENANT_NAME = "MURAT BAYSAL ÇEVRE GERİ DÖNÜŞÜM LTD.ŞTİ."
VKN = "6241349297"
ADRES = "ÖMERLİ MEVKİİ ARPALIK CAD.NO:70/A MERKEZ/KIRIKKALE"

USERNAME = "huseyin.eyitutun@gmail.com"
FULL_NAME = "Hüseyin Eyitutun"
PASSWORD = "Huseyin0!"
ROLE = "admin"


def main():
    print("[1/5] init_db (public schema)...")
    init_db()

    print(f"[2/5] Mevcut tenant kontrolu: {TENANT_NAME!r}")
    with get_public_db() as conn:
        row = conn.execute("SELECT id, schema_name FROM tenants WHERE name=%s", (TENANT_NAME,)).fetchone()
    if row:
        print(f"  ! Tenant zaten var: id={row['id']} schema={row['schema_name']}. Iptal.")
        return 1

    print(f"[3/5] create_tenant(...) -> yeni firma + schema + business tablolari")
    tenant = create_tenant(TENANT_NAME)
    tenant_id = tenant['id']
    schema_name = tenant['schema_name']
    print(f"  OK tenant_id={tenant_id} schema={schema_name}")

    print(f"[4/5] settings_company UPDATE (firma_adi, vkn_tckn, adres) on schema={schema_name}")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # create_tenant icinde init_tenant_schema settings_company (id=1) ekledi.
    # Direk schema-qualified update yap.
    with get_public_db() as conn:
        conn.execute(
            f"UPDATE {schema_name}.settings_company SET firma_adi=%s, vkn_tckn=%s, adres=%s, updated_at=%s WHERE id=1",
            (TENANT_NAME, VKN, ADRES, now),
        )
    print("  OK settings_company guncellendi")

    print(f"[5/5] users INSERT (username={USERNAME}, tenant_id={tenant_id}, role={ROLE})")
    with get_public_db() as conn:
        exists = conn.execute(
            "SELECT id FROM users WHERE username=%s AND tenant_id=%s",
            (USERNAME, tenant_id),
        ).fetchone()
        if exists:
            print(f"  ! Kullanici zaten var: id={exists['id']}. Sifre guncelleniyor.")
            conn.execute(
                "UPDATE users SET password_hash=%s, full_name=%s, role=%s, is_active=1, updated_at=%s WHERE id=%s",
                (hash_password(PASSWORD), FULL_NAME, ROLE, now, exists['id']),
            )
            user_id = exists['id']
        else:
            cur = conn.execute(
                "INSERT INTO users (username, full_name, password_hash, role, is_active, tenant_id, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, 1, %s, %s, %s) RETURNING id",
                (USERNAME, FULL_NAME, hash_password(PASSWORD), ROLE, tenant_id, now, now),
            )
            user_id = cur.fetchone()['id']
    print(f"  OK user_id={user_id}")

    print()
    print("=" * 60)
    print("BASARILI")
    print(f"  Firma     : {TENANT_NAME}")
    print(f"  Tenant ID : {tenant_id}")
    print(f"  Schema    : {schema_name}")
    print(f"  Username  : {USERNAME}")
    print(f"  Password  : {PASSWORD}")
    print(f"  Role      : {ROLE}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
