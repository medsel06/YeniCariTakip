// App shell — routing, modal state, tweaks, theme persistence.

function App() {
  const [page, setPage] = React.useState(() => localStorage.getItem('page') || 'dashboard');
  const [focusCustomer, setFocusCustomer] = React.useState(null);
  const [modal, setModal] = React.useState(null); // { kind, customerId }
  const [toast, setToast] = React.useState(null);
  const [globalSearch, setGlobalSearch] = React.useState('');
  const [tweaksVisible, setTweaksVisible] = React.useState(false);
  const [theme, setTheme] = React.useState(() => {
    try { return JSON.parse(document.getElementById('tweak-defaults').textContent.match(/\{.*\}/s)[0]).theme || 'light'; } catch { return 'light'; }
  });

  React.useEffect(() => { localStorage.setItem('page', page); }, [page]);
  React.useEffect(() => { document.documentElement.setAttribute('data-theme', theme); }, [theme]);

  // Globals used by Sidebar quick actions and cross-component hooks
  window.__nav = setPage;
  window.__openModal = (kind, customerId) => setModal({ kind, customerId });

  // Edit-mode protocol
  React.useEffect(() => {
    const onMsg = (e) => {
      const d = e.data || {};
      if (d.type === '__activate_edit_mode') setTweaksVisible(true);
      if (d.type === '__deactivate_edit_mode') setTweaksVisible(false);
    };
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);

  const setKey = (k, v) => {
    if (k === 'theme') setTheme(v);
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [k]: v } }, '*');
  };

  const nav = (p) => { setPage(p); setFocusCustomer(null); };
  const openCustomer = (id) => { setFocusCustomer(id); setPage('cari'); };
  const openEkstre = (id) => { setFocusCustomer(id); setPage('ekstre'); };

  const pageMeta = {
    dashboard: { title: 'Panel', crumb: 'Genel Bakış' },
    cariler: { title: 'Cari Kartlar', crumb: 'Cariler' },
    cari: { title: 'Cari Kart Detayı', crumb: 'Cariler / Detay' },
    ekstre: { title: 'Hesap Ekstresi', crumb: 'Cariler / Ekstre' },
    rapor: { title: 'Raporlar', crumb: 'Raporlama' },
  };
  const meta = pageMeta[page] || pageMeta.dashboard;

  return (
    <div id="root" data-screen-label={page}>
      <Sidebar page={page === 'cari' ? 'cariler' : page} onNav={nav} />
      <div className="main">
        <Topbar title={meta.title} crumb={meta.crumb} onSearch={setGlobalSearch} searchValue={globalSearch} />
        <div className="content">
          {page === 'dashboard' && <Dashboard onOpenCustomer={openCustomer} />}
          {page === 'ekstre' && <Ekstre initialCustomerId={focusCustomer} search={globalSearch} onOpenCustomer={openCustomer} />}
          {page === 'cariler' && <CariListPage onOpen={openCustomer} search={globalSearch} />}
          {page === 'cari' && <CustomerDetail customerId={focusCustomer || CUSTOMERS[0].id} onOpenEkstre={openEkstre} onBack={() => nav('cariler')} />}
          {page === 'rapor' && <Report />}
        </div>
      </div>

      {modal && <TxModal kind={modal.kind} customerId={modal.customerId} onClose={() => setModal(null)} onSaved={(m) => { setModal(null); setToast(m); }} />}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {tweaksVisible && (
        <div className="tweaks">
          <div>
            <div className="tweak-ttl">Tweaks</div>
            <div style={{ fontSize: 13, fontWeight: 500, marginTop: 2 }}>Tema</div>
          </div>
          <div className="hstack" style={{ gap: 8 }}>
            <IconSun size={15} style={{ color: theme === 'light' ? 'var(--text)' : 'var(--text-dim)' }} />
            <button className={`toggle ${theme === 'dark' ? 'on' : ''}`} onClick={() => setKey('theme', theme === 'dark' ? 'light' : 'dark')} aria-label="Tema değiştir" />
            <IconMoon size={15} style={{ color: theme === 'dark' ? 'var(--text)' : 'var(--text-dim)' }} />
          </div>
        </div>
      )}
    </div>
  );
}

// Simple list page for "Cariler"
function CariListPage({ onOpen, search }) {
  const q = (search || '').toLowerCase().trim();
  let list = CUSTOMERS;
  if (q) list = list.filter(c => (c.name + ' ' + c.code + ' ' + c.city).toLowerCase().includes(q));
  const [sort, setSort] = React.useState('name');
  list = [...list].sort((a, b) => {
    if (sort === 'balance') return b.balance - a.balance;
    if (sort === 'city') return a.city.localeCompare(b.city);
    return a.name.localeCompare(b.name);
  });

  return (
    <div>
      <div className="filterbar">
        <div className="seg">
          <button className={sort === 'name' ? 'active' : ''} onClick={() => setSort('name')}>İsim</button>
          <button className={sort === 'balance' ? 'active' : ''} onClick={() => setSort('balance')}>Bakiye</button>
          <button className={sort === 'city' ? 'active' : ''} onClick={() => setSort('city')}>Şehir</button>
        </div>
        <div className="flt"><IconFilter size={14} /><span>Tüm Durumlar</span><IconChevDown size={13} /></div>
        <div className="grow" />
        <button className="btn btn-sm"><IconXls size={14} /> Excel</button>
        <button className="btn btn-sm btn-primary"><IconPlus size={14} /> Yeni Cari</button>
      </div>
      <div className="card">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Cari Kodu</th>
                <th>Ünvan</th>
                <th>Şehir</th>
                <th>Son İşlem</th>
                <th>Durum</th>
                <th>Kredi Kullanımı</th>
                <th className="td-right">Bakiye</th>
                <th style={{ width: 1 }}></th>
              </tr>
            </thead>
            <tbody>
              {list.map(c => {
                const usage = Math.max(0, c.balance) / c.credit;
                return (
                  <tr key={c.id} onClick={() => onOpen(c.id)}>
                    <td className="num" style={{ color: 'var(--text-dim)' }}>{c.code}</td>
                    <td style={{ fontWeight: 500 }}>{c.name}</td>
                    <td style={{ color: 'var(--text-soft)' }}>{c.city}</td>
                    <td className="td-date">{fmtDate(c.lastActivity)}</td>
                    <td><Chip kind={c.status === 'active' ? 'green' : 'neutral'}>{c.status === 'active' ? 'Aktif' : 'Pasif'}</Chip></td>
                    <td>
                      <div className="hstack" style={{ gap: 8, minWidth: 140 }}>
                        <div style={{ flex: 1, height: 5, background: 'var(--panel-soft)', borderRadius: 999, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${Math.min(100, usage * 100)}%`, background: usage > 0.8 ? 'var(--danger)' : usage > 0.5 ? 'var(--warn)' : 'var(--accent)' }} />
                        </div>
                        <span className="num muted" style={{ fontSize: 11.5, width: 36 }}>%{(usage * 100).toFixed(0)}</span>
                      </div>
                    </td>
                    <td className="td-num" style={{ fontWeight: 600, color: c.balance < 0 ? 'var(--danger)' : 'var(--text)' }}>{fmtTL(c.balance)}</td>
                    <td><IconChevRight size={14} style={{ color: 'var(--text-dim)' }} /></td>
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

window.App = App;
window.CariListPage = CariListPage;

ReactDOM.createRoot(document.getElementById('app')).render(<App />);
