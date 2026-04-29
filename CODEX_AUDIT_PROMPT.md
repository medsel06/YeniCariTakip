# Codex Görev: Cari Takip Mali Doğruluk Denetimi

## ROL
Sen senior yazılım mühendisi + mali müşavir gözüyle çalışan bir denetçisin.
Bu projede dönem filtreleme, devir hesabı, bakiye doğruluğu ile ilgili bir kök bug
tespit edildi. Aynı kök nedenden gelen **tüm benzer hataları** bul, listele,
mali risk seviyesine göre önceliklendir.

## PROJE BAĞLAMI
- **Yol:** `F:\StokTakipAlseWeb` (lokalde) — yapı: `pages/*.py` (NiceGUI sayfaları),
  `services/*.py` (iş mantığı), `db.py` (PostgreSQL multi-tenant), `layout.py` (ortak helper),
  `yeni-tasarim/Cari Takip v3 (Trend).html` (yeni React UI), `services/api_routes.py` (JSON API).
- **DB:** PostgreSQL multi-tenant (her firma için `t_X` schema), `set_tenant_schema()` ile
  request-scoped tenant context.
- **Tarih kolonları:** TEXT tipinde (`'2026-04-15'` formatı). Bazı kayıtlarda `tarih=''` veya `NULL`.
- **Tabloların tarih kolonu:** `hareketler.tarih`, `kasa.tarih`, `cekler.kesim_tarih/vade_tarih`,
  `gelir_gider.tarih/vade_tarih`, `cari_mutabakat.mutabakat_tarih`, `audit_log.created_at`,
  `notifications.created_at`, `personel_hareket.tarih`, `uretim.tarih`, `personel.giris_tarih/cikis_tarih`.

## KÖK BUG — Detaylı Açıklama

### Yer
- `services/cari_service.py:242-260` (`_safe_date_parts`, `get_cari_bakiye_list`)
- `layout.py:513-537` (`donem_secici`)
- `pages/cari.py:18` (state başlangıç değeri)

### Bug 1 — `_safe_date_parts` yıl-only desteklemiyor
```python
def _safe_date_parts(yil, ay):
    if not yil or not ay:        # ← İkisi de zorunlu
        return None, None         # ← Yıl varsa bile None döner
    return int(yil), int(ay)
```
Sonuç: "Yıl 2026 + Ay Tümü" çağrısı backend'e `(None, None)` olarak gidiyor — yıl filtresi tamamen kayboluyor, **TÜM zamanlar** dönüyor.

### Bug 2 — `donem_secici` ay=0 ise yıl da iptal ediliyor
```python
def _changed(_=None):
    y = sel_yil.value
    a = sel_ay.value
    on_change(y if a != 0 else None, a if a != 0 else None)  # ← BUG
```
"Ay Tümü" (a=0) seçilince UI yıl bilgisini de NULL olarak gönderiyor.

### Bug 3 — `pages/cari.py:18` state-UI desync
```python
state = {'yil': now.year, 'ay': now.month}  # 2026, 4
```
Ama `donem_secici(include_all=True)` UI'da default `Ay: Tümü` gösteriyor. State ↔ UI senkron değil.
Kullanıcı dokunmazsa backend Nisan 2026 sorgular, UI "Tümü" gösterir → **mali rapor yanılgısı**.

### Bug 4 — Devir kavramı mali açıdan yanlış uygulanıyor
```python
if yil and ay:
    prefix = f'{yil:04d}-{ay:02d}'
    date_flt = f" AND tarih >= '{prefix}-01' AND tarih < '{prefix}-32'"
    devir_flt = f" AND tarih < '{prefix}-01'"   # ← Sadece ay öncesi
```

**Mali tanım:**
- "2026 Nisan" görünümü → Devir = Mart 31 sonu bakiyesi (= 2026-04-01 öncesi tüm hareketler) ✓ DOĞRU
- "2026 Yıllık" görünümü → Devir = **2025 sonu bakiyesi** (= 2026-01-01 öncesi tüm hareketler)
  → Bu durum **HİÇ DESTEKLENMİYOR**.
  Sonuç: Bu yıl yeni başlayan firma (örn. F042 Doğan Arıcılık, sadece 2026'da hareket görmüş)
  için 2026 Ocak/Şubat/Mart hareketleri yanlışlıkla "Devir" olarak görünüyor.

### Bug 5 — Boş tarihli kayıtlar
T_3 schema'sındaki `hareketler` tablosunda 9 kayıt `tarih=''` (NULL). Bu kayıtlar:
- Mizanı bozar (toplam tutar gerçek dönem dışında kalır)
- KDV beyannamesinde tehlikeli
- `tarih < ...` veya `tarih >= ...` filtreleri NULL'u dışlar (fakat tip TEXT olduğu için
  string karşılaştırması NULL davranışı belirsiz)

