"""SENOL CELIK firmasi icin ornek veriler"""
from db import init_db, set_tenant_schema, get_all_tenants, get_db
from services.auth_service import ensure_default_admin

init_db()
ensure_default_admin()

tenants = get_all_tenants()
senol = [t for t in tenants if 'SENOL' in t['name'].upper() or 'CELIK' in t['name'].upper()]
if not senol:
    print("SENOL CELIK tenant bulunamadi!")
    exit(1)

schema = senol[0]['schema_name']
set_tenant_schema(schema)
print(f"Tenant: {senol[0]['name']} ({schema})")

# Firmalar
with get_db() as conn:
    for kod, ad, tel in [
        ('F001', 'KERESTE DEPOSU MEHMET', '05551112233'),
        ('F002', 'MOBILYA DUNYASI', '05559998877'),
        ('F003', 'AHSAP MARKET', '05553334455'),
        ('F004', 'NAKLIYE HASAN', '05557776655'),
        ('F005', 'ARDIYE DEPO LTD', '05552223344'),
    ]:
        conn.execute("INSERT INTO firmalar (kod, ad, tel) VALUES (%s, %s, %s) ON CONFLICT (kod) DO NOTHING", (kod, ad, tel))
    print("Firmalar OK")

# Urunler
with get_db() as conn:
    for kod, ad, kat, birim in [
        ('URN-001', 'KAVAK KERESTE', 'KERESTE', 'ADET'),
        ('URN-002', 'CEVIZ KERESTE', 'KERESTE', 'ADET'),
        ('URN-003', 'SANDALYE ISKELET', 'YARI MAMUL', 'ADET'),
        ('URN-004', 'SANDALYE KOMPLE', 'MAMUL', 'ADET'),
    ]:
        conn.execute("INSERT INTO urunler (kod, ad, kategori, birim) VALUES (%s, %s, %s, %s) ON CONFLICT (kod) DO NOTHING", (kod, ad, kat, birim))
    print("Urunler OK")

# Alislar
with get_db() as conn:
    for row in [
        ('2026-04-01', 'F001', 'KERESTE DEPOSU MEHMET', 'ALIS', 'URN-001', 'KAVAK KERESTE', 100, 150, 15000, 20, 3000, 18000),
        ('2026-04-03', 'F001', 'KERESTE DEPOSU MEHMET', 'ALIS', 'URN-002', 'CEVIZ KERESTE', 50, 300, 15000, 20, 3000, 18000),
        ('2026-04-05', 'F003', 'AHSAP MARKET', 'ALIS', 'URN-001', 'KAVAK KERESTE', 200, 140, 28000, 20, 5600, 33600),
    ]:
        conn.execute("INSERT INTO hareketler (tarih,firma_kod,firma_ad,tur,urun_kod,urun_ad,miktar,birim_fiyat,toplam,kdv_orani,kdv_tutar,kdvli_toplam) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", row)
    print("Alislar OK")

# Satislar
with get_db() as conn:
    for row in [
        ('2026-04-07', 'F002', 'MOBILYA DUNYASI', 'SATIS', 'URN-004', 'SANDALYE KOMPLE', 20, 500, 10000, 20, 2000, 12000),
        ('2026-04-10', 'F002', 'MOBILYA DUNYASI', 'SATIS', 'URN-004', 'SANDALYE KOMPLE', 30, 500, 15000, 20, 3000, 18000),
    ]:
        conn.execute("INSERT INTO hareketler (tarih,firma_kod,firma_ad,tur,urun_kod,urun_ad,miktar,birim_fiyat,toplam,kdv_orani,kdv_tutar,kdvli_toplam) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", row)
    print("Satislar OK")

# Kasa - cesitli odeme yontemleri
from services.kasa_service import add_kasa
add_kasa({'tarih': '2026-04-02', 'firma_kod': 'F001', 'firma_ad': 'KERESTE DEPOSU MEHMET', 'tur': 'GIDER', 'tutar': 10000, 'odeme_sekli': 'NAKIT', 'aciklama': 'Nakit odeme'})
add_kasa({'tarih': '2026-04-04', 'firma_kod': 'F001', 'firma_ad': 'KERESTE DEPOSU MEHMET', 'tur': 'GIDER', 'tutar': 8000, 'odeme_sekli': 'HAVALE', 'aciklama': 'Banka havalesi', 'banka': 'Halkbank'})
add_kasa({'tarih': '2026-04-08', 'firma_kod': 'F002', 'firma_ad': 'MOBILYA DUNYASI', 'tur': 'GELIR', 'tutar': 12000, 'odeme_sekli': 'NAKIT', 'aciklama': 'Nakit tahsilat'})
add_kasa({'tarih': '2026-04-11', 'firma_kod': 'F002', 'firma_ad': 'MOBILYA DUNYASI', 'tur': 'GELIR', 'tutar': 18000, 'odeme_sekli': 'HAVALE', 'aciklama': 'Banka tahsilat', 'banka': 'Ziraat'})
print("Kasa OK")

