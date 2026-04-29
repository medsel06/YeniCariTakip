# Cari Takip - Mali Dogruluk Denetim Raporu

## Ozet
- Tarama tarihi: 2026-04-29
- Kapsam: `pages/*.py`, `services/*.py`, `layout.py`, `db.py`, `yeni-tasarim/Cari Takip v3 (Trend).html`
- Tarama edilen dosya sayisi: 42
- Tespit edilen bulgu sayisi: 27 (kritik 12, orta 12, dusuk 3)
- Yontem: Kod analizi. Canli SQL/veri sorgusu calistirilmadi.

## Bulgular

### Kritik (mali dogruluk bozar)

| # | Dosya:satir | Bug | Mali etki | Oneri |
|---|---|---|---|---|
| K1 | `layout.py:513-533` | `donem_secici(include_all=True)` icin "Ay=Tumu" secilince `on_change(None, None)` gonderiliyor; secili yil de iptal ediliyor. | Kullanici "2026 / Tumu" beklerken tum zamanlar raporlanir. Cari, dashboard, gelir-gider ve kasa ekranlarinda donem yanilgisina yol acar. | `ay=0` degerini "yil bazli" anlaminda koru: `on_change(y, None)`; tum zamanlar icin ayri bir mod/deger kullan. |
| K2 | `services/cari_service.py:242-260`, `351-362` | `_safe_date_parts()` yil-only desteklemiyor; yil var ay yoksa `(None, None)` donduruyor. | `/api/cariler?yil=2026` veya UI "2026 / Tumu" cagrisi tum zamanlara duser. Yillik mizan/bakiye guvenilmez olur. | Tarih filtresini uc modlu yap: tum zamanlar, yil, ay. Yardimci fonksiyon `yil` varsa int'e cevirip `ay=None` kabul etmeli. |
| K3 | `pages/cari.py:18`, `59`; `pages/dashboard.py:45-46`, `231`; `pages/gelir_gider.py:28-29`, `461`; `pages/kasa.py:20-21`, `397` | Sayfa state'i mevcut ayla basliyor, fakat `donem_secici(include_all=True)` UI'da "Ay=Tumu" gosteriyor. | Kullanici ekranda tum ayi/yili gordugunu sanarken backend mevcut ay sorgular. Bu rapor basligi olmadan ciddi mali yorum hatasi uretir. | State default ile UI default ayni olmali. Ya state `{'yil': now.year, 'ay': None}` olsun ya da UI mevcut ayi gostersin. |
| K4 | `services/cari_service.py:253-260`, `292-325` | Cari bakiye listesinde yillik devir kavrami yok. Sadece ay secilirse `tarih < YYYY-MM-01` devir hesaplaniyor; yil-only hic desteklenmiyor. | "2026 yillik" raporda devir 2025 kapanisi olmali; mevcut kod bunu uretemedigi icin ocak-mart hareketleri devir/donem ayrimina yanlis dagilabilir. | Yil-only modda `date_flt: YYYY-01-01 <= tarih < YYYY+1-01-01`, `devir_flt: tarih < YYYY-01-01` olmali. |
| K5 | `services/cari_service.py:274-286`, `303-315`, `381-422`, `430-440`; `services/kasa_service.py:7-12`; `services/gelir_gider_service.py:22-26` | Tarih filtreleri bos/NULL/bozuk tarihleri acikca dislamiyor ve TEXT tarih formatini dogrulamiyor. | Bos tarihli hareketler bazi modlarda tum zamanlara dahil olur, donem raporlarinda disarida kalir; mizan ve KDV donemleri tutarsizlasir. | Tum tarihli mali sorgulara `tarih IS NOT NULL AND tarih <> '' AND tarih ~ '^\d{4}-\d{2}-\d{2}$'` standardi eklenmeli; kayit girisinde validasyon zorunlu olmali. |
| K6 | `services/cari_service.py:427-448`, `474-478` | `get_cari_ekstre()` devir hesapliyor ama devir satiri/ilk bakiye olarak kullanmiyor; bakiye her zaman 0'dan basliyor. | Aylik ekstrede onceki donem bakiyesi gorunmez; satir bakiyesi gercek cari bakiyeyi degil sadece secili donem akisini gosterir. | Devir satiri geri getirilmeli veya ilk kümülatif bakiye `devir` ile baslatilmali; PDF/ekran basliginda devir ve donem net ayrilmali. |
| K7 | `services/cari_service.py:103-131`, `135-165`; `services/oneri_service.py:14-30` | Risk ve tahsilat onerisi bakiyesi `gelir_gider` kaynakli cari borc/alacaklari disliyor; cari liste ise `gg_gider/gg_gelir` ekliyor. | Cari listede limit asimi gorunen firma risk uyarilarinda dusuk/normal gorunebilir veya tersi olur. Tahsilat onceligi yanlis siralanir. | Bakiye hesaplari tek merkezi fonksiyona alinmali; cari liste, risk ve tahsilat onerisi ayni borc/alacak formülünü kullanmali. |
| K8 | `services/cari_service.py:169-230` | Alacak yaslandirma sadece satislari tarihe gore dagitiyor; tahsilatlari faturalara FIFO/kapama mantigiyla baglamiyor, vade tarihini kullanmiyor, bozuk tarihi 0-30 gune atiyor. | Vadesi gecmis alacak yeni gibi gorunebilir; tahsil edilmis eski faturalar hala yaslandirma kovalarinda kalabilir. | Yaslandirma acik kalem/FIFO kapama veya belge bazli kapama mantigiyla, vade tarihi varsa ona gore hesaplanmali; parse edilemeyen tarih rapor disi/hata listesi olmali. |
| K9 | `services/api_routes.py:321-327` | Dashboard KPI tum carileri filtresiz aliyor, `kasa_bakiye` icin beklenen `toplam_giris` anahtari yok (`get_kasa_bakiye` `giris` donduruyor). | API dashboard'da "bu ay tahsilat" 0 gorunebilir; toplam alacak/borc donem secicisinden bagimsiz tum zamanlar olur. | API sozlesmesi duzeltilmeli: `giris` kullanilmali ve KPI parametreleri donem bilgisi almalidir. |
| K10 | `yeni-tasarim/Cari Takip v3 (Trend).html:3043-3061` | v3 ilk veri yuklemede `/api/cariler`, `/api/hareketler`, `/api/kasa`, `/api/gelir-gider` parametresiz cagriliyor. | Cari liste ve dashboard tum zamanlar verisiyle acilir; yil/ay donemi kavrami backend'e hic gitmez. | v3 icin global donem state'i ekle; API cagrilarina `?yil=&ay=` parametresi veya acik `periodMode` gonder. |
| K11 | `yeni-tasarim/Cari Takip v3 (Trend).html:538-545`, `3045`, `3071` | v3 ekstre `get_cari_ekstre` yerine `/api/hareketler` verisinden `TX` uretiyor; kasa satirlarinda `tur` TAHSILAT/ODEME oldugu icin `borc/alacak` 0 kaliyor, gelir-gider ve devir zaten yok. | v3 ekstre, dashboard "bu ay tahsilat" ve cari detay donem toplamlarinda tahsilat/odeme tutarlari eksik veya sifir gorunur. | Ekstre icin `/api/cariler/{kod}/ekstre` kullan; kasa/gelir-gider/devir dahil tek kaynak backend ekstre olmalı. |
| K12 | `yeni-tasarim/Cari Takip v3 (Trend).html:2028` | Tahsilat/odeme modalinda varsayilan tarih sabit `2026-04-24`. | Yeni kasa tahsilat/odeme kayitlari bugunun tarihi yerine eski tarihle kaydedilebilir; donem raporlari dogrudan bozulur. | `new Date().toISOString().slice(0,10)` kullan; tarih inputunu zorunlu dogrula. |

