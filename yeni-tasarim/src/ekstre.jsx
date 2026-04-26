function Ekstre({ initialCustomerId, search, onOpenCustomer }) {
  const [selected, setSelected] = React.useState(initialCustomerId || CUSTOMERS[0].id);
  const [typeFilter, setTypeFilter] = React.useState('all');
  const [range, setRange] = React.useState('90');
  const [localSearch, setLocalSearch] = React.useState('');

  React.useEffect(() => { if (initialCustomerId) setSelected(initialCustomerId); }, [initialCustomerId]);

  const customer = CUSTOMERS.find(c => c.id === selected);
  const q = (search || localSearch || '').toLowerCase().trim();

  let txs = TRANSACTIONS.filter(t => t.customerId === selected);
  if (typeFilter !== 'all') txs = txs.filter(t => t.type === typeFilter);
  if (range !== 'all') {
    const days = parseInt(range, 10);
    const cutoff = new Date('2026-04-19'); cutoff.setDate(cutoff.getDate() - days);
    txs = txs.filter(t => new Date(t.date) >= cutoff);
  }
  if (q) txs = txs.filter(t => (t.ref + ' ' + t.description).toLowerCase().includes(q));
  txs = [...txs].sort((a, b) => b.date.localeCompare(a.date));

  const toplamBorc = txs.reduce((s, t) => s + t.borc, 0);
  const toplamAlacak = txs.reduce((s, t) => s + t.alacak, 0);

  const filteredCustomers = CUSTOMERS.filter(c => q ? c.name.toLowerCase().includes(q) : true);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
      {/* Customer list */}
      <div className="card" style={{ alignSelf: 'start', position: 'sticky', top: 76 }}>
        <div className="card-hd" style={{ padding: '10px 14px' }}>
          <div className="card-ttl" style={{ fontSize: 13 }}>Cariler</div>
          <div className="grow" />
          <span className="muted" style={{ fontSize: 11 }}>{filteredCustomers.length}</span>
        </div>
        <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          {filteredCustomers.map(c => (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                width: '100%', padding: '10px 14px', textAlign: 'left',
                borderBottom: '1px solid var(--border)',
                background: selected === c.id ? 'var(--accent-soft)' : 'transparent',
                borderLeft: selected === c.id ? '3px solid var(--accent)' : '3px solid transparent',
                transition: 'background 0.1s'
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: selected === c.id ? 'var(--accent-ink)' : 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</div>
                <div className="num" style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>{c.code}</div>
              </div>
              <div className="num" style={{ fontSize: 12, fontWeight: 600, color: c.balance < 0 ? 'var(--danger)' : 'var(--accent-ink)', whiteSpace: 'nowrap' }}>
                {fmtTLShort(c.balance)}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Ekstre content */}
      <div>
        {/* Header strip */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="hstack" style={{ gap: 10 }}>
                <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em' }}>{customer.name}</div>
                <Chip kind={customer.status === 'active' ? 'green' : 'neutral'}>{customer.status === 'active' ? 'Aktif' : 'Pasif'}</Chip>
              </div>
              <div className="hstack" style={{ gap: 14, marginTop: 4, fontSize: 12, color: 'var(--text-soft)' }}>
                <span className="num">{customer.code}</span>
                <span>·</span>
                <span className="hstack" style={{ gap: 4 }}><IconMap size={12} />{customer.city} / {customer.district}</span>
                <span>·</span>
                <span className="hstack" style={{ gap: 4 }}><IconPhone size={12} />{customer.phone}</span>
              </div>
            </div>
            <BalanceChip value={customer.balance} size="lg" />
            <button className="btn btn-sm" onClick={() => onOpenCustomer(customer.id)}>Cari Kart <IconChevRight size={13} /></button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="filterbar">
          <div className="seg">
            {[
              { id: '30', l: '30 gün' },
              { id: '90', l: '90 gün' },
              { id: '180', l: '6 ay' },
              { id: 'all', l: 'Tümü' },
            ].map(r => (
              <button key={r.id} className={range === r.id ? 'active' : ''} onClick={() => setRange(r.id)}>{r.l}</button>
            ))}
          </div>
          <button className={`flt ${typeFilter !== 'all' ? 'active' : ''}`}>
            <IconTag size={14} />
            <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
              <option value="all">Tüm Belgeler</option>
              {DOC_TYPES.map(t => <option key={t} value={t}>{DOC_LABEL[t]}</option>)}
            </select>
            <IconChevDown size={13} />
          </button>
          <div className="flt" style={{ cursor: 'default' }}>
            <IconCal size={14} />
            <span className="num" style={{ fontSize: 12.5 }}>01.01.2026 — 19.04.2026</span>
          </div>
          <div className="tb-search" style={{ width: 260, marginLeft: 'auto' }}>
            <IconSearch size={14} />
            <input placeholder="Belge/açıklamada ara…" value={localSearch} onChange={e => setLocalSearch(e.target.value)} />
          </div>
          <button className="btn btn-sm"><IconPdf size={14} /> PDF</button>
          <button className="btn btn-sm"><IconXls size={14} /> Excel</button>
          <button className="btn btn-sm btn-primary" onClick={() => window.__openModal?.('collection', customer.id)}><IconPlus size={14} /> Tahsilat</button>
        </div>

        {/* Summary strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
          <div className="card" style={{ padding: '14px 18px' }}>
            <div className="kpi-label">Dönem Borç (Fatura)</div>
            <div className="num" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{fmtTL(toplamBorc)}</div>
          </div>
          <div className="card" style={{ padding: '14px 18px' }}>
            <div className="kpi-label">Dönem Alacak (Tahsilat)</div>
            <div className="num pos" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{fmtTL(toplamAlacak)}</div>
          </div>
          <div className="card" style={{ padding: '14px 18px' }}>
            <div className="kpi-label">Net Bakiye</div>
            <div className={`num ${customer.balance < 0 ? 'neg' : ''}`} style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{fmtTL(customer.balance)}</div>
          </div>
        </div>

        {/* Transactions */}
        <div className="card">
          <div className="card-hd">
            <div className="card-ttl">Hareketler</div>
            <span className="muted" style={{ fontSize: 12 }}>{txs.length} kayıt</span>
            <div className="grow" />
            <button className="btn-ghost btn btn-sm"><IconSort size={13} /> Sırala</button>
          </div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: 100 }}>Tarih</th>
                  <th style={{ width: 140 }}>Belge No</th>
                  <th>Açıklama</th>
                  <th style={{ width: 130 }}>Tip</th>
                  <th className="td-right" style={{ width: 130 }}>Borç</th>
                  <th className="td-right" style={{ width: 130 }}>Alacak</th>
                  <th className="td-right" style={{ width: 140 }}>Bakiye</th>
                </tr>
              </thead>
              <tbody>
                {txs.length === 0 && <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>Bu filtre için hareket bulunamadı.</td></tr>}
                {txs.map(t => (
                  <tr key={t.id}>
                    <td className="td-date">{fmtDate(t.date)}</td>
                    <td className="td-ref">{t.ref}</td>
                    <td style={{ color: 'var(--text)' }}>{t.description}</td>
                    <td><DocTypeBadge type={t.type} /></td>
                    <td className="td-num">{t.borc ? fmtTL(t.borc) : <span className="muted">—</span>}</td>
                    <td className="td-num pos">{t.alacak ? fmtTL(t.alacak) : <span className="muted">—</span>}</td>
                    <td className="td-num" style={{ fontWeight: 600, color: t.running < 0 ? 'var(--danger)' : 'var(--text)' }}>{fmtTL(t.running)}</td>
                  </tr>
                ))}
              </tbody>
              {txs.length > 0 && (
                <tfoot>
                  <tr style={{ background: 'var(--panel-soft)', fontWeight: 600 }}>
                    <td colSpan={4} style={{ padding: '12px 14px', fontSize: 12, color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Dönem Toplamı</td>
                    <td className="td-num" style={{ padding: '12px 14px' }}>{fmtTL(toplamBorc)}</td>
                    <td className="td-num pos" style={{ padding: '12px 14px' }}>{fmtTL(toplamAlacak)}</td>
                    <td className="td-num" style={{ padding: '12px 14px', color: customer.balance < 0 ? 'var(--danger)' : 'var(--text)' }}>{fmtTL(customer.balance)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

window.Ekstre = Ekstre;