# Gelir/Gider
from services.gelir_gider_service import add_gelir_gider
add_gelir_gider({'tarih': '2026-04-02', 'tur': 'GIDER', 'kategori': 'Nakliye', 'tutar': 2000, 'toplam': 2400, 'kdv_orani': 20, 'kdv_tutar': 400, 'odeme_sekli': 'NAKIT', 'firma_kod': 'F004', 'firma_ad': 'NAKLIYE HASAN', 'odeme_durumu': 'ODENDI'})
add_gelir_gider({'tarih': '2026-04-06', 'tur': 'GIDER', 'kategori': 'Ardiye', 'tutar': 3000, 'toplam': 3600, 'kdv_orani': 20, 'kdv_tutar': 600, 'odeme_sekli': '', 'firma_kod': 'F005', 'firma_ad': 'ARDIYE DEPO LTD', 'odeme_durumu': 'ODENMEDI'})
add_gelir_gider({'tarih': '2026-04-09', 'tur': 'GIDER', 'kategori': 'Nakliye', 'tutar': 1500, 'toplam': 1800, 'kdv_orani': 20, 'kdv_tutar': 300, 'odeme_sekli': 'CEK', 'firma_kod': 'F004', 'firma_ad': 'NAKLIYE HASAN', 'odeme_durumu': 'KISMI'})
add_gelir_gider({'tarih': '2026-04-10', 'tur': 'GIDER', 'kategori': 'Elektrik', 'tutar': 800, 'toplam': 960, 'kdv_orani': 20, 'kdv_tutar': 160, 'odeme_sekli': 'NAKIT', 'odeme_durumu': 'ODENDI'})
add_gelir_gider({'tarih': '2026-04-11', 'tur': 'GELIR', 'kategori': 'Fason Iscilik', 'tutar': 5000, 'toplam': 6000, 'kdv_orani': 20, 'kdv_tutar': 1000, 'odeme_sekli': 'NAKIT', 'odeme_durumu': 'ODENDI'})
add_gelir_gider({'tarih': '2026-04-12', 'tur': 'GIDER', 'kategori': 'Nakliye', 'tutar': 2500, 'toplam': 3000, 'kdv_orani': 20, 'kdv_tutar': 500, 'odeme_sekli': 'SENET', 'firma_kod': 'F004', 'firma_ad': 'NAKLIYE HASAN', 'odeme_durumu': 'ODENDI'})
print("Gelir/Gider OK")

# Cekler + Senetler
from services.cek_service import add_cek
add_cek({'cek_no': 'CK-001', 'firma_kod': 'F002', 'firma_ad': 'MOBILYA DUNYASI', 'kesim_tarih': '2026-04-01', 'vade_tarih': '2026-04-15', 'tutar': 5000, 'cek_turu': 'ALINAN', 'evrak_tipi': 'CEK'})
add_cek({'cek_no': 'CK-002', 'firma_kod': 'F002', 'firma_ad': 'MOBILYA DUNYASI', 'kesim_tarih': '2026-04-05', 'vade_tarih': '2026-04-20', 'tutar': 8000, 'cek_turu': 'ALINAN', 'evrak_tipi': 'CEK'})
add_cek({'cek_no': 'CK-003', 'firma_kod': 'F001', 'firma_ad': 'KERESTE DEPOSU MEHMET', 'kesim_tarih': '2026-04-03', 'vade_tarih': '2026-05-03', 'tutar': 15000, 'cek_turu': 'VERILEN', 'evrak_tipi': 'CEK'})
add_cek({'cek_no': 'SN-001', 'firma_kod': 'F003', 'firma_ad': 'AHSAP MARKET', 'kesim_tarih': '2026-04-05', 'vade_tarih': '2026-04-13', 'tutar': 10000, 'cek_turu': 'ALINAN', 'evrak_tipi': 'SENET'})
add_cek({'cek_no': 'SN-002', 'firma_kod': 'F005', 'firma_ad': 'ARDIYE DEPO LTD', 'kesim_tarih': '2026-04-08', 'vade_tarih': '2026-04-18', 'tutar': 3600, 'cek_turu': 'VERILEN', 'evrak_tipi': 'SENET'})
print("Cek/Senet OK")

# Personel
from services.personel_service import add_personel
add_personel({'ad': 'AHMET USTA', 'maas': 25000, 'giris_tarih': '2025-01-01'})
add_personel({'ad': 'MEHMET KALFA', 'maas': 20000, 'giris_tarih': '2025-03-01'})
add_personel({'ad': 'ALI CIRAK', 'maas': 15000, 'giris_tarih': '2025-06-01'})
print("Personel OK")

print("\n=== TAMAMLANDI ===")