### Orta (yanlis gorunum / UX / rapor guveni)

| # | Dosya:satir | Bug | Mali etki | Oneri |
|---|---|---|---|---|
| O1 | `pages/cari.py:24-31` | Backend hareket/bakiye filtresi yapsa bile UI tum firmasiz/sifir bakiyeli firmalari tekrar ekliyor. | Yil icinde hareketsiz ve bakiyesi sifir cariler listeyi sisirir; kullanici aktif cari sayisini yanlis algilar. | "Sifir/hareketsizleri goster" filtresi eklenmeli; varsayilan raporda gizlenmeli. |
| O2 | `services/kasa_service.py:7-30`, `113-169`; `services/gelir_gider_service.py:22-48` | `_date_filter()` yil-only desteklemiyor; yil var ay yoksa filtresiz tum zamanlar. | Kasa ve gelir/gider yillik rapor istekleri tum zamanlar sonucuna duser. | Ortak `build_period_filter(col, yil, ay, mode)` yardimcisi kullanilmali. |
| O3 | `pages/dashboard.py:14-31` | Dashboard ozetinde yil-only yok; `date_filter` sadece ay varsa `LIKE` uyguluyor. | "2026 / Tumu" dashboard kartlari tum zamanlar veya mevcut ayla karisir. | Dashboard da merkezi donem filtresini kullanmali. |
| O4 | `services/cari_service.py:337-343` | `gg_gider/gg_gelir`, cari alis/satis kolonlarina sessizce ekleniyor. | Gelir/gider faturasi ile stok alis/satis ayni kolonda toplandigi icin matrah/fatura turu ayrimi kaybolur. | Kolonlari ayir veya raporda "ticari hareket" ve "gelir/gider cari etkisi" olarak acik dokum ver. |
| O5 | `services/pdf_service.py:188-265`, `306-349`, `395-452` | PDF raporlarinda donem bilgisi parametre olarak yer almiyor; basliklar veri filtresinin hangi doneme ait oldugunu soylemiyor. | Ekran filtresi hataliysa PDF bunu gizler; "Nisan 2026" mi "tum zamanlar" mi belirsiz kalir. | PDF servisleri `donem_label` alsin ve baslik/alt bilgiye yazsin. |
| O6 | `services/cek_service.py:176-190`, `pages/cek_takvim.py:71-72` | Cek vade karsilastirmalari TEXT tarih uzerinden; bos/bozuk vade tarihleri ayri hata olarak raporlanmiyor. | Vadesi gecmis evraklar uyarilardan dusabilir veya siralama yanlis olabilir. | Vade tarihine format validasyonu ekle; bos/bozuk vade icin ayri "eksik vade" uyarisi uret. |
| O7 | `services/gelir_gider_service.py:39-48`, `pages/gelir_gider.py:358-386` | Odenmemis/kismi gelir-gider kayitlarinin vade raporu yok; `vade_tarih` kaydediliyor ama aktif uyari/aging yok. | Vadesi gecmis gider/gelir faturasi takip disinda kalir. | `gelir_gider` icin vadesi gecen/kismi/odenmemis liste ve dashboard uyarisi ekle. |
| O8 | `services/oneri_service.py:34-43` | En eski satis tarihi parse edilemezse gecikme 0 kabul ediliyor. | Tarihi bozuk eski alacak tahsilat onerisinde dusuk oncelik alir. | Parse hatalarini "tarih sorunlu" olarak yukselt; 0 gun varsayma. |
| O9 | `services/api_routes.py:114-116`, `138-140`, `175-177`, `225-232`, `262-269` | API yil/ay parametrelerini aliyor ama servislerin bir kismi yil-only modunu desteklemiyor. | Frontend/API kullanicisi parametre verdigini sanir, sonuc tum zamanlar olabilir. | API katmaninda donem modunu valide et; desteklenmeyen kombinasyonu 400 veya dogru yil filtresiyle isle. |
| O10 | `yeni-tasarim/Cari Takip v3 (Trend).html:1291` | v3 Gelir/Gider filtre referans tarihi sabit `2026-04-24`. | "30g/90g" filtreleri zaman ilerledikce gercek bugune gore degil sabit tarihe gore calisir. | `new Date()` kullan; tercihen server-side donem filtresine tasin. |
| O11 | `yeni-tasarim/Cari Takip v3 (Trend).html:1394-1396`, `2209-2212` | v3 Hareketler/Kasa filtrelerinde bos tarih `null` yapiliyor ve donem filtresinden geciyor. | Bos tarihli kayitlar her ay/yil gorunumunde gorunebilir. | Bos tarihli kayitlari donem raporundan ayir; "tarih eksik" uyari listesine al. |
| O12 | `yeni-tasarim/Cari Takip v3 (Trend).html:866`, `1984-1985` | v3'te bazi donem etiketleri statik (`01.01.2026 - 24.04.2026`, `01.04.2026 - 30.04.2026`). | Ekran etiketi gercek filtreyle uyusmayabilir; PDF/Excel ciktisi yanlis donem algisi yaratir. | Etiketleri aktif donem state'inden uret; statik tarih kullanma. |

