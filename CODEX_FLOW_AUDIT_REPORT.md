# Cari/Stok/Kasa/Gelir-Gider/Cek Akis Denetimi

Tarih: 2026-04-29

Not: Canli PostgreSQL baglantisi `194.146.50.147:5432` icin `connection refused` dondu. Bu rapor kod akisi uzerinden hazirlandi; mevcut veri uzerinde sayisal backfill/duble kayit kontrolu DB erisimi acilinca ayrica kosulmali.

## Ozet

Kullanicinin "cek kayitlari cariye yansimiyor, ciro da yansimiyor" tespiti dogru.

Mevcut cari bakiye su kaynaklardan hesaplanir:

- `hareketler`: ALIS/SATIS
- `gelir_gider`: GIDER/GELIR
- `kasa`: GIDER/GELIR

`cekler` tablosu cari bakiye ve ekstre hesaplarina hic dahil edilmez. Bu yuzden cek/senet kaydi olusturmak tek basina cariyi etkilemez. `CIRO_EDILDI` durumu da `cekler.ciro_firma_kod` alanina yazilir, fakat cari hesap bu alani okumadigi icin ciro edilen firmaya otomatik odeme yansimaz.

## Kritik Bulgular

### 1. Cek/senet kaydi cariye yansimiyor

Dosyalar:

- `services/cek_service.py:add_cek`
- `services/cari_service.py:get_cari_bakiye_list`
- `services/cari_service.py:get_cari_ekstre`

`add_cek()` sadece `cekler` ve `cek_hareketleri` tablolarina yazar. Cari hesap `cekler` kaynagini okumadigi icin:

- Musteriden alinan cek, musteri bakiyesini azaltmaz.
- Firmaya verilen cek, firma bakiyesini azaltmaz.
- Cari ekstrede cek/senet satiri gorunmez.

### 2. Ciro akisi iki farkli davranir ve biri cariye hic yansimaz

Dosyalar:

- `services/cek_service.py:change_durum`
- `pages/cekler.py:open_durum_dialog`
- `pages/kasa.py:open_add_dialog`

`pages/cekler.py` uzerinden "Durum Degistir > Ciro Edildi" yapilirsa sadece `cekler` satirina `ciro_firma_kod/ad` yazilir. Cari etki yoktur.

`pages/kasa.py` uzerinden "Ciro Ceki" secilirse `change_durum(..., CIRO_EDILDI)` sonrasi ayrica `kasa` kaydi acilir. Bu cari hesaba yansir, fakat ciro aslinda nakit hareketi olmadigi icin kasa bakiyesini de oynatir. Yani bir akista eksik, diger akista kasa/cari anlamlari karisiktir.

### 3. Cek tahsil/odeme durumlari gelecekte cift sayima acik

Dosya:

- `services/cek_service.py:change_durum`

`TAHSIL_EDILDI` ve `ODENDI` durumlarinda otomatik `kasa` kaydi olusturuluyor. Eger cek kaydi cari deftere dogru sekilde ilk kayit aninda yansitilirsa, bu kasa kayitlari cariye tekrar yansimamali. Aksi halde:

- Alinan cek: ilk kayitta tahsilat + tahsil edildi durumunda tekrar tahsilat
- Verilen cek: ilk kayitta odeme + odendi durumunda tekrar odeme

olur.

Dogru modelde tahsil/odendi durumu sadece finansal/kasa/banka hareketidir; cari etki ilk cek alma/verme aninda olmalidir.

### 4. Gelir-gider yeni kayit akisi mantikli, ama duzenleme bagli kasayi guncellemiyor

Dosyalar:

- `pages/gelir_gider.py`
- `services/gelir_gider_service.py:update_gelir_gider`
- `services/gelir_gider_service.py:delete_gelir_gider`

Yeni gelir/gider kaydinda odenen tutar varsa `gelir_gider` + bagli `kasa` kaydi olusuyor. Bu model cari acisindan dogru:

- Toplam gider/gelir cari borc/alacak olusturur.
- Odenen kisim kasa ile cariyi kapatir.
- Kalan kisim cari bakiyede kalir.

Fakat duzenleme modunda sadece `gelir_gider` guncelleniyor. Bagli `kasa.gelir_gider_id` kaydi guncellenmiyor. Tutar, firma, tarih veya odeme durumu degisirse kasa ve cari sapabilir. Silme tarafinda bagli kasa siliniyor; duzenleme tarafinda da ayni eslestirme gerekir.

### 5. v3 Gelir-Gider "Odendi" kasa kaydi olusturmuyor

Dosyalar:

- `yeni-tasarim/Cari Takip v3 (Trend).html:NewGGModal`
- `services/api_routes.py:api_gelir_gider_create`

