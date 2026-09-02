#!/usr/bin/env python3
"""Haftalik otomatik yedek - her firma AYRI dosyaya.

Cron ile calisir (VPS: /etc/cron.d/cari-takip-yedek, Pazar 02:00 = cumartesiyi
pazara baglayan gece). Uygulamadan bagimsizdir; PM2 servisi durmus olsa da calisir.

Her tenant icin backup_service.create_backup(schema=...) cagrilir; dosya adi
cari_takip_<schema>_<tarih>.sql.gz olur ve Ayarlar ekraninda SADECE o firmaya
gorunur. Firma basina son 8 yedek tutulur (~2 ay).

Elle calistirma:
    cd /var/www/cari-takip && ./venv/bin/python3 tools/haftalik_yedek.py
"""
import os
import sys
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_all_tenants  # noqa: E402
from services.backup_service import create_backup  # noqa: E402


def main():
    basla = datetime.now()
    print(f"[{basla:%Y-%m-%d %H:%M:%S}] Haftalik yedek basliyor")
    try:
        tenants = get_all_tenants()
    except Exception:
        print('HATA: tenant listesi alinamadi')
        traceback.print_exc()
        return 1

    basarili, hatali = 0, 0
    for t in tenants:
        schema = t.get('schema_name')
        ad = t.get('name', '?')
        if not schema:
            continue
        try:
            yol = create_backup(schema=schema)
            boyut_mb = round(os.path.getsize(yol) / (1024 * 1024), 2)
            print(f"  OK   {schema:6s} {ad[:40]:40s} -> {os.path.basename(yol)} ({boyut_mb} MB)")
            basarili += 1
        except Exception as e:
            print(f"  HATA {schema:6s} {ad[:40]:40s} -> {type(e).__name__}: {e}")
            hatali += 1

    sure = (datetime.now() - basla).total_seconds()
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Bitti: {basarili} basarili, {hatali} hatali, {sure:.1f} sn")
    return 0 if hatali == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
