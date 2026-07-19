"""Kolay Muhasebe — public tanıtım (landing) sayfası (mokap görselli)."""
from nicegui import ui

_HTML = r'''
<style>
  .km-root{font-family:'Plus Jakarta Sans',system-ui,Segoe UI,sans-serif;color:#1e1b4b;}
  .km-root *{box-sizing:border-box;}
  .km-wrap{max-width:1140px;margin:0 auto;padding:0 24px;}
  a.km-cta{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:700;border-radius:12px;transition:transform .15s, box-shadow .15s;}
  a.km-cta:hover{transform:translateY(-2px);}
  .km-cta-w{background:#fff;color:#6d28d9;height:48px;padding:0 26px;box-shadow:0 10px 30px rgba(0,0,0,.16);}
  .km-cta-v{background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff;height:48px;padding:0 26px;box-shadow:0 10px 26px rgba(124,58,237,.35);}
  .km-cta-sm{height:40px;padding:0 18px;}

  /* HERO */
  .km-hero{background:radial-gradient(1200px 500px at 80% -10%,#7c3aed 0%,#5b21b6 40%,#4c1d95 100%);color:#fff;padding-bottom:70px;}
  .km-topbar{display:flex;align-items:center;justify-content:space-between;padding:18px 0;}
  .km-brand{display:flex;align-items:center;gap:10px;font-size:21px;font-weight:800;}
  .km-brand .ico{width:38px;height:38px;border-radius:11px;background:rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;}
  .km-brand .ico svg{width:22px;height:22px;fill:#fff;}
  .km-brand .m{color:#c4b5fd;}
  .km-hero-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:40px;align-items:center;padding-top:26px;}
  .km-h1{font-size:44px;font-weight:800;line-height:1.12;letter-spacing:-1.2px;margin:0 0 16px;}
  .km-sub{font-size:17px;color:#ede9fe;line-height:1.6;margin:0 0 26px;max-width:520px;}
  .km-pill{display:inline-block;background:rgba(255,255,255,.14);color:#ddd6fe;font-size:12px;font-weight:600;padding:5px 12px;border-radius:999px;margin-bottom:18px;letter-spacing:.3px;}
  .km-hero-note{margin-top:16px;font-size:12.5px;color:#c4b5fd;}

  /* Browser window mockup */
  .km-win{background:#fff;border-radius:14px;box-shadow:0 30px 70px rgba(23,9,54,.45);overflow:hidden;border:1px solid rgba(255,255,255,.4);}
  .km-bar{height:34px;background:#f1f5f9;display:flex;align-items:center;gap:6px;padding:0 12px;border-bottom:1px solid #e5e7eb;}
  .km-dot{width:10px;height:10px;border-radius:50%;}
  .km-url{margin-left:10px;height:18px;flex:1;max-width:230px;background:#fff;border-radius:6px;border:1px solid #e5e7eb;}
  .km-winbody{background:#f7f7fb;}

  /* Dashboard mockup */
  .km-dash{display:flex;height:300px;}
  .km-side{width:120px;background:#faf7ff;border-right:1px solid #ece9f6;padding:12px 10px;}
  .km-slogo{display:flex;align-items:center;gap:6px;font-size:11px;font-weight:800;color:#6d28d9;margin-bottom:12px;}
  .km-slogo i{width:16px;height:16px;border-radius:5px;background:linear-gradient(135deg,#7c3aed,#6366f1);display:inline-block;}
  .km-nav{height:9px;border-radius:5px;background:#e9e5f5;margin:8px 2px;}
  .km-nav.act{background:linear-gradient(90deg,#7c3aed,#a78bfa);width:88%;}
  .km-main{flex:1;padding:14px;}
  .km-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;}
  .km-stat{border-radius:10px;padding:9px 10px;color:#fff;}
  .km-stat b{display:block;font-size:8px;opacity:.9;font-weight:600;letter-spacing:.3px;}
  .km-stat span{font-size:13px;font-weight:800;}
  .km-s1{background:linear-gradient(135deg,#ef4444,#dc2626);} .km-s2{background:linear-gradient(135deg,#3b82f6,#2563eb);} .km-s3{background:linear-gradient(135deg,#10b981,#059669);}
  .km-row2{display:grid;grid-template-columns:1.3fr 1fr;gap:10px;}
  .km-chart{background:#fff;border:1px solid #eee;border-radius:10px;padding:10px;}
  .km-bars{display:flex;align-items:flex-end;gap:6px;height:96px;}
  .km-bars i{flex:1;background:linear-gradient(180deg,#a78bfa,#7c3aed);border-radius:4px 4px 0 0;display:block;}
  .km-list{background:#fff;border:1px solid #eee;border-radius:10px;padding:10px;}
  .km-li{display:flex;justify-content:space-between;align-items:center;font-size:9px;padding:4px 0;border-bottom:1px dashed #eee;}
  .km-li b{color:#0f172a;} .km-li .r{color:#059669;font-weight:700;}
  .km-badge{font-size:7.5px;background:#fee2e2;color:#b91c1c;padding:1px 5px;border-radius:5px;font-weight:700;}

  /* Sections */
  .km-sec{padding:64px 0;}
  .km-sec-h{text-align:center;font-size:27px;font-weight:800;margin:0 0 6px;}
  .km-sec-s{text-align:center;color:#6b7280;font-size:15px;margin:0 0 34px;}
  .km-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
  .km-feat{background:#fff;border:1px solid #ece9f6;border-radius:16px;padding:22px;box-shadow:0 6px 18px rgba(124,58,237,.05);transition:transform .2s, box-shadow .2s;}
  .km-feat:hover{transform:translateY(-5px);box-shadow:0 16px 34px rgba(124,58,237,.12);}
  .km-feat h3{margin:0 0 5px;font-size:16px;font-weight:700;display:flex;align-items:center;gap:7px;}
  .km-feat h3 .material-icons{font-size:20px;color:#7c3aed;}
  .km-feat p{margin:0;font-size:13.5px;color:#6b7280;line-height:1.55;}
  .km-fprev{background:#faf8ff;border:1px solid #f0ecfa;border-radius:10px;padding:11px;height:96px;margin-bottom:13px;overflow:hidden;display:flex;flex-direction:column;justify-content:center;}
  .km-mrow{display:flex;justify-content:space-between;align-items:center;font-size:10px;padding:3px 0;border-bottom:1px dashed #ece9f6;color:#475569;}
  .km-mrow:last-child{border:none;}
  .km-chip{display:inline-block;font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:6px;}
  .km-mbars{display:flex;align-items:flex-end;gap:5px;height:62px;width:100%;}
  .km-mbars i{flex:1;background:linear-gradient(180deg,#a78bfa,#7c3aed);border-radius:3px 3px 0 0;}
  .km-big{font-size:22px;font-weight:800;color:#1e1b4b;}
  .km-prog{flex:0 0 84px;height:7px;background:#ece9f6;border-radius:4px;position:relative;overflow:hidden;}
  .km-prog i{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#7c3aed,#a78bfa);border-radius:4px;}
  .km-mini2{flex:1;border-radius:8px;padding:8px;color:#fff;}
  .km-mini2 b{font-size:15px;}

  /* Showcase alternating */
  .km-show{display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:center;padding:40px 0;}
  .km-show.rev .km-show-txt{order:2;}
  .km-show h3{font-size:23px;font-weight:800;margin:0 0 10px;}
  .km-show p{font-size:15px;color:#475569;line-height:1.65;margin:0 0 14px;}
  .km-check{list-style:none;padding:0;margin:0;}
  .km-check li{display:flex;gap:8px;align-items:flex-start;font-size:14px;color:#334155;margin:7px 0;}
  .km-check li:before{content:"✓";color:#7c3aed;font-weight:800;}

  /* mini mockup panels */
  .km-panel{background:#fff;border:1px solid #ece9f6;border-radius:14px;box-shadow:0 18px 44px rgba(76,29,149,.12);padding:14px;}
  .km-ext-row{display:grid;grid-template-columns:52px 1fr 78px;gap:8px;font-size:11px;padding:7px 4px;border-bottom:1px solid #f1f0f7;align-items:center;}
  .km-ext-row .a{color:#94a3b8;} .km-ext-row .b{color:#0f172a;font-weight:600;} .km-ext-row .amt{text-align:right;font-weight:800;}
  .km-neg{color:#dc2626;} .km-pos{color:#059669;}
  .km-wa{margin-top:12px;background:#dcf8c6;border-radius:12px 12px 12px 4px;padding:10px 12px;font-size:12px;color:#14532d;max-width:88%;box-shadow:0 4px 10px rgba(0,0,0,.06);}
  .km-wa small{display:block;color:#3f6212;margin-top:4px;font-size:10px;}

  .km-cek{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;}
  .km-cekcard{border-radius:12px;padding:12px;color:#fff;}
  .km-cekcard b{font-size:10px;opacity:.92;display:block;} .km-cekcard span{font-size:18px;font-weight:800;}
  .km-cin{background:linear-gradient(135deg,#10b981,#059669);} .km-cout{background:linear-gradient(135deg,#ef4444,#dc2626);}
  .km-cekli{display:flex;justify-content:space-between;align-items:center;font-size:11.5px;padding:6px 2px;border-bottom:1px dashed #eee;}

  /* CTA strip + footer */
  .km-ctas{background:linear-gradient(135deg,#6d28d9,#7c3aed);color:#fff;text-align:center;padding:56px 24px;}
  .km-ctas h2{font-size:26px;font-weight:800;margin:0 0 6px;}
  .km-ctas p{color:#ede9fe;margin:0 0 22px;font-size:15px;}
  .km-foot{background:#1e1b4b;color:#c4b5fd;text-align:center;padding:26px;font-size:12.5px;}

  @media (max-width:900px){
    .km-hero-grid{grid-template-columns:1fr;} .km-h1{font-size:34px;}
    .km-grid{grid-template-columns:1fr 1fr;}
    .km-show{grid-template-columns:1fr;gap:24px;} .km-show.rev .km-show-txt{order:0;}
  }
  @media (max-width:600px){ .km-grid{grid-template-columns:1fr;} .km-stats{grid-template-columns:repeat(3,1fr);} }
</style>

<div class="km-root">
  <!-- HERO -->
  <section class="km-hero">
    <div class="km-wrap">
      <div class="km-topbar">
        <div class="km-brand">
          <span class="ico"><svg viewBox="0 0 24 24"><path d="M11.71 17.99C8.53 17.84 6 15.22 6 12c0-3.31 2.69-6 6-6 3.22 0 5.84 2.53 5.99 5.71l-2.1-.63C15.5 9.28 13.92 8 12 8c-2.21 0-4 1.79-4 4 0 1.92 1.28 3.5 3.01 3.89l.7 2.1zM22 12c0-5.52-4.48-10-10-10S2 6.48 2 12s4.48 10 10 10h.5v-2H12c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8v.5h2V12zm-6.88 1.9l5.51 1.65-2.35 1.18 2.68 5.36-1.79.89-2.68-5.36-2.35 1.18z"/></svg></span>
          <span>Kolay&nbsp;<span class="m">Muhasebe</span></span>
        </div>
        <a class="km-cta km-cta-w km-cta-sm" href="/login">Giriş Yap</a>
      </div>

      <div class="km-hero-grid">
        <div>
          <span class="km-pill">Cari · Stok · Kasa · Çek · Gelir-Gider · Raporlar</span>
          <h1 class="km-h1">İşletmenizin tüm hesabı<br>tek panelde</h1>
          <p class="km-sub">Alış-satıştan tahsilata, çek takibinden gelir-gidere ve kârlılık raporlarına kadar — günlük muhasebenizi tek ekrandan, kolayca yönetin.</p>
          <a class="km-cta km-cta-w" href="/login">Hemen Giriş Yap →</a>
          <div class="km-hero-note">Tek tıkla WhatsApp'tan hesap özeti · Vadesi yaklaşan çek uyarıları · Ürün kâr marjı</div>
        </div>

        <!-- Dashboard mokap -->
        <div class="km-win">
          <div class="km-bar">
            <span class="km-dot" style="background:#ff5f57"></span><span class="km-dot" style="background:#febc2e"></span><span class="km-dot" style="background:#28c840"></span>
            <span class="km-url"></span>
          </div>
          <div class="km-winbody"><div class="km-dash">
            <div class="km-side">
              <div class="km-slogo"><i></i> Kolay Muhasebe</div>
              <div class="km-nav act"></div><div class="km-nav"></div><div class="km-nav"></div>
              <div class="km-nav"></div><div class="km-nav"></div><div class="km-nav"></div><div class="km-nav"></div>
            </div>
            <div class="km-main">
              <div class="km-stats">
                <div class="km-stat km-s1"><b>NET KÂR</b><span>₺ 1.28M</span></div>
                <div class="km-stat km-s2"><b>KASA</b><span>₺ 342B</span></div>
                <div class="km-stat km-s3"><b>SATIŞ</b><span>₺ 2.4M</span></div>
              </div>
              <div class="km-row2">
                <div class="km-chart"><div class="km-bars">
                  <i style="height:40%"></i><i style="height:62%"></i><i style="height:48%"></i><i style="height:80%"></i><i style="height:58%"></i><i style="height:92%"></i><i style="height:70%"></i>
                </div></div>
                <div class="km-list">
                  <div class="km-li"><b>Aygersan</b><span class="r">59.094 ₺</span></div>
                  <div class="km-li"><b>Fil Plastik</b><span class="badge km-badge">3 gün</span></div>
                  <div class="km-li"><b>Volkan Pls.</b><span class="r">18.500 ₺</span></div>
                  <div class="km-li"><b>Korplas</b><span class="r">24.300 ₺</span></div>
                </div>
              </div>
            </div>
          </div></div>
        </div>
      </div>
    </div>
  </section>

  <!-- FEATURES -->
  <section class="km-sec km-wrap">
    <h2 class="km-sec-h">Her şey tek uygulamada</h2>
    <p class="km-sec-s">Günlük muhasebe işlerinizi hızlandıran modüller</p>
    <div class="km-grid">
      <div class="km-feat">
        <div class="km-fprev">
          <div class="km-mrow"><span>Satış — PP Granül</span><span class="km-pos" style="font-weight:700">+27.520</span></div>
          <div class="km-mrow"><span>Tahsilat — Havale</span><span class="km-neg" style="font-weight:700">-15.000</span></div>
          <div class="km-mrow"><b style="color:#0f172a">Bakiye</b><span class="km-chip" style="background:#dcfce7;color:#15803d">24.000 ₺</span></div>
        </div>
        <h3><span class="material-icons">groups</span> Cari Hesaplar</h3>
        <p>Müşteri/tedarikçi bakiyeleri, canlı ekstre ve tek tıkla WhatsApp'tan hesap özeti (PDF ile).</p>
      </div>
      <div class="km-feat">
        <div class="km-fprev" style="flex-direction:row;align-items:flex-end;gap:9px">
          <div class="km-mbars" style="flex:1"><i style="height:45%"></i><i style="height:70%"></i><i style="height:55%"></i><i style="height:90%"></i><i style="height:66%"></i></div>
          <span class="km-chip" style="background:#f3e8ff;color:#7c3aed;align-self:center">%25 marj</span>
        </div>
        <h3><span class="material-icons">inventory_2</span> Stok & Ürün</h3>
        <p>Ürün bazlı alış/satış, ortalama alış-satış fiyatı ve kâr marjı raporu.</p>
      </div>
      <div class="km-feat">
        <div class="km-fprev" style="align-items:flex-start;justify-content:center">
          <span style="font-size:9px;color:#94a3b8;font-weight:700;letter-spacing:.3px">KASA BAKİYESİ</span>
          <span class="km-big">₺ 342.180</span>
          <div style="margin-top:7px;display:flex;gap:5px">
            <span class="km-chip" style="background:#eef2ff;color:#4338ca">Nakit</span>
            <span class="km-chip" style="background:#ecfeff;color:#0e7490">Havale</span>
            <span class="km-chip" style="background:#f0fdf4;color:#15803d">Banka</span>
          </div>
        </div>
        <h3><span class="material-icons">account_balance</span> Kasa & Banka</h3>
        <p>Nakit ve banka hareketleri, tahsilat/ödeme ve anlık kasa bakiyesi.</p>
      </div>
      <div class="km-feat">
        <div class="km-fprev" style="flex-direction:row;gap:8px">
          <div class="km-mini2" style="background:linear-gradient(135deg,#10b981,#059669)"><span style="font-size:8px;opacity:.92">GİRECEK</span><br><b>₺6.5M</b></div>
          <div class="km-mini2" style="background:linear-gradient(135deg,#ef4444,#dc2626)"><span style="font-size:8px;opacity:.92">ÇIKACAK</span><br><b>₺3.1M</b></div>
        </div>
        <h3><span class="material-icons">description</span> Çek / Senet</h3>
        <p>Portföy görünümü, girecek/çıkacak para, vade takvimi ve yaklaşan vade uyarıları.</p>
      </div>
      <div class="km-feat">
        <div class="km-fprev">
          <div class="km-mrow"><span>🚚 Nakliye</span><span class="km-prog" style="flex:0 0 82px"><i style="width:45%"></i></span></div>
          <div class="km-mrow"><span>👷 Personel</span><span class="km-prog" style="flex:0 0 82px"><i style="width:72%"></i></span></div>
          <div class="km-mrow"><span>⚡ Elektrik</span><span class="km-prog" style="flex:0 0 82px"><i style="width:28%"></i></span></div>
        </div>
        <h3><span class="material-icons">receipt_long</span> Gelir / Gider</h3>
        <p>Kategori bazlı gider takibi ve gün/ay/yıl filtreli, ikonlu PDF raporlar.</p>
      </div>
      <div class="km-feat">
        <div class="km-fprev">
          <div class="km-mbars"><i style="height:35%"></i><i style="height:55%"></i><i style="height:45%"></i><i style="height:72%"></i><i style="height:60%"></i><i style="height:88%"></i><i style="height:76%"></i></div>
        </div>
        <h3><span class="material-icons">query_stats</span> Raporlar & Analiz</h3>
        <p>Karlılık, mutabakat, tahsilat önerisi ve çek takvimi — hepsi tek ekranda.</p>
      </div>
    </div>
  </section>

  <!-- SHOWCASE 1: Cari + WhatsApp -->
  <section style="background:#faf7ff;"><div class="km-wrap"><div class="km-show">
    <div class="km-show-txt">
      <h3>Cari hesap & tek tıkla tahsilat hatırlatma</h3>
      <p>Her müşteri/tedarikçinin güncel bakiyesini ve ekstresini anında görün. Bakiyeyi hazır mesajla WhatsApp'tan gönderin — hesap dökümü PDF'i 15 gün geçerli bir bağlantı olarak eklenir.</p>
      <ul class="km-check">
        <li>Yürüyen bakiyeli cari ekstre</li>
        <li>WhatsApp'tan bakiye + PDF ekstre gönderimi</li>
        <li>Tahsilat/ödeme tek ekrandan</li>
      </ul>
    </div>
    <div class="km-panel">
      <div class="km-ext-row"><span class="a">12.07</span><span class="b">Satış — PP Granül</span><span class="amt km-pos">+27.520</span></div>
      <div class="km-ext-row"><span class="a">14.07</span><span class="b">Tahsilat — Havale</span><span class="amt km-neg">-15.000</span></div>
      <div class="km-ext-row"><span class="a">16.07</span><span class="b">Satış — ABS Çapak</span><span class="amt km-pos">+12.480</span></div>
      <div class="km-ext-row"><span class="a"></span><span class="b" style="font-weight:800">Bakiye</span><span class="amt km-pos">24.000 ₺</span></div>
      <div class="km-wa">Sayın Aygersan, 19.07.2026 itibarıyla borç bakiyeniz <b>24.000 ₺</b>'dir. 📄 Ekstre: kolaymuhasebe.site/…
        <small>WhatsApp · bugün 14:32 ✓✓</small>
      </div>
    </div>
  </div></div></section>

  <!-- SHOWCASE 2: Çek portföy -->
  <div class="km-wrap"><div class="km-show rev">
    <div class="km-show-txt">
      <h3>Çek portföyü & vade takibi</h3>
      <p>Elinizdeki (tahsil edilecek) ve verdiğiniz (ödenecek) çekleri vadeye göre tek ekranda görün. Girecek ve çıkacak parayı, net etkiyi ve geciken çekleri anında yakalayın.</p>
      <ul class="km-check">
        <li>Girecek / çıkacak / net özeti</li>
        <li>"3 gün kaldı" / "geçti" vade uyarıları</li>
        <li>Aylık çek vade takvimi</li>
      </ul>
    </div>
    <div class="km-panel">
      <div class="km-cek">
        <div class="km-cekcard km-cin"><b>GİRECEK (Tahsil)</b><span>₺ 6.5M</span></div>
        <div class="km-cekcard km-cout"><b>ÇIKACAK (Ödeme)</b><span>₺ 3.1M</span></div>
      </div>
      <div class="km-cekli"><span><b>ÇK-10432</b> · Yakup Çal</span><span class="km-badge">2 gün kaldı</span></div>
      <div class="km-cekli"><span><b>ÇK-10510</b> · Fil Plastik</span><span class="km-pos">tahsil edildi</span></div>
      <div class="km-cekli"><span><b>ÇK-10488</b> · Korplas</span><span class="km-badge">bugün</span></div>
      <div class="km-cekli" style="border:none"><span><b>SNT-221</b> · Tarlasan</span><span style="color:#94a3b8">12 gün</span></div>
    </div>
  </div></div>

  <!-- SHOWCASE 3: Ürün kâr marjı -->
  <section style="background:#faf7ff;"><div class="km-wrap"><div class="km-show">
    <div class="km-show-txt">
      <h3>Ürün bazlı kâr marjı</h3>
      <p>Hangi üründen ne kadar kazandığınızı görün: ortalama alış fiyatı, ortalama satış fiyatı ve marj yüzdesi — dönem bazında. Fiyat dalgalanmalarında doğru kararı verin.</p>
      <ul class="km-check">
        <li>Ort. alış vs ort. satış fiyatı</li>
        <li>Ürün bazında kâr ve marj %</li>
        <li>Söküm/ayrıştırma verimi (hurda) desteği</li>
      </ul>
    </div>
    <div class="km-panel">
      <div class="km-ext-row" style="grid-template-columns:1fr 60px 60px 46px;font-weight:800;color:#64748b;font-size:10px"><span>ÜRÜN</span><span style="text-align:right">ALIŞ</span><span style="text-align:right">SATIŞ</span><span style="text-align:right">MARJ</span></div>
      <div class="km-ext-row" style="grid-template-columns:1fr 60px 60px 46px"><span class="b">PP Granül</span><span style="text-align:right">24,0</span><span style="text-align:right">32,0</span><span class="amt km-pos">%25</span></div>
      <div class="km-ext-row" style="grid-template-columns:1fr 60px 60px 46px"><span class="b">ABS Çapak</span><span style="text-align:right">18,5</span><span style="text-align:right">27,0</span><span class="amt km-pos">%31</span></div>
      <div class="km-ext-row" style="grid-template-columns:1fr 60px 60px 46px"><span class="b">Bakır</span><span style="text-align:right">210</span><span style="text-align:right">248</span><span class="amt km-pos">%15</span></div>
      <div class="km-ext-row" style="grid-template-columns:1fr 60px 60px 46px;border:none"><span class="b">Kristal</span><span style="text-align:right">42,0</span><span style="text-align:right">55,0</span><span class="amt km-pos">%24</span></div>
    </div>
  </div></div></section>

  <!-- CTA -->
  <section class="km-ctas">
    <h2>Hesabınıza giriş yapın</h2>
    <p>Kolay Muhasebe ile tüm işletmenizi tek panelden yönetin.</p>
    <a class="km-cta km-cta-w" href="/login">Giriş Yap →</a>
  </section>

  <div class="km-foot">© 2026 Kolay Muhasebe · Tüm hakları saklıdır</div>
</div>
'''


def render_landing():
    ui.query('body').style('margin:0;background:#faf7ff')
    # NiceGUI icerik kapsayicisini tam genislik yap (padding/max-width kaldir) — landing full-bleed
    ui.query('.nicegui-content').style('padding:0;margin:0;max-width:100%;width:100%;gap:0')
    ui.query('.q-page').style('padding:0')
    # CSS'i head'e koy (ui.html icindeki <style> uygulanmaz), govdeyi ui.html ile bas
    _css, _, _body = _HTML.partition('</style>')
    ui.add_head_html(_css + '</style>')
    ui.html(_body).classes('w-full')


@ui.page('/tanitim')
def tanitim_page():
    render_landing()