### Dusuk (kod kalitesi / uzun vadeli risk)

| # | Dosya:satir | Bug | Mali etki | Oneri |
|---|---|---|---|---|
| D1 | `db.py:70-79` | PostgreSQL `Decimal` degerleri wrapper katmaninda `float`'a cevriliyor. | DB kolonlari `NUMERIC` olsa da uygulama tarafinda kucuk yuvarlama sapmalari birikebilir. | Para hesaplarinda `Decimal` korunmali; UI formatlama en sonda yapilmali. |
| D2 | `db.py:348-383`, `517-533`, `536-594` | Tarih kolonlari `TEXT`, format icin CHECK constraint yok. | `2026-4-5` gibi kayitlar string siralama/filtrelemede yanlis konumlanir. | `DATE` tipine migrasyon veya en azindan regex CHECK + input validasyonu ekle. |
| D3 | `db.py:370-383`, `517-533` | `kasa.cek_id`, `kasa.gelir_gider_id`, `gelir_gider.firma_kod`, `hareketler.firma_kod` icin foreign key yok. | Orphan kayitlar cari/kasa/mutabakat raporlarini sessizce bozabilir. | Eski veri temizlendikten sonra FK ekle; gecis icin orphan kontrol raporu calistir. |

## Donem Secici Kullanim Matrisi