### Bug 6 — Kapanmış firmalar listede
`pages/cari.py:24-31`: Backend hareketsiz firmaları filtrelemiş olsa bile UI tekrar ekler:
```python
for f in firmalar:
    if f['kod'] not in bakiye_kodlar:
        bakiyeler.append({...alis:0, satis:0, ...})
```
Mali müşavir gözüyle: yıl içinde hareketsiz + bakiye=0 firmalar listede gereksiz görünüm kalabalığı.

---

## GÖREV

### 1. Aynı pattern'in olduğu TÜM yerleri bul
Aşağıdaki kategorilerdeki **her bir kullanım noktasını** denetle:

#### A. `donem_secici` kullanan tüm sayfalar
```bash
grep -rn "donem_secici" pages/
grep -rn "_safe_date_parts" services/
```
Her sayfa için kontrol et:
- State default `now.month` mi `None` mı? (state-UI desync var mı?)
- `include_all=True` ise `Ay Tümü` seçildiğinde yıl filtresi düzgün çalışıyor mu?
- Yıl-only sorgu desteklenmiş mi backend'de?
- Aylık vs Yıllık vs Tüm Zamanlar üç moddan kaç tanesi destekleniyor?

#### B. Tarih filtreli SQL sorguları
```bash
grep -rn "AND tarih" services/
grep -rn "tarih >=" services/
grep -rn "tarih <" services/
```
Her sorgu için:
- Boş tarih (`tarih = ''` veya `NULL`) filtreleniyor mu? Mali açıdan dışlanmalı.
- Devir hesabı yıl-only modunda doğru mu?
- Yuvarlama: tutar kolonları `numeric` mi `double` mu? Akümülasyon hatası var mı?
- KDV/Tevkifat ayrımı: `kdvli_toplam` vs `toplam` (matrah) — hangi rapor hangisini kullanıyor?

#### C. Bakiye/Mizan hesaplayan tüm fonksiyonlar
- `cari_service.get_cari_bakiye_list`
- `cari_service.get_cari_ekstre`
- `cari_service.get_firma_risk_durumu`
- `cari_service.get_alacak_yaslandirma`
- `kasa_service.get_kasa_bakiye`
- `gelir_gider_service.get_gelir_gider_ozet`
- `oneri_service.get_tahsilat_onerileri`
- `oneri_service.get_urun_karlilik_ozeti`
- `personel_service.get_aylik_ozet` / `get_donem_ozet`

Her birinde:
- Devir kavramı doğru mu uygulanıyor?
- Yıl-only mod var mı?
- Mizan kapatma garantisi var mı? (ΣBorç = ΣAlacak = ΣBakiye)
- Boş tarihli kayıtlar dahil mi/hariç mi?

#### D. v3 (Trend) yeni UI'da aynı pattern var mı?
- `yeni-tasarim/Cari Takip v3 (Trend).html` içinde:
  - `Ekstre`, `CariList`, `Hareketler`, `Kasa`, `GelirGider`, `Bilanco`, `Karlilik` sayfaları
  - JavaScript filter mantığı (yıl/ay state)
  - API çağrıları yıl-only desteklenmediği için bug ne kadar yansıyor?

#### E. PDF/Excel raporları
- `services/pdf_service.py` — rapor başlığında dönem doğru mu?
- `services/api_routes.py` — `/api/cariler`, `/api/hareketler` vs. yıl-only param desteklenmiş mi?
- PDF çıktısında "Dönem: Ocak-Aralık 2026" ifadesi backend'in hangi sorguya karşılık geldiği ile uyumlu mu?

### 2. Ek mali doğruluk kontrolleri

Bu konularda da kod tarayıp risk varsa raporla:

- **Mizan denetimi:** Hiçbir yerde "ΣBorç = ΣAlacak" otomatik kontrol var mı?
  Yoksa eklenmesi gereken yerleri öner.