v3 modalinde "Odendi - Kasa hareketi olustur" yaziyor, ama `/api/gelir-gider` endpoint'i sadece `gelir_gider` kaydi ekliyor. Bagli kasa kaydi yaratmiyor.

Ayrica v3 payload `tur: "gelir" / "gider"` gonderiyor; servis ve SQL tarafinda `GELIR/GIDER` bekleniyor. Bu kayitlar raporlarda/cari hesapta gorunmeyebilir veya yanlis siniflanabilir.

### 6. v3 Kasa cek/ciro alanlari backend tarafinda yok sayiliyor

Dosyalar:

- `yeni-tasarim/Cari Takip v3 (Trend).html:KasaModal`
- `services/api_routes.py:api_kasa_create`

v3 kasa modal'i `cek_turu`, `cek_no`, `cek_vade_tarih`, `ciro_cek_id` gonderiyor. Backend ise bunlari islemiyor; sadece `kasa_service.add_kasa(data)` cagiriyor. Sonuc:

- "Firma ceki" secilirse cekler tablosunda cek olusmaz.
- "Ciro ceki" secilirse secili cek `CIRO_EDILDI` olmaz.
- Cari/kasa/cek portfoy durumlari birbirinden kopar.

### 7. Firma veya urun silme gecmis finansal/stok hareketlerini ekrandan dusurebilir

Dosyalar:

- `services/cari_service.py:delete_firma`
- `services/stok_service.py:delete_urun`
- `services/cari_service.py:get_cari_bakiye_list`
- `services/stok_service.py:get_stok_list`

Firma silinince `hareketler`, `kasa`, `gelir_gider`, `cekler` kayitlari kodla kalir. Fakat cari liste `FROM firmalar f` ile basladigi icin silinen firmanin gecmis bakiyesi cari listeden kaybolur.

Urun silinince hareketler kalir, fakat stok listesi `FROM urunler u` ile basladigi icin silinen urunun gecmis stok hareketleri stok listesinden kaybolur.

Mali/stok sisteminde silme yerine pasife alma tercih edilmeli; hareketi olan firma/urun fiziksel silinmemeli.

### 8. Donem filtreleri yil-only modunda tutarsiz

Dosyalar:

- `layout.py:donem_secici`
- `services/cari_service.py:_safe_date_parts`
- `services/kasa_service.py:_date_filter`
- `services/gelir_gider_service.py:_date_filter`

"2026 + Tumu" secimi yil filtresi gibi degil, tum zaman gibi calisabiliyor. Bu audit prompt'undaki ana mali dogruluk sorunudur.

### 9. Cari bakiye formulu birden cok yerde kopyalanmis

Dosyalar:

- `services/cari_service.py:get_cari_bakiye_list`
- `services/cari_service.py:get_firma_risk_durumu`
- `services/cari_service.py:get_risk_uyarilari`
- `services/cari_service.py:get_alacak_yaslandirma`
- `services/oneri_service.py:get_tahsilat_onerileri`

Risk, tahsilat onerisi, yaslandirma ve cari liste ayni kaynaklardan ayni sekilde hesaplanmiyor. `gelir_gider` bazi fonksiyonlarda var, bazilarinda yok. Cek/senet eklendiginde bu fark daha da buyur.

Tek merkezi cari defter fonksiyonu olmadan rakamlar ekrandan ekrana degisir.

### 10. KDV %18 yok

Dosya:

- `pages/hareketler.py`

KDV secenekleri `%0, %1, %10, %20`. Eski kayitlari duzeltmek icin `%18` eklenmeli. Planda gecen `%8` de gerekiyorsa eklenebilir.

## Dogru Uygulama Modeli

Ana karar: `kasa` tablosu hem "nakit/banka hareketi" hem "cari kapama hareketi" gibi kullaniliyor. Cek/senet icin bu iki kavram ayrilmali.

En guvenli yol:

1. `cari_service` icinde tek bir merkezi `get_cari_ledger(firma_kod=None, yil=None, ay=None)` fonksiyonu olustur.
2. Cari liste, ekstre, risk, tahsilat onerisi ve yaslandirma sadece bu ledger'dan beslensin.
3. Ledger kaynaklari:
   - Stok hareketleri: `hareketler`
   - Gelir/gider tahakkuku: `gelir_gider`
   - Dogrudan nakit/havale tahsilat/odeme: `kasa`
   - Cek/senet cari etkileri: `cekler` + `cek_hareketleri`