| Sayfa | State default | `include_all` | Backend yil-only | Durum |
|---|---:|---:|---:|---|
| `pages/cari.py` | `now.year, now.month` | Evet | Hayir | Kritik desync + yil-only kayip |
| `pages/cari_detay.py` | `None, None` | Evet | Hayir | UI default tutarli, fakat yil-only secim tum zamanlara duser; devir ekstrede kullanilmiyor |
| `pages/dashboard.py` | `now.year, now.month` | Evet | Hayir | Kritik desync |
| `pages/gelir_gider.py` | `now.year, now.month` | Evet | Hayir | Kritik desync |
| `pages/hareketler.py` | `now.year, now.month` | Hayir | Gerekmiyor | Aylik mod tutarli, fakat ortak helper yil-only desteklemiyor |
| `pages/kasa.py` | `now.year, now.month` | Evet | Hayir | Kritik desync |
| `pages/loglar.py` | `donem_secici` import var, kullanim yok | - | - | Temizlik |
| `yeni-tasarim/Cari Takip v3 (Trend).html` | Bilesene gore degisiyor | Kismen | Hayir | Parametresiz API + client-side filtre; ekstre/kasa tutarlari eksik |

## Tarih Filtreli SQL Riskleri

- `services/cari_service.py`: `tarih >= ... AND tarih < ...` ve `tarih < ...` elle f-string ile kuruluyor. Degerler int'e zorlandigi icin injection riski dusuk, fakat yil-only ve bos tarih standardi yok.
- `services/kasa_service.py` / `services/gelir_gider_service.py`: `LIKE 'YYYY-MM%'` yalniz aylik calisiyor; yil-only yok.
- `services/kdv_service.py`: Aylik KDV matrah/KDV/tevkifat ayrimi daha dogru kurulmus; ancak tarih kolonu TEXT ve validasyon yok.
- `services/audit_service.py`: `created_at` metin araligi kullaniyor; mali rapor degil ama tarih format standardina bagimli.
- `services/cek_service.py`: `vade_tarih` metin karsilastirmasi kullaniyor; format bozuksa vade uyarisi yanlis olur.
- `yeni-tasarim/Cari Takip v3 (Trend).html`: Donem filtreleri cogunlukla client-side ve parametresiz API uzerinden calisiyor; bos tarihli kayitlar donem filtresini asabiliyor.

## Mali Dogruluk Degerlendirmesi

- Mizan denetimi: Kodda otomatik `SUM(borc) = SUM(alacak)` veya cari alt toplam tutarlilik kontrolu bulunmadi. En azindan cari listesi, ekstre ve mutabakat kaydi oncesinde "kaynak bazli toplamlar" kontrol edilmeli.
- KDV/tevkifat: `kdv_service.py` matrah icin `toplam`, KDV icin `kdv_tutar`, tevkifat icin `tevkifat_tutar` kullaniyor; bu iyi. Cari bakiye ise `kdvli_toplam` kullaniyor; ticari cari bakiye icin normal olabilir, fakat KDV beyannamesiyle ayni kolon gibi sunulmamali.
- Vade/tahakkuk: Cek vade uyarisi var; gelir/gider vadesi ve acik/kismi borclar icin yaslandirma yok.
- Risk limiti: `risk_limiti=0` olan firmalar bilincli olarak risk disi kaliyor. Ancak kac firmanin limitsiz oldugu koddan gorunmuyor; canli veri sorgusu ile ayrica raporlanmali.
- Gelir/giderin cariye etkisi: Kod, odenmemis/kismi gelir-gideri cari bakiyeye dahil ediyor. Bu mali olarak kabul edilebilir, fakat ayri dokum ve etiket sart; aksi halde stok alis/satisla karisir.