- **KDV/Tevkifat ayrımı:** Hareketler tablosunda `kdvli_toplam`, `kdv_tutar`, `tevkifat_tutar`,
  `tevkifatsiz_kdv` kolonları var. Cari listede `kdvli_toplam` kullanılıyor — bu KDV
  beyannamesi ile uyumlu mu? Tevkifatlı işlemlerde matrah ayrı tutulmalı.
- **Vade/Tahakkuk:** Çek vadesi `cekler.vade_tarih`, gelir/gider vadesi `gelir_gider.vade_tarih`.
  Vadesi geçmiş çek/fatura aranıyor mu? Yaşlandırma raporu (`get_alacak_yaslandirma`) doğru çalışıyor mu?
- **gg_gider/gg_gelir cari'ye karışması:** `cari_service.get_cari_bakiye_list:342-343`:
  ```python
  'alis': alis + gg_gider,
  'satis': satis + gg_gelir,
  ```
  Mali açıdan gelir/gider faturaları cari hesabıyla aynı bakiyeye eklenir mi? (Gerekirse cari
  faturaları + gg ödemeleri tek bakiyede olabilir, ama bu açık dökümlü olmalı). Tartışılmalı.
- **Cari risk limiti:** `get_firma_risk_durumu` — limit aşımı uyarısı doğru mu?
  39 firmanın kaçında `risk_limiti=0` (yani limit yok)? Bunlar risk uyarısı kapsamı dışında mı?

### 3. Veri tutarlılığı kontrolleri

`db.py` ve schema:
- Tarih kolonları `TEXT` tipinde — bu PostgreSQL'de sıralama/karşılaştırma için OK ama
  formatı standart değilse (örn. '2026-4-5' vs '2026-04-05') yanlış sıralama olur.
  Kontrol: tüm hareketlerin tarih formatı `YYYY-MM-DD` mi?
- Tutar kolonları: `kdvli_toplam`, `tutar`, `bakiye` vs. `numeric(20,2)` mi `double` mu?
  Float ise akümülasyon hatası riski.
- Foreign key kısıtları: `kasa.cek_id` → `cekler.id`. Eski ALSE PLASTİK (t_3) verisinde
  orphan kayıt var mı?
- Aynı firma kodu farklı yazımla iki kez eklenmiş olabilir mi? (örn. "F006" ve "f006")
- Aynı belge_no ile mükerrer hareket var mı?

### 4. Çıktı formatı

Aşağıdaki yapıda Markdown raporu üret:

```markdown
# Cari Takip — Mali Doğruluk Denetim Raporu

## Özet
- Tarama edilen dosya sayısı: N
- Tespit edilen bug sayısı: M (kritik X, orta Y, düşük Z)

## Bulgular

### 🔴 Kritik (mali doğruluk bozar)
| # | Dosya:satır | Bug | Mali etki | Öneri |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

### 🟡 Orta (yanlış görünüm/UX)
...

### 🟢 Düşük (kod kalitesi)
...

## Önerilen düzeltme paketi
1. ...
2. ...

## Test senaryoları
- Senaryo 1: ...
- Senaryo 2: ...

## Açık sorular (kullanıcı kararı bekleniyor)
- gg_gelir/gg_gider cari bakiyesine dahil mi olsun?
- Boş tarihli 9 kaydın akıbeti ne olsun (silme/düzeltme)?
```

### 5. Kısıtlamalar
- **Hiçbir dosyayı değiştirme.** Sadece tarama + rapor.
- **Push yok**, commit yok, sadece okuma.
- Rapor: `F:\StokTakipAlseWeb\CODEX_AUDIT_REPORT.md` dosyasına yaz.

## ÇALIŞMA YÖNTEMİ
1. Önce `pages/`, `services/`, `layout.py`, `db.py` dizinlerini gez
2. `donem_secici` ve `_safe_date_parts` kullanan tüm yerleri çıkar
3. Tarih filtreli SQL sorgularını tara
4. Mali hesap fonksiyonlarını dökümante et
5. Bulguları kategorize et, dosya:satır referansları ile rapor yaz
6. Sonunda mali müşavir + senior yazılım mühendisi perspektifinden 5-10 kritik öneri sırala

## NOT
Detaylı SQL sorguları çalıştırmana gerek yok — sadece kod analizi yeter. Schema bilgisi
yukarıda verildi. Multi-tenant context (`set_tenant_schema()`) tüm sorguların başında
çalışır, bu yüzden FROM kelimesinden sonra schema prefix'i (`t_X.`) yok — bu beklenen davranış.
