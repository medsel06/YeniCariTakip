function CustomerDetail({ customerId, onOpenEkstre, onBack }) {
  const c = CUSTOMERS.find(c => c.id === customerId);
  const txs = TRANSACTIONS.filter(t => t.customerId === customerId).sort((a, b) => b.date.localeCompare(a.date));

  // 30-day balance series for sparkline
  const series = React.useMemo(() => {
    const sorted = [...TRANSACTIONS.filter(t => t.customerId === customerId)].sort((a, b) => a.date.localeCompare(b.date));
    let r = 0;
    const pts = sorted.map(t => { r += t.borc - t.alacak; return r; });
    return pts.length > 1 ? pts : [0, 0];
  }, [customerId]);

  const totalFatura = txs.filter(t => t.type === 'fatura').reduce((s, t) => s + t.borc, 0);
  const totalTahsilat = txs.filter(t => t.type === 'tahsilat' || t.type === 'cek').reduce((s, t) => s + t.alacak, 0);
  const openCek = txs.filter(t => t.type === 'cek').reduce((s, t) => s + t.alacak, 0);

  return (
    <div>
      <div className="hstack" style={{ marginBottom: 14, gap: 10 }}>
        <button className="btn btn-sm btn-ghost" onClick={onBack}><IconChevRight size={13} style={{ transform: 'rotate(180deg)' }} /> Geri</button>
        <span className="muted" style={{ fontSize: 12 }}>Cariler / {c.name}</span>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="cd-hero">
          <div className="cd-avatar">{c.name.split(' ').slice(0, 2).map(w => w[0]).join('')}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="hstack" style={{ gap: 10 }}>
              <div className="cd-name">{c.name}</div>
              <Chip kind={c.status === 'active' ? 'green' : 'neutral'}>{c.status === 'active' ? 'Aktif' : 'Pasif'}</Chip>
            </div>
            <div className="cd-meta">
              <span className="num">{c.code}</span>
              <span className="hstack" style={{ gap: 5 }}><IconMap size={12} />{c.city} / {c.district}</span>
              <span className="hstack" style={{ gap: 5 }}><IconPhone size={12} />{c.phone}</span>
              <span className="hstack" style={{ gap: 5 }}><IconMail size={12} />{c.email}</span>
              <span>VKN: <span className="num">{c.tax}</span> · {c.taxOffice}</span>
            </div>
          </div>
          <div className="hstack" style={{ gap: 8 }}>
            <BalanceChip value={c.balance} size="lg" />
            <button className="btn btn-sm" onClick={() => onOpenEkstre(c.id)}><IconEkstre size={14} /> Ekstre</button>
            <button className="btn btn-sm btn-primary" onClick={() => window.__openModal?.('collection', c.id)}><IconPlus size={14} /> Tahsilat</button>
            <button className="btn btn-icon btn-ghost"><IconMore size={16} /></button>
          </div>
        </div>
        <div className="cd-stats">
          <div className="cd-stat">
            <div className="cd-stat-lbl">Kredi Limiti</div>
            <div className="cd-stat-val num">{fmtTL(c.credit)}</div>
            <div className="cd-stat-sub">Kullanım: %{((Math.max(0, c.balance) / c.credit) * 100).toFixed(0)}</div>
          </div>
          <div className="cd-stat">
            <div className="cd-stat-lbl">Vade</div>
            <div className="cd-stat-val num">{c.paymentTerm} gün</div>
            <div className="cd-stat-sub">Fatura tarihinden itibaren</div>
          </div>
          <div className="cd-stat">
            <div className="cd-stat-lbl">Açık Çek/Senet</div>
            <div className="cd-stat-val num">{fmtTL(openCek)}</div>
            <div className="cd-stat-sub">{txs.filter(t => t.type === 'cek').length} adet</div>
          </div>
          <div className="cd-stat">
            <div className="cd-stat-lbl">Son İşlem</div>
            <div className="cd-stat-val">{fmtDate(c.lastActivity)}</div>
            <div className="cd-stat-sub">{Math.floor((new Date('2026-04-19') - new Date(c.lastActivity)) / 86400000)} gün önce</div>
          </div>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-hd">
            <div>
              <div className="card-ttl">Bakiye Gelişimi</div>
              <div className="card-sub">Son {txs.length} hareket boyunca</div>
            </div>
          </div>
          <div style={{ padding: '16px 20px' }}>
            <Sparkline data={series} height={140} color={c.balance < 0 ? 'var(--danger)' : 'var(--accent)'} />
          </div>
        </div>

        <div className="card">
          <div className="card-hd"><div className="card-ttl">Dönem Özeti</div></div>
          <div style={{ padding: '6px 0' }}>
            <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--text-soft)', fontSize: 13 }}>Toplam Fatura</span>
              <span className="num" style={{ fontWeight: 600 }}>{fmtTL(totalFatura)}</span>
            </div>
            <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--text-soft)', fontSize: 13 }}>Toplam Tahsilat</span>
              <span className="num pos" style={{ fontWeight: 600 }}>{fmtTL(totalTahsilat)}</span>
            </div>
            <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
              <span style={{ color: 'var(--text-soft)', fontSize: 13 }}>Ortalama Tahsilat Süresi</span>
              <span className="num" style={{ fontWeight: 600 }}>32 gün</span>
            </div>
            <div style={{ padding: '12px 20px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-soft)', fontSize: 13 }}>Risk Skoru</span>
              <Chip kind={c.balance > c.credit * 0.8 ? 'warn' : 'green'}>{c.balance > c.credit * 0.8 ? 'Orta' : 'Düşük'}</Chip>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-hd">
          <div className="card-ttl">Son Hareketler</div>
          <div className="grow" />
          <button className="btn btn-sm" onClick={() => onOpenEkstre(c.id)}>Tüm Ekstreyi Aç <IconChevRight size={13} /></button>
        </div>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Tarih</th><th>Belge No</th><th>Açıklama</th><th>Tip</th><th className="td-right">Borç</th><th className="td-right">Alacak</th></tr></thead>
            <tbody>
              {txs.slice(0, 8).map(t => (
                <tr key={t.id}>
                  <td className="td-date">{fmtDate(t.date)}</td>
                  <td className="td-ref">{t.ref}</td>
                  <td>{t.description}</td>
                  <td><DocTypeBadge type={t.type} /></td>
                  <td className="td-num">{t.borc ? fmtTL(t.borc) : '—'}</td>
                  <td className="td-num pos">{t.alacak ? fmtTL(t.alacak) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

window.CustomerDetail = CustomerDetail;
