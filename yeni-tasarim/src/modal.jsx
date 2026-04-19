function TxModal({ kind, customerId, onClose, onSaved }) {
  const [type, setType] = React.useState(kind === 'payment' ? 'payment' : 'collection');
  const [cust, setCust] = React.useState(customerId || CUSTOMERS[0].id);
  const [amount, setAmount] = React.useState('');
  const [method, setMethod] = React.useState('havale');
  const [date, setDate] = React.useState('2026-04-19');
  const [note, setNote] = React.useState('');

  const customer = CUSTOMERS.find(c => c.id === cust);

  const submit = (e) => {
    e.preventDefault();
    onSaved?.(type === 'collection' ? 'Tahsilat kaydedildi.' : 'Ödeme kaydedildi.');
  };

  const isCollection = type === 'collection';

  return (
    <div className="modal-scrim" onClick={onClose}>
      <form className="modal" onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-hd">
          <div style={{ width: 34, height: 34, borderRadius: 9, background: isCollection ? 'var(--accent-soft)' : 'var(--danger-soft)', color: isCollection ? 'var(--accent-ink)' : 'var(--danger)', display: 'grid', placeItems: 'center' }}>
            {isCollection ? <IconArrowUp size={16} /> : <IconArrowDown size={16} />}
          </div>
          <div style={{ flex: 1 }}>
            <div className="modal-ttl">Yeni {isCollection ? 'Tahsilat' : 'Ödeme'}</div>
            <div className="muted" style={{ fontSize: 12 }}>Cari hesaba kayıt oluştur</div>
          </div>
          <button type="button" className="btn btn-icon btn-ghost" onClick={onClose}><IconX size={16} /></button>
        </div>
        <div className="modal-bd">
          <div className="field">
            <label>İşlem Tipi</label>
            <div className="type-pick">
              <label>
                <input type="radio" name="type" value="collection" checked={type === 'collection'} onChange={() => setType('collection')} />
                <div className="tp-icon"><IconArrowUp size={14} /></div>
                <div className="tp-body">
                  <div className="tp-ttl">Tahsilat</div>
                  <div className="tp-sub">Cariden para giriş</div>
                </div>
              </label>
              <label>
                <input type="radio" name="type" value="payment" checked={type === 'payment'} onChange={() => setType('payment')} />
                <div className="tp-icon"><IconArrowDown size={14} /></div>
                <div className="tp-body">
                  <div className="tp-ttl">Ödeme</div>
                  <div className="tp-sub">Cariye para çıkış</div>
                </div>
              </label>
            </div>
          </div>

          <div className="field">
            <label>Cari Hesap</label>
            <select value={cust} onChange={e => setCust(e.target.value)}>
              {CUSTOMERS.map(c => <option key={c.id} value={c.id}>{c.name}  ·  {c.code}</option>)}
            </select>
            {customer && (
              <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--panel-soft)', borderRadius: 7, display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                <span className="muted">Mevcut bakiye:</span>
                <BalanceChip value={customer.balance} />
                <span className="grow" />
                <span className="muted">Limit: <span className="num">{fmtTL(customer.credit)}</span></span>
              </div>
            )}
          </div>

          <div className="field-row">
            <div className="field">
              <label>Tutar (₺)</label>
              <input type="text" placeholder="0,00" value={amount} onChange={e => setAmount(e.target.value)} style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 16, fontWeight: 600, textAlign: 'right' }} autoFocus />
            </div>
            <div className="field">
              <label>Tarih</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)} />
            </div>
          </div>

          <div className="field">
            <label>Tahsilat Şekli</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
              {[
                { k: 'nakit', l: 'Nakit' },
                { k: 'havale', l: 'Havale/EFT' },
                { k: 'kredi', l: 'Kredi Kartı' },
                { k: 'cek', l: 'Çek/Senet' },
              ].map(m => (
                <button key={m.k} type="button" className={`flt ${method === m.k ? 'active' : ''}`} onClick={() => setMethod(m.k)} style={{ justifyContent: 'center', padding: '9px 6px', fontSize: 12.5 }}>
                  {m.l}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Açıklama (opsiyonel)</label>
            <textarea rows="2" value={note} onChange={e => setNote(e.target.value)} placeholder="Örn: Nisan faturası kapatıldı" />
          </div>
        </div>
        <div className="modal-ft">
          <button type="button" className="btn" onClick={onClose}>İptal</button>
          <button type="submit" className="btn btn-primary"><IconCheck size={14} /> Kaydet</button>
        </div>
      </form>
    </div>
  );
}

window.TxModal = TxModal;
