// Shared UI: Sidebar, Topbar, BalanceChip, Sparkline.

function Sidebar({ page, onNav }) {
  const items = [
    { id: 'dashboard', label: 'Panel', icon: <IconDashboard /> },
    { id: 'cariler', label: 'Cari Kartlar', icon: <IconCari />, badge: String(CUSTOMERS.length) },
    { id: 'ekstre', label: 'Ekstre', icon: <IconEkstre /> },
    { id: 'rapor', label: 'Raporlar', icon: <IconReport /> },
  ];
  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div className="sb-logo">ŞÇ</div>
        <div>
          <div className="sb-brand-name">ŞENOL ÇELİK</div>
          <div className="sb-brand-sub">Cari Takip · v2.4</div>
        </div>
      </div>

      <div className="sb-section-title">Ana Menü</div>
      <nav className="sb-nav">
        {items.map(it => (
          <button key={it.id} className={`sb-item ${page === it.id ? 'active' : ''}`} onClick={() => onNav(it.id)}>
            {it.icon}
            <span>{it.label}</span>
            {it.badge && <span className="sb-badge">{it.badge}</span>}
          </button>
        ))}
      </nav>

      <div className="sb-section-title">Hızlı</div>
      <nav className="sb-nav">
        <button className="sb-item" onClick={() => window.__openModal?.('collection')}>
          <IconPlus /><span>Tahsilat</span>
        </button>
        <button className="sb-item" onClick={() => window.__openModal?.('payment')}>
          <IconArrowDown /><span>Ödeme</span>
        </button>
        <button className="sb-item" onClick={() => window.__openModal?.('invoice')}>
          <IconInvoice /><span>Fatura Kes</span>
        </button>
      </nav>

      <div className="sb-foot">
        <div className="avatar">MY</div>
        <div>
          <div className="sb-user-name">Mustafa Yıldırım</div>
          <div className="sb-user-role">Muhasebe</div>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ title, crumb, onSearch, searchValue }) {
  return (
    <div className="topbar">
      <div>
        {crumb && <div className="tb-crumb">{crumb}</div>}
        <div className="tb-title">{title}</div>
      </div>
      <div className="tb-spacer" />
      <div className="tb-search">
        <IconSearch size={16} />
        <input placeholder="Cari, belge no veya açıklama ara…" value={searchValue || ''} onChange={e => onSearch?.(e.target.value)} />
        <kbd>⌘K</kbd>
      </div>
      <button className="btn btn-icon btn-ghost" title="Bildirimler"><IconBell size={17} /></button>
    </div>
  );
}

function BalanceChip({ value, size = 'md' }) {
  const neg = value < 0;
  const label = neg ? 'Alacak' : 'Borç';
  return (
    <span className={`balance-chip ${neg ? 'neg' : ''}`} style={size === 'lg' ? { padding: '7px 16px' } : {}}>
      <span className="bc-label">{label}</span>
      <span className="bc-val" style={size === 'lg' ? { fontSize: '16px' } : {}}>{fmtTL(Math.abs(value))}</span>
    </span>
  );
}

function Chip({ kind = 'neutral', children, dot = true }) {
  return <span className={`chip chip-${kind}`}>{dot && <span className="chip-dot" />}{children}</span>;
}

function Sparkline({ data, color = 'var(--accent)', height = 50, fill = true }) {
  if (!data || !data.length) return null;
  const w = 280, h = height, pad = 4;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => [
    pad + (i / (data.length - 1)) * (w - pad * 2),
    h - pad - ((v - min) / range) * (h - pad * 2)
  ]);
  const path = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const area = path + ` L${w - pad},${h - pad} L${pad},${h - pad} Z`;
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
      {fill && <path d={area} fill={color} opacity="0.12" />}
      <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

function BarChart({ data, labels, height = 160, color = 'var(--accent)' }) {
  const max = Math.max(...data) || 1;
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height, padding: '0 4px' }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
          <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-end' }}>
            <div style={{ width: '100%', height: `${(v / max) * 100}%`, background: color, borderRadius: '4px 4px 0 0', opacity: i === data.length - 1 ? 1 : 0.75, transition: 'height 0.3s' }} />
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontFamily: 'IBM Plex Mono, monospace' }}>{labels[i]}</div>
        </div>
      ))}
    </div>
  );
}

function DocTypeBadge({ type }) {
  return <Chip kind={DOC_CHIP[type]}>{DOC_LABEL[type]}</Chip>;
}

function Toast({ message, onDone }) {
  React.useEffect(() => {
    const t = setTimeout(onDone, 2200);
    return () => clearTimeout(t);
  }, []);
  return <div className="toast">{message}</div>;
}

Object.assign(window, { Sidebar, Topbar, BalanceChip, Chip, Sparkline, BarChart, DocTypeBadge, Toast });