## Onerilen Duzeltme Paketi

1. Merkezi donem modeli ekle: `ALL_TIME`, `YEAR`, `MONTH`; UI ve API ayni modeli kullansin.
2. `donem_secici` davranisini duzelt: ay tumu secilince yil korunmali, tum zamanlar ayri secenek olmali.
3. `cari_service`, `kasa_service`, `gelir_gider_service`, `dashboard` icin ortak tarih filtresi yardimcisi yaz.
4. Cari bakiye ve ekstrede devir hesaplarini yil/ay modlari icin acik tanimla; ekstre kümülatif bakiyeyi devirden baslat.
5. Tarih validasyonunu kayit girisinde zorunlu yap; eski bos/bozuk tarihleri veri temizlik raporuna al.
6. Tek bir `calculate_cari_balance()`/SQL view mantigi ile cari liste, risk, tahsilat onerisi ve mutabakat ayni bakiye kaynagini kullansin.
7. Yaslandirma raporunu vade/acik kalem mantigina tasi; parse edilemeyen tarihleri rapora dahil etme, hata listesi yap.
8. PDF/Excel raporlarina donem etiketi ve sorgu parametresi ekle.
9. v3 yeni tasarimda ekstre/cari/kasa/gelir-gider ekranlarini backend period API'lerine bagla; statik tarihleri kaldir.
10. DB seviyesinde tarih CHECK, case-insensitive firma kodu kontrolu ve orphan kayit kontrolleri ekle.
11. Para hesaplarinda `Decimal` kullan; float'a sadece gorsellestirme sirasinda don.

## Test Senaryolari

- Senaryo 1: Cari listede `2026 / Tumu` secildiginde sadece 2026 hareketleri gelmeli; devir `2026-01-01` oncesi bakiye olmali.
- Senaryo 2: Cari listede `2026 / Nisan` secildiginde devir `2026-04-01` oncesi, donem hareketi sadece Nisan olmali.
- Senaryo 3: `tarih=''` veya `NULL` hareket eklenirse donem raporuna girmemeli; veri kalite uyarisinda gorunmeli.
- Senaryo 4: Cari ekstre Nisan 2026 acildiginda ilk bakiye devirle baslamali; son bakiye cari liste Nisan bakiyesiyle tutmali.
- Senaryo 5: Gelir/giderde odenmemis cari gider kaydi acildiginda cari bakiyesi etkilenmeli, odeme yapilinca kasa hareketiyle kalan dogru azaltilmali.
- Senaryo 6: Risk limiti olan firma icin cari liste bakiyesi ve risk uyarisi ayni bakiyeyi gostermeli.
- Senaryo 7: Tevkifatli satis kaydinda cari bakiye `kdvli_toplam`, KDV raporu `toplam/kdv_tutar/tevkifat_tutar` uzerinden tutarli hesaplanmali.
- Senaryo 8: Vadesi gecmis cek ve odenmemis gelir/gider faturasi dashboard uyarilarinda ayrica gorunmeli.
- Senaryo 9: v3 ekstrede tahsilat/odeme tutarlari sifir degil, backend ekstreyle birebir ayni gorunmeli.
- Senaryo 10: v3 yeni tahsilat/odeme kaydi bugunun tarihiyle acilmali; sabit 2026-04-24 tarihi kalmamali.

## Acik Sorular

- `gg_gelir/gg_gider` cari bakiyesine dahil olmaya devam edecek mi, yoksa ayri cari etkisi kolonlari mi istenecek?
- Bos/bozuk tarihli kayitlar icin politika ne olacak: duzeltme zorunlu mu, rapor disi mi, yoksa "tarih belirsiz" donemi mi?
- `risk_limiti=0` "limitsiz" mi demek, yoksa "limit tanimsiz; uyarilarda ayrica goster" mi?
- Ekstrede devir satiri tekrar gorunsun mu, yoksa gorunmeden kümülatif bakiye devirden mi baslasin?
- PDF/Excel raporlarinda varsayilan donem etiketi "Tüm Zamanlar", "2026 Yılı" ve "Nisan 2026" olarak ayrilsin mi?
