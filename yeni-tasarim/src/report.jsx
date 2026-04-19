function Report() {
  const [period, setPeriod] = React.useState('month');

  const byCity = {};
  CUSTOMERS.forEach(c => { byCity[c.city] = (byCity[c.city] || 0) + Math.max(0, c.balance); });
  const cities = Object.entries(byCity).sort((a, b) => b[1] - a[1]);
  const maxCity = cities[0]?.[1] || 1;

  const typeTotals = {};
  TRANSACTIONS.forEach(t => {
    typeTotals[t.type] = (typeTotals[t.type] || 0) + (t.borc || t.alacak);
  });
  const typeArr = Object.entries(typeTotals).map(([k, v]) => ({ k, v }));
  const maxType = Math.max(...typeArr.map(t => t.v));

  const aging = [
    { label: '0–30 gün', value: 412500, color: 'var(--accent)' },
    { label: '31–60 gün', value: 284300, color: 'oklch(0.72 0.12 130)' },
    { label: '61–90 gün', value: 128400, color: 'var(--warn)' },
    { label: '90+ gün', value: 62800, color: 'var(--danger)' },
  ];
  const totalAging = aging.reduce((s, a) => s + a.value, 0);

  return (
    <div>
      {/* Filter strip */}
      <div className="card" style={{ marginBottom: 16, padding: '14px 18px' }}>
        <div className="hstack" style={{ gap: 12, flexWrap: 'wrap' }}>
          <div className="seg">
            {[['week', 'Bu Hafta'], ['month', 'Bu Ay'], ['quarter', 'Çeyrek'], ['year', '2026']].map(([k, l]) => (
              <button key={k} className={period === k ? 'active' : ''} onClick={() => setPeriod(k)}>{l}</button>
            ))}
          </div>
          <div className="flt"><IconCal size={14} /><span className="num" style={{ fontSize: 12.5 }}>01.04.2026 — 30.04.2026</span></div>
          <div className="flt"><IconTag size={14} /><span>Tüm Belgeler</span><IconChevDown size={13} /></div>
          <div className="flt"><IconFilter size={14} /><span>Tüm Şubeler</span><IconChevDown size={13} /></div>
          <div className="grow" />
          <button className="btn btn-sm"><IconPdf size={14} /> PDF Rapor</button>
          <button className="btn btn-sm"><IconXls size={14} /> Excel</button>
        </div>
      </div>

      {/* KPIs */}
      <div className="kpi-grid">
        <div className="kpi"><div className="kpi-label">Cari Hesap Sayısı</div><div className="kpi-val num">{CUSTOMERS.length}</div><div className="kpi-delta">+2 bu ay</div></div>
        <div className="kpi"><div className="kpi-label">Dönem Faturası</div><div className="kpi-val num">{fmtTL(TRANSACTIONS.filter(t => t.type === 'fatura').reduce((s, t) => s + t.borc, 0))}</div><div className="kpi-delta up"><IconArrowUp size={12} /> %12 artış</div></div>
        <div className="kpi"><div className="kpi-label">Tahsil Edilen</div><div className="kpi-val num">{fmtTL(TRANSACTIONS.filter(t => t.type === 'tahsilat').reduce((s, t) => s + t.alacak, 0))}</div><div className="kpi-delta up"><IconArrowUp size={12} /> %8 artış</div></div>
        <div className="kpi"><div className="kpi-label">Tahsilat Oranı</div><div className="kpi-val num">%68,4</div><div className="kpi-delta">Hedef: %75</div></div>
      </div>

      <div className="rp-grid">
        {/* Aging */}
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-ttl">Yaşlandırma Analizi</div>
              <div className="card-sub">Vade tarihine göre açık alacaklar</div>
            </div>
          </div>
          <div style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', height: 14, borderRadius: 7, overflow: 'hidden', marginBottom: 14 }}>
              {aging.map(a => (
                <div key={a.label} style={{ width: `${(a.value / totalAging) * 100}%`, background: a.color }} />
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {aging.map(a => (
                <div key={a.label} className="hstack">
                  <span style={{ width: 10, height: 10, borderRadius: 3, background: a.color }} />
                  <span style={{ flex: 1, fontSize: 13 }}>{a.label}</span>
                  <span className="num" style={{ fontSize: 12.5, color: 'var(--text-dim)', width: 50, textAlign: 'right' }}>%{((a.value / totalAging) * 100).toFixed(0)}</span>
                  <span className="num" style={{ fontWeight: 600, width: 140, textAlign: 'right' }}>{fmtTL(a.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* City breakdown */}
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-ttl">Şehir Bazlı Alacak</div>
              <div className="card-sub">Toplam açık alacak dağılımı</div>
            </div>
          </div>
          <div style={{ padding: '12px 0' }}>
            {cities.map(([city, val]) => (
              <div key={city} style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border)' }}>
                <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{city}</span>
                <div style={{ width: 120, height: 4, background: 'var(--panel-soft)', borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--accent)', width: `${(val / maxCity) * 100}%` }} />
                </div>
                <span className="num" style={{ width: 110, textAlign: 'right', fontWeight: 600, fontSize: 12.5 }}>{fmtTL(val)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Doc type breakdown */}
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-hd">
            <div>
              <div className="card-ttl">Belge Tipi Dağılımı</div>
              <div className="card-sub">Tüm hareketler · Nisan 2026</div>
            </div>
          </div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Belge Tipi</th><th>Adet</th><th>Toplam Tutar</th><th>Ortalama</th><th style={{ width: '40%' }}>Oran</th></tr></thead>
              <tbody>
                {typeArr.map(({ k, v }) => {
                  const count = TRANSACTIONS.filter(t => t.type === k).length;
                  return (
                    <tr key={k}>
                      <td><DocTypeBadge type={k} /></td>
                      <td className="num">{count}</td>
                      <td className="td-num" style={{ fontWeight: 600 }}>{fmtTL(v)}</td>
                      <td className="td-num">{fmtTL(v / count)}</td>
                      <td>
                        <div className="hstack" style={{ gap: 8 }}>
                          <div style={{ flex: 1, height: 6, background: 'var(--panel-soft)', borderRadius: 999, overflow: 'hidden' }}>
                            <div style={{ height: '100%', background: 'var(--accent)', width: `${(v / maxType) * 100}%` }} />
                          </div>
                          <span className="num muted" style={{ fontSize: 12, width: 46, textAlign: 'right' }}>%{((v / typeArr.reduce((s, t) => s + t.v, 0)) * 100).toFixed(0)}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

window.Report = Report;
