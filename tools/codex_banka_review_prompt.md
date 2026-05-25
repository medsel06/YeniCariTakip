# GÖREV: Banka Modülü Tasarım Planını İncele ve Doğrula

Sen bir kıdemli backend mimarısın. Aşağıdaki banka modülü ekleme planını, **mevcut kod tabanını okuyarak** denetleyeceksin. Kod YAZMA — sadece planı kontrol et, hata/risk/eksik bul, somut düzeltme öner.

## Proje bağlamı
- PostgreSQL **multi-tenant** (her firma ayrı schema: `t_1`, `t_2`, ... `public` schema'da `tenants` + `users`).
- Backend: NiceGUI (Python). Önemli dosyalar:
  - `db.py` — schema/tablo tanımları (`_create_business_tables`), connection pool, `_col_exists`
  - `services/kasa_service.py` — kasa CRUD + `get_kasa_bakiye`
  - `services/gelir_gider_service.py` — gelir/gider, `ODENDI` ise otomatik bağlı kasa kaydı (`gelir_gider_id`)
  - `services/cari_service.py` — cari bakiye hesabı (kasa GELIR/GIDER + cekler üzerinden)
  - `services/cek_service.py` — çek/senet
  - `pages/kasa.py`, `pages/gelir_gider.py`, `pages/cekler.py`, `pages/cari*.py`
  - `layout.py` — sol menü

## Mevcut durum (benim tespitim — DOĞRULA)
- `kasa` tablosu = TÜM para hareketlerinin tek defteri. Doğrudan kasa kayıtları + `gelir_gider_id` bağlı + `cek_id` bağlı kayıtlar hep buraya yazılıyor.
- `kasa` tablosunda `banka TEXT` kolonu VAR ama hiçbir yerde doldurulmuyor/gösterilmiyor.
- UI'da ayrı banka sayfası yok, ödeme şeklinde banka hesabı seçimi yok.
- Cari bakiye `cari_service` içinde `kasa` (GELIR/GIDER) + `cekler` toplanarak hesaplanıyor.

## ÖNERİLEN MİMARİ (kontrol et)
1. `kasa` tablosu tek para defteri olarak KALIR. Yeni kolon: `kasa.banka_hesap_id INTEGER NULL`.
   - `banka_hesap_id IS NULL` → NAKİT kasa
   - `banka_hesap_id` dolu → o banka hesabı
2. Yeni master tablo `banka_hesaplari (id, ad, tip[BANKA/KREDI_KARTI], iban, acilis_bakiye NUMERIC, aktif, created_at)`.
3. Banka bakiyesi = `acilis_bakiye + Σ(tur=GELIR) − Σ(tur=GIDER)` (o `banka_hesap_id`'ye ait kasa kayıtları).
4. Nakit kasa bakiyesi = sadece `banka_hesap_id IS NULL` olan kayıtlar.

## İLİŞKİ MODELİ (kontrol et)
**Tek bacaklı** (bankada tek hareket, karşı taraf başka modülde): Cari tahsilat(+)/ödeme(−), Çek alınan-tahsil(+)/verilen-ödeme(−), Stoklu mal satış(+)/alış(−), Gelir(+)/Gider(−).

**Çift bacaklı / transfer** (iki kayıt, biri çıkış biri giriş, `transfer_id` ile bağlı):
- Nakit yatırma: NAKİT(−) → BANKA(+)
- Nakit çekme: BANKA(−) → NAKİT(+)
- Havale/EFT/Virman: BANKA A(−) → BANKA B(+)

## FAZ PLANI
- **Faz 1**: `banka_hesaplari` tablosu + `kasa.banka_hesap_id` kolonu + `banka_service.py` (CRUD/bakiye/hareket) + `pages/banka.py` + menüye "Banka".
- **Faz 2**: Ödeme şekli sadeleştir (NAKİT/BANKA/ÇEK/SENET — Havale+EFT → tek "BANKA"). "BANKA" seçilince tanımlı hesaplardan **dropdown** açılır. Etkilenen: kasa.py, gelir_gider.py, cari ödeme/tahsilat, cekler.py. Seçim `kasa.banka_hesap_id`'ye yazılır.
- **Faz 3**: Excel migration (kasa + banka sheet → kasa tablosu).

## SENDEN İSTENENLER (KONTROL LİSTESİ)
Mevcut kodu OKUYARAK şu soruları yanıtla, her birine somut dosya/satır referansı ver:

1. **Çift sayım riski**: Banka kayıtları `kasa` tablosuna `tur=GELIR/GIDER` ile yazılınca, `cari_service` cari bakiye hesabı bu kayıtları İKİNCİ KEZ sayar mı? (Banka tahsilatı hem bankaya girer hem cari alacağı kapatmalı, ama cari bakiyeyi bozmamalı.) `get_kasa_bakiye` toplam bakiyeyi nasıl etkiler?

2. **Transfer çift kayıt**: Nakit↔Banka ve Banka↔Banka transferinde iki kasa kaydı atmak doğru mu? Bu iki kayıt `tur=GELIR`/`GIDER` olunca cari bakiyeye veya gelir/gider raporlarına yanlış yansır mı? Transferin cari/gelir-gider'e SIZMAMASI için ne gerekir? (örn. özel `tur` değeri veya `firma_kod` boş + flag)

3. **`get_kasa_bakiye` ve raporlar**: Bu fonksiyon banka kayıtlarını da topluyorsa, "nakit kasa bakiyesi" artık yanlış olur. `banka_hesap_id IS NULL` filtresi eklemek gerekir mi? Hangi başka sorgular (`karlilik`, `raporlar`, `dashboard`) etkilenir?

4. **Ödeme şekli sadeleştirme migration riski**: Mevcut kayıtlarda `odeme_sekli` = 'HAVALE'/'EFT' olanlar var mı (diğer tenant'larda)? 'BANKA'ya indirgersek geçmiş veri bozulur mu? Geriye dönük migration gerekli mi?

5. **multi-tenant**: Yeni tablo/kolon `_create_business_tables`'a nasıl eklenmeli? `_col_exists` ile idempotent migration (mevcut t_1/t_2/t_3/t_6 schema'larına da uygulanacak şekilde). Az önce `_col_exists` schema-aware yapıldı (`current_schema()` filtresi) — bu yeni kolon migration'ı için yeterli mi?

6. **Çek bağlantısı**: `cekler` tablosunda çek ödeme/tahsilatı banka seçiliyse, `kasa` kaydının `banka_hesap_id`'si nasıl set edilecek? `cek_service`'te çek durumu değişince (TAHSIL/ÖDENDİ) oluşan kasa kaydına banka bilgisi nasıl taşınır?

7. **Silme/güncelleme tutarlılığı**: Banka kaydı veya transfer silinince ne olmalı? `transfer_id` ile bağlı çift kayıt birlikte silinmeli mi? Mevcut `delete_kasa` / gelir_gider sync mantığını incele.

8. **Eksik gördüğün herhangi bir şey**: Planda atladığım, riskli veya daha basit yapılabilecek bir nokta var mı?

## ÇIKTI FORMATI
- Her kontrol maddesi için: ✅ Plan doğru / ⚠️ Risk var / ❌ Hatalı — kısa gerekçe + dosya:satır referansı + öneri.
- Sonda: "KRİTİK DÜZELTMELER" listesi (varsa) ve genel onay/ret.
- Türkçe yaz.
