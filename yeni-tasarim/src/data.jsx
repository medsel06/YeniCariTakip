// Mock data. Turkish steel/metal industry — realistic customer names, invoice refs, amounts.

const fmtTL = (n, opts = {}) => {
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  const s = abs.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${sign}${s} ${opts.noSuffix ? '' : '₺'}`.trim();
};
const fmtTLShort = (n) => {
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${(n/1e6).toFixed(1).replace('.', ',')} M ₺`;
  if (abs >= 1e3) return `${(n/1e3).toFixed(0)} B ₺`;
  return fmtTL(n);
};
const fmtDate = (d) => {
  const dt = d instanceof Date ? d : new Date(d);
  return dt.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};
const fmtDateShort = (d) => {
  const dt = d instanceof Date ? d : new Date(d);
  return dt.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' });
};

// Customers
const CUSTOMERS = [
  { id: 'C-1042', code: '120.01.042', name: 'Yıldız İnşaat Malzemeleri A.Ş.', city: 'İstanbul', district: 'Pendik', phone: '0216 412 88 90', email: 'muhasebe@yildizinsaat.com.tr', tax: '9870012345', taxOffice: 'Pendik V.D.', balance: 284650.50, credit: 500000, lastActivity: '2026-04-16', paymentTerm: 45, status: 'active' },
  { id: 'C-1019', code: '120.01.019', name: 'Demir Çelik Ticaret Ltd. Şti.', city: 'İstanbul', district: 'Tuzla', phone: '0216 395 11 22', email: 'info@demircelikltd.com', tax: '4320098765', taxOffice: 'Tuzla V.D.', balance: 142800.00, credit: 300000, lastActivity: '2026-04-18', paymentTerm: 30, status: 'active' },
  { id: 'C-1078', code: '120.01.078', name: 'Karadeniz Metal Sanayi A.Ş.', city: 'Samsun', district: 'Atakum', phone: '0362 445 67 89', email: 'satinalma@kdzmetal.com.tr', tax: '6540087654', taxOffice: 'Atakum V.D.', balance: 98500.75, credit: 200000, lastActivity: '2026-04-15', paymentTerm: 60, status: 'active' },
  { id: 'C-1055', code: '120.01.055', name: 'Bayraktar Yapı Market', city: 'Ankara', district: 'Sincan', phone: '0312 278 90 11', email: 'bayraktaryapi@gmail.com', tax: '1230087456', taxOffice: 'Sincan V.D.', balance: -18400.00, credit: 150000, lastActivity: '2026-04-17', paymentTerm: 30, status: 'active' },
  { id: 'C-1033', code: '120.01.033', name: 'Ege Profil İnşaat Ltd.', city: 'İzmir', district: 'Çiğli', phone: '0232 376 55 44', email: 'info@egeprofil.com', tax: '8760054321', taxOffice: 'Çiğli V.D.', balance: 67200.00, credit: 150000, lastActivity: '2026-04-14', paymentTerm: 45, status: 'active' },
  { id: 'C-1088', code: '120.01.088', name: 'Güney Hırdavat Kollektif Şti.', city: 'Antalya', district: 'Kepez', phone: '0242 344 12 77', email: 'guney.hrd@outlook.com', tax: '3210054678', taxOffice: 'Kepez V.D.', balance: 38950.25, credit: 80000, lastActivity: '2026-04-10', paymentTerm: 30, status: 'active' },
  { id: 'C-1012', code: '120.01.012', name: 'Anadolu Yapı Kimyasalları', city: 'Konya', district: 'Selçuklu', phone: '0332 221 66 33', email: 'muhasebe@anadoluyapi.com', tax: '5670012890', taxOffice: 'Selçuklu V.D.', balance: 215400.00, credit: 400000, lastActivity: '2026-04-18', paymentTerm: 60, status: 'active' },
  { id: 'C-1099', code: '120.01.099', name: 'Marmara Çelik Konstrüksiyon', city: 'Kocaeli', district: 'Gebze', phone: '0262 642 33 11', email: 'info@marmaracelik.com.tr', tax: '2340087120', taxOffice: 'Gebze V.D.', balance: 425800.00, credit: 600000, lastActivity: '2026-04-19', paymentTerm: 45, status: 'active' },
  { id: 'C-1061', code: '120.01.061', name: 'Mete Hırdavat & Nalbur', city: 'Bursa', district: 'Nilüfer', phone: '0224 453 22 88', email: 'mete.hrd@hotmail.com', tax: '7890012345', taxOffice: 'Nilüfer V.D.', balance: 0, credit: 50000, lastActivity: '2026-04-02', paymentTerm: 15, status: 'passive' },
  { id: 'C-1025', code: '120.01.025', name: 'Doğu Anadolu Demir Tic.', city: 'Erzurum', district: 'Yakutiye', phone: '0442 233 11 66', email: 'doga.demir@gmail.com', tax: '6540012987', taxOffice: 'Yakutiye V.D.', balance: 52300.00, credit: 100000, lastActivity: '2026-04-12', paymentTerm: 30, status: 'active' },
];

