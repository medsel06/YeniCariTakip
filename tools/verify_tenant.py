# -*- coding: utf-8 -*-
"""Yeni tenant + user dogrulamasi."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_public_db
from services.auth_service import authenticate

TENANT_ID = 6
USERNAME = "huseyin.eyitutun@gmail.com"
PASSWORD = "Huseyin0!"

with get_public_db() as conn:
    print('--- TENANTS ---')
    for r in conn.execute('SELECT id, name, schema_name, is_active FROM tenants ORDER BY id').fetchall():
        print(f"  {r['id']}: {r['name']} (schema={r['schema_name']}, active={r['is_active']})")

    print()
    print(f'--- USERS (tenant={TENANT_ID}) ---')
    for r in conn.execute('SELECT id, username, full_name, role, is_active FROM users WHERE tenant_id=%s', (TENANT_ID,)).fetchall():
        print(f"  {r['id']}: {r['username']} / {r['full_name']} role={r['role']} active={r['is_active']}")

    print()
    print(f'--- t_{TENANT_ID}.settings_company ---')
    for r in conn.execute(f'SELECT firma_adi, vkn_tckn, adres FROM t_{TENANT_ID}.settings_company').fetchall():
        print(f"  firma : {r['firma_adi']}")
        print(f"  vkn   : {r['vkn_tckn']}")
        print(f"  adres : {r['adres']}")

print()
print('--- authenticate() testi ---')
r = authenticate(USERNAME, PASSWORD, tenant_id=TENANT_ID)
if r:
    print(f"  OK login basarili: user_id={r['id']} role={r['role']} tenant={r['tenant_name']} schema={r['tenant_schema']}")
else:
    print("  FAIL login basarisiz")
