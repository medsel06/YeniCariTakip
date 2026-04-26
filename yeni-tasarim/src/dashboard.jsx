function Dashboard({ onOpenCustomer }) {
  const totalAlacak = CUSTOMERS.reduce((s, c) => s + Math.max(0, c.balance), 0);
  const totalBorc = Math.abs(CUSTOMERS.reduce((s, c) => s + Math.min(0, c.balance), 0));
  const activeCount = CUSTOMERS.filter(c => c.status === 'active').length;

  // Month series
  const monthlyTahsilat = [285, 312, 278, 340, 395, 420, 388, 445, 510, 478, 522, 612];
  const monthlyFatura = [320, 345, 310, 378, 410, 455, 420, 480, 540, 520, 568, 640];
  const months = ['May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara', 'Oca', 'Şub', 'Mar', 'Nis'];

  // Top customers by balance
  const top = [...CUSTOMERS].filter(c => c.balance > 0).sort((a, b) => b.balance - a.balance).slice(0, 6);
  const maxTop = top[0]?.balance || 1;

  // Recent activity (last 6 tx across all)
  const recent = [...TRANSACTIONS].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6);

  return (
    <div>
      <div className="kpi-grid">
        <div className="kpi">
          <div className="kpi-label"><IconWallet size={14} /> Toplam Alacak</div>
          <div className="kpi-val num">{fmtTL(totalAlacak)}</div>
          <div className="kpi-delta up"><IconArrowUp size={12} /> %8,4 geçen aya göre</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><IconArrowDown size={14} /> Toplam Borç</div>
          <div className="kpi-val num">{fmtTL(totalBorc)}</div>
          <div className="kpi-delta down"><IconArrowDown size={12} /> %3,2 geçen aya göre</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><IconReceipt size={14} /> Bu Ay Tahsilat</div>
          <div className="kpi-val num">{fmtTL(612400)}</div>
          <div className="kpi-delta up"><IconArrowUp size={12} /> %17,2 artış</div>
        </div>
        <div className="kpi">
          <div className="kpi-label"><IconCari size={14} /> Aktif Cari</div>
          <div className="kpi-val num">{activeCount}</div>
          <div className="kpi-delta">{CUSTOMERS.length - activeCount} pasif cari</div>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-ttl">Aylık Hareket Özeti</div>
              <div className="card-sub">Son 12 ay · Fatura vs Tahsilat (bin ₺)</div>
            </div>
            <div className="grow" />
            <div className="hstack" style={{ fontSize: 12, color: 'var(--text-soft)' }}>
              <span className="hstack" style={{ gap: 6 }}><span style={{ width: 10, height: 10, background: 'var(--accent)', borderRadius: 2 }} /> Tahsilat</span>
              <span className="hstack" style={{ gap: 6 }}><span style={{ width: 10, height: 10, background: 'var(--border-strong)', borderRadius: 2 }} /> Fatura</span>
            </div>
          </div>
          <div style={{ padding: '18px 18px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 180 }}>
              {months.map((m, i) => {
                const max = Math.max(...monthlyFatura);
                return (
                  <div key={m} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                    <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-end', gap: 3 }}>
                      <div style={{ flex: 1, height: `${(monthlyTahsilat[i] / max) * 100}%`, background: 'var(--accent)', borderRadius: '3px 3px 0 0', opacity: i === months.length - 1 ? 1 : 0.85 }} />
                      <div style={{ flex: 1, height: `${(monthlyFatura[i] / max) * 100}%`, background: 'var(--border-strong)', borderRadius: '3px 3px 0 0' }} />
                    </div>
                    <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontFamily: 'IBM Plex Mono, monospace' }}>{m}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="card top-customers">
          <div className="card-hd">
            <div>
              <div className="card-ttl">En Yüksek Bakiyeler</div>
              <div className="card-sub">Alacak tutarına göre</div>
            </div>
          </div>
          {top.map((c, i) => (
            <div key={c.id} className="row" onClick={() => onOpenCustomer(c.id)} style={{ cursor: 'pointer' }}>
              <span className="tc-rank">{String(i + 1).padStart(2, '0')}</span>
              <span className="tc-name" title={c.name}>{c.name.length > 28 ? c.name.slice(0, 28) + '…' : c.name}</span>
              <div className="tc-bar"><div className="tc-bar-fill" style={{ width: `${(c.balance / maxTop) * 100}%` }} /></div>
              <span className="tc-val num">{fmtTL(c.balance)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <div>
            <div className="card-ttl">Son Hareketler</div>
            <div className="card-sub">Tüm carilerden son 6 kayıt</div>
          </div>
          <div className="grow" />
          <button className="btn btn-sm" onClick={() => window.__nav?.('ekstre')}>Tümünü Gör <IconChevRight size={14} /></button>
        </div>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Tarih</th><th>Cari</th><th>Belge No</th><th>Açıklama</th><th>Tip</th><th className="td-right">Borç</th><th className="td-right">Alacak</th></tr></thead>
            <tbody>
              {recent.map(t => {
                const c = CUSTOMERS.find(c => c.id === t.customerId);
                return (
                  <tr key={t.id} onClick={() => onOpenCustomer(t.customerId)}>
                    <td className="td-date">{fmtDate(t.date)}</td>
                    <td style={{ fontWeight: 500 }}>{c?.name}</td>
                    <td className="td-ref">{t.ref}</td>
                    <td style={{ color: 'var(--text-soft)' }}>{t.description}</td>
                    <td><DocTypeBadge type={t.type} /></td>
                    <td className="td-num">{t.borc ? fmtTL(t.borc) : '—'}</td>
                    <td className="td-num pos">{t.alacak ? fmtTL(t.alacak) : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

window.Dashboard = Dashboard;