4. Cek/senet cari etkileri event bazli olussun:
   - ALINAN cek/senet ilk kayit: eski firma icin tahsilat etkisi.
   - VERILEN cek/senet ilk kayit: firma icin odeme etkisi.
   - CIRO_EDILDI: ciro edilen firma icin odeme etkisi.
   - IADE_EDILDI/KARSILIKSIZ: onceki cari etkinin ters kaydi.
   - TAHSIL_EDILDI/ODENDI: cari etkisi yok; sadece kasa/banka/portfoy durumudur.
5. Cek tahsil/odeme aninda olusan kasa kayitlari cariye ikinci kez yansimamali. Bunun icin:
   - ya `kasa` tablosuna `cari_etki INTEGER DEFAULT 1` eklenir ve cek tahsil/odeme kasa satirlarinda `cari_etki=0` yazilir,
   - ya da cari ledger `kasa.cek_id IS NOT NULL` olan cek kapanis kayitlarini dislar ve ciro etkisini `cekler` kaynagindan okur.
6. Ciro sadece Kasa sayfasina bagli kalmamali. `change_durum(..., CIRO_EDILDI)` calistigi her yerde ayni cari etkisi gorunmeli.
7. v3 `/api/kasa` ve `/api/gelir-gider` endpointleri eski UI ile ayni servis davranisini kullanmali; frontend'in gonderdigi ekstra cek/ciro alanlari backend'de islenmeli veya frontend bu alanlari gondermemeli.

## Oncelikli Duzeltme Sirasi

1. Donem filtresi yil-only fix.
2. Merkezi cari ledger.
3. Cek/senet eventlerini ledger'a ekle.
4. `kasa` cek kapanis satirlarinda cari cift sayimi engelle.
5. Ciro akisini `change_durum` uzerinden tek hale getir.
6. Gelir-gider duzenlemede bagli kasa kaydini senkronize et.
7. Firma/urun silmeyi pasife alma veya hareket varsa engelleme haline getir.
8. v3 API uyumsuzluklarini kapat.
9. KDV %18/%8 seceneklerini ekle.

## Canli VPS/DB Kontrolu

VPS icinden DB baglantisi calisti. Tenant listesi:

- `t_1` Varsayilan Firma
- `t_2` SENOL CELIK
- `t_3` ALSE PLASTIK

### ALSE PLASTIK (`t_3`) canli bulgular

- Ciro edilmis alinan cek: 4 adet, toplam 467.120 TL.
- Bu 4 ciro cek icin ciro edilen firmaya bagli kasa/cari etkisi yok.
- Verilen ve `KESILDI` durumunda kalan cek: 6 adet, toplam 415.500 TL.
- Bu 6 verilen cek icin bagli kasa/cari etkisi yok.
- `cekler` tablosunda kasa linki olmayan toplam cek: 10 adet, toplam 882.620 TL.
- Gelir-gider odendi/kismi kayitlarda bagli kasa eksigi canli veride gorunmedi.
- Gelir-gider bagli kasa tutar uyumsuzlugu canli veride gorunmedi.
- Silinmis/eksik firma referanslari:
  - `hareketler`: F002 icin 52 kayit, toplam 8.470.237,50 TL.
  - `kasa`: F002 icin 22 kayit, toplam 628.297 TL.
  - `cekler`: F038 ve F039 icin 2 kayit, toplam 22.700 TL.
- Silinmis/eksik urun referanslari:
  - `hareketler`: UX007 icin 1 kayit, UX070 icin 2 kayit.
- Bos tarih:
  - `hareketler`: 9 kayit.
  - `kasa`: 4 kayit.
  - `cekler.kesim_tarih`: 6 kayit.

Canli ciro detaylari:

- Cek 01, 125.000 TL: HAK PLASTIK -> SALIMOGLU GERI DONUSUM.
- Cek 02, 140.000 TL: HAK PLASTIK -> SALIMOGLU GERI DONUSUM.
- Cek 03, 102.120 TL: HAK PLASTIK -> SALIMOGLU GERI DONUSUM.
- Cek 04, 100.000 TL: HM CANPOLATLAR -> SALIMOGLU GERI DONUSUM.

Bu canli sonuc, cek/senet ve ciro icin backfill gerektigini dogrular. Backfill dogrudan kasa satiri basarak degil, once dry-run raporla ve merkezi cari ledger kurulduktan sonra yapilmalidir.

### Diger tenantlar

- `t_2` SENOL CELIK: cek ve akista belirgin canli bulgu yok.
- `t_1` Varsayilan Firma: `BEKLEMEDE` durumlu 7 alinan cek ve cok sayida bos tarihli hareket/kasa kaydi var. Bu tenant muhtemelen eski/demo veri; uretim kararindan once ayrica teyit edilmeli.
