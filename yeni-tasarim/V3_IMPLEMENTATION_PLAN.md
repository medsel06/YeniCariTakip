# v3 (Trend) Tasarımı — Uygulama Planı

**Hazırlık tarihi:** 2026-04-26
**Hazırlayan oturum:** Claude (Opus 4.7)
**Hedef:** v3 tasarımını mevcut Cari Takip sistemine entegre et, gerçek PostgreSQL verisiyle çalıştır
**Geri dönüş tag'i:** `v2-stable-2026-04-25` (commit `8312096`)

---

## 1. Bağlam

### Mevcut sistem
- **Backend:** Python NiceGUI (port 8080), `main.py` + `pages/*.py` + `services/*.py`
- **DB:** PostgreSQL multi-tenant (her firma `t_X` schema'sında)
- **Auth:** Session cookie, login zorunlu
- **DB connection:** `db.py` → psycopg2 pool, `set_tenant_schema()` ile context
- **Mevcut pages/:** dashboard, cari, cari_detay, hareketler, stok, stok_detay, kasa, cekler, uretim, gelir_gider, raporlar, mutabakat, cek_takvim, tahsilat_oneri, karlilik, personel, firma_master, ayarlar, loglar, haftalik_bilanco, login

### v3 (Trend) tasarımı
- **Kaynak:** `C:\Users\ykahm\Downloads\cari (2).zip` → `Cari Takip v3 (Trend).html`
- **Tip:** Self-contained tek HTML (React 18 + Babel + JSX, CDN bağımlılıklar)
- **Tema:** Dark/Light, lime accent (`#a3e635`), Inter + JetBrains Mono fontları
- **Sayfalar:** Dashboard, CariList, CustomerDetail, Ekstre, StokPage, GelirGider, Report
- **Modallar:** TxModal, NewCariModal, NewStokModal, StokHrkModal, NewGGModal
- **Şu an:** Tamamen mock data (CUSTOMERS array, genTx() fonksiyonları)

### Ek dosyalar
- `PDF Dökümleri.html` — A4 baskı tasarımı, standalone, kendi navigasyonu (cari/stok/gg seçici)
- `src/*.jsx` — v2'nin kaynak modülleri (referans, kullanılmıyor)

---

## 2. Kullanıcı kararları (verilen cevaplar)

| Soru | Cevap |
|---|---|
| Bilgi Ekranı'nda "Aylık Hareket Özeti" silindiğinde ne olsun? | **Sol: Hızlı Özet · Sağ: En Yüksek Bakiyeler** |
| Cari Detay'da "Bakiye Gelişimi" silindiğinde ne olsun? | **Tam genişlik tek kart** (Dönem Özeti, 4 sütun) |
| Gelir/Gider'de "Akış" grafiği silindiğinde ne olsun? | **Gider Kategorileri tam genişlik** |
| PDF Dökümleri nasıl bağlansın? | **Standalone dosya**, sidebar'dan link |
| Mock data ne yapacak? | **Gerçek DB'den oku** (PostgreSQL) |
| Strateji? | **v3'ü backend'e bağla (büyük iş)** — fazlı yaklaşım |
| v3'ten ne alıyoruz? | **Sadece arayüz tasarımı + bazı kartlar** (veri sistemden) |

---

## 3. Faz Planı

### Faz 1 — Tasarım iskeleti (gelecek oturumun hedefi, ~2 saat)

**Çıktı:** Tarayıcıda açılan, tüm sayfaların v3 stilinde göründüğü, mock'sız (boş) prototip. API'a hazır yapı.

#### 1.1. Dosya kopyalama
- [ ] `Cari Takip v3 (Trend).html` → `yeni-tasarim/Cari Takip v3 (Trend).html`
- [ ] `PDF Dökümleri.html` → `yeni-tasarim/PDF Dökümleri.html`
- Kaynak: `C:\Users\ykahm\AppData\Local\Temp\cari_v4\` (henüz duruyorsa) veya `C:\Users\ykahm\Downloads\cari (2).zip` zip'inden tekrar çıkar

#### 1.2. Mock data temizliği (v3 içinde)
v3'ün üst bölümündeki sabit mock array'leri **boş array** ile değiştir:
- `const CUSTOMERS = [...]` (10 kayıt) → `let CUSTOMERS = []`
- `function genTx() {...}` ve `const TX = genTx()` → `let TX = []`
- `const STOK = (() => {...})()` (20 kayıt) → `let STOK = []`
- `const STOK_HRK = (() => {...})()` → `let STOK_HRK = []`
- `const GG = (() => {...})()` → `let GG = []`

Her birinin yanına yorum ekle:
```js
// TODO Faz 2/3: const res = await fetch('/api/cariler'); CUSTOMERS = await res.json();
```

#### 1.3. Boş state placeholder'ları
Her tabloda zaten mevcut `length===0` durumlarını koru, mesajları güncelle:
- "Bu filtre için cari bulunamadı." → "Henüz cari yok. Yeni Cari ile başla."
- "Bu filtre için hareket bulunamadı." → "Bu cari için hareket yok."
- vb.

#### 1.4. Grafik kaldırma — 3 sayfa

**A) Dashboard (`function Dashboard`, satır ~570-642)**
- Sil: 12-ay bar chart kartı (`<div className="card">` blokunun ilki)
- Sil: `tahs`, `fat`, `months`, `mx`, `cumulative` array'leri ve hesapları
- Yeni: Sol tarafa **Hızlı Özet** kartı:
  ```
  Aktif Cari: {active}/{CUSTOMERS.length}
  Toplam Açık Alacak: {fmt(totalA)}
  Toplam Borç: {fmt(totalB)}
  Limit Üstü: {overLim} cari
  ```
- "En Yüksek Bakiyeler" kartı sağda kalır (mevcut yapı)

**B) CustomerDetail (`function CustomerDetail`, satır ~780-794)**
- Sil: `<div className="two-col">` bloğu (Bakiye Gelişimi + Dönem Özeti)
- Sil: `series` `useMemo` hesabı, `<Spark>` import'u kalabilir (başka sayfalarda kullanılıyor mu kontrol et — ekstre KPI grid'inde değil, sadece detayda; spark fonksiyonunu koru)
- Yeni: Tek kart, 4 sütunlu metric grid:
  ```
  | Toplam Fatura | Toplam Tahsilat | Ort. Tahsilat Süresi | Risk Skoru |
  ```

**C) GelirGider (`function GelirGider`, satır ~1004-1018)**
- Sil: "Gelir / Gider Akışı" kartı (sol)
- Sil: 15-günlük bar chart hesaplama IIFE'si (`{(()=>{...})()}`)
- Yeni: "Gider Kategorileri" kartını **tam genişliğe** çek (`<div className="two-col">` → `<div>` veya `<div className="card">`)

#### 1.5. Yeni sayfa — Stok Hareketler (`function Hareketler`)

**Konum:** v3 içinde, GelirGider'den sonra ekle

**Yapı:**
```jsx
function Hareketler({onNew}) {
  // States: arama, dönem (yıl/ay), tür filtresi (all/alis/satis), edit modal
  // Boş veri: const HAREKETLER = []; (Faz 2'de fetch)

  return <div>
    {/* KPI strip - 4 kart */}
    {/* Toplam Alış | Toplam Satış | Net Sonuç | Toplam Hareket */}

    {/* Filter bar */}
    {/* Arama + Dönem (yıl/ay) + Tür chips + Yeni Hareket btn */}

    {/* Tablo */}
    {/* Tarih, Belge No, Firma, Tür chip, Ürün, Miktar, B.Fiyat, Matrah, KDV, Tevkifat, Toplam */}

    {/* Edit/Delete actions per row */}
  </div>;
}

function HareketModal({editRow, onClose, onSaved}) {
  // Tek-form modal (wizard değil)
  // Field'lar: Tarih, Belge No, Tür (radio: ALIŞ/SATIŞ), KDV (1/10/20), Tevkifat (yok/2-9 / 10),
  //           Firma (select + mini-add), Ürün (select + mini-add), Miktar, Birim Fiyat, Açıklama
  // Live calc panel: Matrah / KDV / Tevkifat / Toplam
  // Risk uyarısı: SATIŞ + bakiye>kredi*0.8 → kırmızı banner
}
```

**v3 stil sınıfları:** `kpi-grid`, `kpi`, `card`, `card-hd`, `fbar`, `flt`, `seg`, `tbl`, `chip`, `c-info`, `c-good`, `modal`, `field`, `field-row`, `tp` (radio tile)

#### 1.6. Yeni sayfa — Haftalık Bilanço (`function HaftalikBilanco`)

**Konum:** v3 içinde, Hareketler'den sonra ekle

**Yapı:**
```jsx
function HaftalikBilanco() {
  const [yil, setYil] = useState(2026);
  const [ay, setAy] = useState(4);
  const [hafta, setHafta] = useState('');  // ISO week format
  const [papelFiyat, setPapelFiyat] = useState(25);
  const [tutkalFiyat, setTutkalFiyat] = useState(10);
  const [rows, setRows] = useState([]);  // {kod, ad, desi, adet, satisFiyat, tutkal} — boş başla

  // Live calc: her input değişiminde row.kar/kazanc/hammadde/ciro yeniden hesapla
  // Toplamlar: useMemo ile derive

  return <div>
    {/* Header card: Yıl/Ay/Hafta select + Papel/Tutkal price card (warn-soft sarı) */}

    {/* Edit table: 11 sütun */}
    {/* Ürün, DESİ, [Adet input], Papel Ham, [Tutkal input], Ham Maliyet,
        [Satış Fiyat input], Kar, Kazanç, Hammadde, Ciro */}

    {/* Footer card: Toplam Hammadde (desi & m³), Toplam Ciro, Toplam Kazanç */}

    {/* Buttons: Kaydet | PDF | Excel */}
  </div>;
}
```

**v3 stil sınıfları:** `card`, `field`, `field-row`, input border classes, `kpi-grid` for footer

**Hesaplama formülleri (haftalik_bilanco.py'den):**
- `papel_ham = desi * papelFiyat`
- `ham_maliyet = papel_ham + tutkal`
- `kar = satisFiyat - ham_maliyet` (eğer satisFiyat > 0)
- `kazanc = kar * adet`
- `hammadde = desi * adet`
- `ciro = satisFiyat * adet`
- Toplam hammadde m³ = hammadde / 1000

#### 1.7. PDF Dökümleri entegrasyonu
- Dosya kopyala (1.1'de yapıldı)
- v3 sidebar'da "Finans Analiz" grubuna **"PDF Dökümleri"** linki ekle
- Tıklayınca: `window.open('PDF Dökümleri.html', '_blank')` (yeni sekmede açar)
- Icon: `IPdf` (zaten v3'te var)

#### 1.8. Sidebar güncelleme

`function Sidebar`, satır ~531-545:
```js
const op = [
  {id:'dashboard', l:'Bilgi Ekranı', i:<IDash/>},
  {id:'cariler', l:'Cari Hesaplar', i:<ICari/>, b:String(CUSTOMERS.length)},
  {id:'hareketler', l:'Stok Hareketler', i:<ISwap/>},  // YENİ — Stok'tan önce
  {id:'firmalar', l:'Firmalar', i:<IApt/>},
  {id:'stok', l:'Stok', i:<IStok/>},
  {id:'kasa', l:'Kasa', i:<IKasa/>},
  {id:'gelirgider', l:'Gelir / Gider', i:<IGel/>},
  {id:'personel', l:'Personel', i:<IBdg/>},
  {id:'cekler', l:'Çek / Senet', i:<ICek/>},
  {id:'uretim', l:'Üretim', i:<IFct/>},
  {id:'bilanco', l:'Haftalık Bilanço', i:<ITrend/>},  // YENİ — Üretim'den sonra
];
const fn = [
  {id:'cektakvim', l:'Çek Takvimi', i:<ICal/>},
  {id:'mutabakat', l:'Mutabakat', i:<ICk/>},
  {id:'tahsilatoneri', l:'Tahsilat Önerisi', i:<IIns/>},
  {id:'rapor', l:'Raporlar', i:<IRep/>},
  {id:'pdfdokum', l:'PDF Dökümleri', i:<IPdf/>, ext:true},  // YENİ — yeni sekmede
];
```

`ISwap` icon yeni yazılacak (path swap_horiz benzeri). `ITrend` mevcut.

#### 1.9. App routing güncelleme

`function App`, satır ~1315-1331:
```js
const meta = {
  dashboard: ['Bilgi Ekranı'],
  cariler: ['Cariler'],
  cari: ['Cariler', 'Cari Kart Detayı'],
  ekstre: ['Cariler', 'Hesap Ekstresi'],
  hareketler: ['Stok Hareketler'],  // YENİ
  stok: ['Stok'],
  gelirgider: ['Gelir / Gider'],
  bilanco: ['Üretim', 'Haftalık Bilanço'],  // YENİ
  rapor: ['Finans Analiz', 'Raporlar'],
};

// render():
if (page === 'hareketler') return <Hareketler onNew={() => setModal({kind:'hareket'})}/>;
if (page === 'bilanco') return <HaftalikBilanco/>;
```

PDF link sidebar'da `ext:true` flag'i ile özel handling — `nav` fonksiyonu kontrol edip yeni sekmede açar:
```js
const nav = (p) => {
  if (p === 'pdfdokum') { window.open('PDF Dökümleri.html', '_blank'); return; }
  setPage(p); setFocus(null);
};
```

#### 1.10. Test
- [ ] Tarayıcıda `Cari Takip v3 (Trend).html` aç
- [ ] Light + Dark tema toggle
- [ ] Tüm sidebar item'larına tıkla → her sayfa render olmalı (boş veriyle bile crash olmamalı)
- [ ] Modal aç/kapa testi
- [ ] PDF Dökümleri linki yeni sekmede açıyor mu
- [ ] Console'da hata yok mu

#### 1.11. Commit
```bash
git add yeni-tasarim/
git commit -m "v3 (Trend) tasarımı + Stok Hareketler + Haftalık Bilanço + PDF Dökümleri ekle (boş veri, API'a hazır)"
git push origin yeni-tasarim
```

---

### Faz 2 — Backend API endpoint'leri (~1-2 oturum)

**Çıktı:** NiceGUI app içinde `/api/*` JSON endpoint'leri. Postman ile test edilebilir.

#### Endpoint listesi
**GET (okuma):**
- `GET /api/me` — login session check, kullanıcı + tenant bilgisi
- `GET /api/dashboard/kpi` — toplam alacak/borç, aktif cari, bu ay tahsilat
- `GET /api/dashboard/top-customers?limit=6` — en yüksek bakiye carileri
- `GET /api/cariler?status=&city=&q=` — filtreli liste
- `GET /api/cariler/:id` — tek cari detayı
- `GET /api/cariler/:id/hareketler?yil=&ay=&tip=` — ekstre
- `GET /api/cariler/:id/ozet` — fatura/tahsilat toplamları, ort. tahsilat süresi
- `GET /api/stok?kategori=&q=` — stok listesi
- `GET /api/stok-hareketler?yil=&ay=&tip=&q=` — alış/satış hareketleri
- `GET /api/gelir-gider?yil=&ay=&tip=` — gelir/gider hareketleri
- `GET /api/bilanco/:yil/:hafta` — haftalık bilanço
- `GET /api/bilanco/desi-urunler` — DESİ değerli ürünler listesi
- `GET /api/raporlar/yaslandirma?yil=&ay=` — 0-30/30-60/60-90/90+ dağılımı
- `GET /api/raporlar/sehir-dagilim` — şehir bazlı açık alacak
- `GET /api/raporlar/belge-tipi-dagilim?yil=&ay=` — fatura/tahsilat/çek dağılımı

**POST (yazma):**
- `POST /api/cariler` — yeni cari
- `POST /api/stok` — yeni stok kartı
- `POST /api/stok-hareketler` — alış/satış (mini firma/ürün ekleme dahil)
- `POST /api/cariler/:id/tahsilat` — tahsilat
- `POST /api/cariler/:id/odeme` — ödeme
- `POST /api/gelir-gider` — yeni gelir/gider kaydı
- `POST /api/bilanco/:yil/:hafta` — haftalık bilanço kaydet
- `POST /api/cariler/:id/risk-check` — risk limit kontrolü

#### Implementasyon notları
- NiceGUI altta FastAPI kullanır → `from fastapi import APIRouter` veya `app.add_api_route`
- Auth: NiceGUI session'ı kullan → `app.storage.user.get('user_id')`
- Tenant: `set_tenant_schema()` middleware ile request başına ayarla
- Mevcut `services/cari_service.py`, `services/stok_service.py`, vb. zaten iş mantığını içeriyor → endpoint'ler ince wrapper olur (~10-20 satır her biri)
- Decimal/datetime serialize: `RealDictCursor` zaten dict döndürüyor, datetime için custom encoder
- Hata yönetimi: 400/404/500 + Türkçe mesaj

#### Test
- Postman/curl ile her endpoint'i test et (login cookie ile)
- Her endpoint için bir örnek response JSON dosyası kaydet (`docs/api-examples/`)

---

### Faz 3 — Bağlama + auth (~1 oturum)

**Çıktı:** v3 HTML gerçek veriyle çalışır. `/yeni-ui/` URL'inde çalışır.

#### Adımlar
1. **Mount:** `main.py` içinde `app.add_static_files('/yeni-ui', os.path.join(BASE_DIR, 'yeni-tasarim'))`
2. **Login redirect:** v3 boot'unda `fetch('/api/me')` → 401 ise `window.location='/login'`
3. **CSRF/auth:** NiceGUI session cookie zaten gönderilir, ek iş yok
4. **Tüm `loadData()` fonksiyonlarını gerçek `fetch()` ile doldur:**
   ```js
   async function loadCariler() {
     const r = await fetch('/api/cariler');
     if (r.status === 401) { window.location = '/login'; return; }
     const data = await r.json();
     setCustomers(data);
   }
   ```
5. **Loading/error state'ler:** Her `useState` data'nın yanına `loading` ve `error` ekle, UI'da göster
6. **Modal'lar yazma:** TxModal, NewCariModal, vb. submit → POST endpoint
7. **Toast mesajları:** `Başarılı: Tahsilat kaydedildi` gerçek backend onayından gelsin

#### Test
- `localhost:8080/yeni-ui/Cari Takip v3 (Trend).html` aç
- Login → 8 cari görmeli (gerçek)
- Yeni cari ekle → DB'ye kaydetmeli
- Refresh sonrası cari listede görünmeli

---

### Faz 4 — Ölçeklendirme + üretim (~1-2 oturum)

#### Performans
- Pagination: cari/hareket listelerinde `?page=&size=`
- Server-side filtering (URL params backend'e geçsin)
- Index check (PostgreSQL EXPLAIN)

#### PDF Dökümleri gerçek veri
- `PDF Dökümleri.html` içine query param ekle: `?type=cari&id=C-1042&yil=2026`
- Backend: `GET /api/pdf/cari-ekstre/:id?yil=&ay=` HTML render et
- veya: tarayıcıda `fetch` ile JSON al, HTML'i client-side doldur

#### Eski sayfaları kapatma
- Önce yeni-ui'yi default'a çek (`/` → redirect `/yeni-ui/`)
- Eski NiceGUI pages'i bir süre paralel tut (rollback için)
- Sonra kademeli kaldır

---

## 4. Mimari kararlar

| Karar | Gerekçe |
|---|---|
| v3 self-contained tek HTML kalır | React + Babel CDN; yeni dosyalara bölmek karmaşa yaratır |
| API ön eki `/api/` | Mevcut NiceGUI route'ları `/cari`, `/stok` vb. ile çakışmaz |
| Mock yok, boş başla | "Veri yok" UX'i Faz 1'den itibaren doğru görünür; Faz 2 plug & play |
| Wizard yok, tek-form modal | Kullanıcı talebi |
| 3 grafik kaldırıldı | Kullanıcı talebi: gereksiz karmaşıklık |
| PDF standalone, link ile | Farklı tasarım dili (A4 print), iframe gömme görsel uyum bozar |
| Faz ayrımı | Her faz commit'lenebilir, test edilebilir, geri alınabilir |

---

## 5. Risk ve geri dönüş

### Tag
`v2-stable-2026-04-25` → `8312096` (origin'e push edildi)

### Rollback komutları
```bash
# Yeni-tasarim klasörünü tag'deki haline geri al:
git checkout v2-stable-2026-04-25 -- yeni-tasarim/

# Tüm dosyaları geri al:
git checkout v2-stable-2026-04-25 -- .

# Tag'den yeni branch oluştur:
git checkout -b rollback-v3 v2-stable-2026-04-25
```

### Bilinen riskler
- **PostgreSQL multi-tenant**: API endpoint'lerinde `set_tenant_schema()` çağrısı unutulursa cross-tenant veri sızıntısı. Middleware şart.
- **CDN bağımlılık**: v3 React/Babel CDN'den çekiyor. Üretimde local'e indir veya bundle.
- **Babel runtime parse**: Sayfa açılışta JSX compile süresi (~200-500ms). Üretimde pre-compile düşün.
- **Auth hijack**: API endpoint'leri session check unutursa açık. Decorator pattern şart.

---

## 6. Dosya değişiklik haritası

### Yeni
- `yeni-tasarim/Cari Takip v3 (Trend).html` (modifiye edilmiş kopya)
- `yeni-tasarim/PDF Dökümleri.html` (orijinal kopya)
- `yeni-tasarim/V3_IMPLEMENTATION_PLAN.md` (bu dosya)

### Faz 2'de değişecek
- `main.py` — API router import + mount
- (yeni) `api/` klasörü veya `routes_api.py` — endpoint'ler
- `services/*.py` — gerekirse yeni method'lar
- `db.py` — gerekirse query helper'lar

### Faz 3'te değişecek
- `main.py` — `app.add_static_files('/yeni-ui', ...)`
- `yeni-tasarim/Cari Takip v3 (Trend).html` — fetch() çağrıları

### Hiç değişmeyecek
- `pages/*.py` (eski NiceGUI sayfaları, paralel çalışmaya devam)
- `db.py` core (PostgreSQL pool)
- `auth_service.py`

---

## 7. Yeni oturum için hızlı başlangıç

```
1. Bu dosyayı oku: yeni-tasarim/V3_IMPLEMENTATION_PLAN.md
2. Task listesini kontrol et: TaskList
3. Tag'in hala var olduğunu doğrula: git tag -l
4. Kaynak zip'i bul: C:\Users\ykahm\Downloads\cari (2).zip
5. Faz 1 task'larını sırayla işle (1.1'den 1.11'e)
6. Her task tamamlanınca TaskUpdate ile completed işaretle
7. Faz 1 bitince commit + push
```

---

**SON.**