// Transaction generator
const DOC_TYPES = ['fatura', 'tahsilat', 'cek', 'odeme', 'iade'];
const DOC_LABEL = { fatura: 'Satış Faturası', tahsilat: 'Tahsilat', cek: 'Çek/Senet', odeme: 'Ödeme', iade: 'İade Faturası' };
const DOC_CHIP = { fatura: 'neutral', tahsilat: 'green', cek: 'warn', odeme: 'red', iade: 'neutral' };

// Deterministic pseudo-random
function seeded(seed) {
  let x = seed;
  return () => { x = (x * 16807) % 2147483647; return (x - 1) / 2147483646; };
}

function genTransactions() {
  const rnd = seeded(42);
  const tx = [];
  let id = 10000;
  const today = new Date('2026-04-19');
  CUSTOMERS.forEach(c => {
    const count = Math.floor(rnd() * 18) + 8;
    let running = 0;
    const entries = [];
    for (let i = 0; i < count; i++) {
      const daysAgo = Math.floor(rnd() * 180);
      const d = new Date(today); d.setDate(d.getDate() - daysAgo);
      let type;
      const r = rnd();
      if (r < 0.55) type = 'fatura';
      else if (r < 0.85) type = 'tahsilat';
      else if (r < 0.93) type = 'cek';
      else if (r < 0.98) type = 'odeme';
      else type = 'iade';
      let amount;
      if (type === 'fatura') amount = +(rnd() * 45000 + 3500).toFixed(2);
      else if (type === 'tahsilat') amount = +(rnd() * 30000 + 5000).toFixed(2);
      else if (type === 'cek') amount = +(rnd() * 25000 + 5000).toFixed(2);
      else if (type === 'odeme') amount = +(rnd() * 8000 + 1000).toFixed(2);
      else amount = +(rnd() * 6000 + 500).toFixed(2);

      const borc = (type === 'fatura') ? amount : 0;
      const alacak = (type === 'tahsilat' || type === 'cek' || type === 'odeme' || type === 'iade') ? amount : 0;
      running += borc - alacak;

      entries.push({
        id: `T-${++id}`,
        customerId: c.id,
        date: d.toISOString().slice(0, 10),
        type,
        ref: refFor(type, id, rnd),
        description: descFor(type, c, rnd),
        borc, alacak,
        running: 0, // computed below
      });
    }
    entries.sort((a, b) => a.date.localeCompare(b.date));
    let run = 0;
    entries.forEach(e => { run += e.borc - e.alacak; e.running = run; });
    tx.push(...entries);
  });
  return tx;
}

function refFor(type, n, rnd) {
  const ys = '2026';
  if (type === 'fatura') return `FT${ys}-${String(n).padStart(5, '0')}`;
  if (type === 'iade') return `IF${ys}-${String(n).padStart(5, '0')}`;
  if (type === 'tahsilat') return `TH${ys}-${String(n).padStart(5, '0')}`;
  if (type === 'cek') return `CK${ys}-${String(n).padStart(5, '0')}`;
  if (type === 'odeme') return `OD${ys}-${String(n).padStart(5, '0')}`;
  return String(n);
}
function descFor(type, c, rnd) {
  const products = ['Ø12 İnşaat demiri', 'Ø16 nervürlü demir', 'HEA 120 profil', 'Kare profil 40x40', 'Sac levha 2mm', 'L köşebent 50x50', 'U demir', 'IPE 200', 'Galvaniz tel', 'Hasır çelik Q188'];
  const p = products[Math.floor(rnd() * products.length)];
  const tonaj = +(rnd() * 8 + 0.5).toFixed(1);
  if (type === 'fatura') return `${p} — ${tonaj} ton`;
  if (type === 'iade') return `${p} — iade`;
  if (type === 'tahsilat') return ['Havale', 'EFT', 'Nakit tahsilat', 'Kredi kartı'][Math.floor(rnd() * 4)];
  if (type === 'cek') {
    const d = new Date('2026-04-19'); d.setDate(d.getDate() + Math.floor(rnd() * 90) + 30);
    return `Vadeli çek — ${fmtDate(d)}`;
  }
  if (type === 'odeme') return 'Banka masrafı / komisyon';
  return '';
}

const TRANSACTIONS = genTransactions();

Object.assign(window, { CUSTOMERS, TRANSACTIONS, DOC_TYPES, DOC_LABEL, DOC_CHIP, fmtTL, fmtTLShort, fmtDate, fmtDateShort });
