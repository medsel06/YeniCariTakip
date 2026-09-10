"""Banka Hesapları + Kredi Kartları Sayfası"""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog, IM_MODAL_CSS, f2_kisayolu
from services.banka_service import (
    list_banka_hesaplari, get_tum_banka_bakiyeler, add_banka_hesap,
    update_banka_hesap, delete_banka_hesap, get_banka_hareketler,
    transfer, get_banka_hesap,
)

TIP_LABEL = {'BANKA': 'Banka', 'KREDI_KARTI': 'Kredi Kartı'}


@ui.page('/banka')
def banka_page():
    if not create_layout(active_path='/banka', page_title='Banka'):
        return

    ui.add_css('''
        .bnk-wrap{border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;background:#fff;}
        .bnk-menu2{flex:0 0 236px;min-width:0;border-right:1px solid #e2e8f0;background:#faf8ff;display:flex;flex-direction:column;}
        .bnk-detay2{flex:1;min-width:0;}
        .bnk-seg{display:flex;gap:2px;background:#eef2f6;border-radius:9px;padding:3px;margin:8px 8px 0;flex:0 0 auto;}
        .bnk-tab{flex:1;border-radius:7px;font-size:12px !important;color:#64748b;min-height:30px;}
        .bnk-tab-act{background:#fff !important;color:#0f172a !important;box-shadow:0 1px 3px rgba(0,0,0,.12);}
        .bnk-ozet{padding:9px 12px;border-bottom:1px solid #ece9f6;flex:0 0 auto;}
        .bnk-foot{padding:8px;border-top:1px solid #ece9f6;flex:0 0 auto;gap:6px;align-items:center;margin-top:auto;}
        .bnk-list{overflow-y:auto;flex:0 0 auto;max-height:348px;padding:6px;}
        .bnk-list::-webkit-scrollbar{width:6px;}
        .bnk-list::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:6px;}
        .bnk-list::-webkit-scrollbar-track{background:transparent;}
        .bnk-item{padding:8px 10px;border-radius:10px;gap:9px;margin-bottom:2px;transition:background .12s;}
        .bnk-item:hover{background:#f0ebff;}
        .bnk-item-sec{background:#f0ebff;box-shadow:inset 3px 0 0 #7c3aed;}
        .bnk-ad{font-size:13px;font-weight:600;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;}
        /* Sabit tablo (DUZ HTML): dis div SABIT yukseklik + ic scroll; sutunlar table-layout:fixed. */
        .bnk-scroll{height:clamp(400px, calc(100vh - 236px), 760px);overflow-y:auto;border:1px solid #e5e7eb;border-radius:10px;background:#fff;}
        .bnk-scroll::-webkit-scrollbar{width:8px;}
        .bnk-scroll::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:8px;}
        .bnk-scroll::-webkit-scrollbar-track{background:transparent;}
        .bnk-htbl{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12.5px;}
        .bnk-htbl thead th{position:sticky;top:0;z-index:2;background:#1e293b;color:#fff;padding:9px 12px;font-size:11px;font-weight:700;letter-spacing:.2px;}
        .bnk-htbl td{padding:8px 12px;border-bottom:1px solid #e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#334155;}
        .bnk-htbl td:first-child{font-variant-numeric:tabular-nums;}  /* tarih: rakam genisligi sabit, 08 vs 09 farki yok */
        .bnk-htbl tbody tr:nth-child(even){background:#f1f5f9;}
        .bnk-htbl tbody tr:hover{background:#eef2ff;}
        .bnk-htbl .c-empty{text-align:center;color:#94a3b8;padding:44px 12px;}
    ''')

    state = {'tip': 'BANKA', 'secili': None}
    kartlar_box = None
    hareket_box = None
    ozet_box = None
    btn_banka = None
    btn_kredi = None

    def _refresh():
        _ozet()
        _kartlar()
        _hareket()

    def _ozet():
        """Ust toolbar'da tek parca ozet panel (sekmeye gore toplamlar)."""
        if ozet_box is None:
            return
        ozet_box.clear()
        hesaplar = [h for h in get_tum_banka_bakiyeler() if h['tip'] == state['tip']]
        with ozet_box:
            if not hesaplar:
                return
            if state['tip'] == 'KREDI_KARTI':
                borc = sum(-float(h['bakiye']) for h in hesaplar if float(h['bakiye']) < 0)
                ui.label('TOPLAM KART BORCU').style('font-size:9px;color:#94a3b8;font-weight:800;letter-spacing:.4px')
                ui.label(f"{fmt_para(borc)} ₺").style('font-size:16px;font-weight:800;color:#b91c1c')
            else:
                toplam = sum(float(h['bakiye']) for h in hesaplar)
                ui.label('TOPLAM BAKİYE').style('font-size:9px;color:#94a3b8;font-weight:800;letter-spacing:.4px')
                ui.label(f"{fmt_para(toplam)} ₺").style(
                    f"font-size:16px;font-weight:800;color:{'#059669' if toplam >= 0 else '#b91c1c'}")

    def _kartlar():
        kartlar_box.clear()
        hesaplar = [h for h in get_tum_banka_bakiyeler() if h['tip'] == state['tip']]
        is_kart_tip = state['tip'] == 'KREDI_KARTI'
        with kartlar_box:
            # Sol menu: banka/kart listesi. Secili yoksa (veya tip degistiyse) ilkini otomatik sec.
            if hesaplar and not any(h['id'] == state['secili'] for h in hesaplar):
                state['secili'] = hesaplar[0]['id']
            elif not hesaplar:
                state['secili'] = None
            if not hesaplar:
                with ui.column().classes('w-full items-center justify-center text-grey-6').style('min-height:220px;gap:6px'):
                    ui.icon('credit_card' if is_kart_tip else 'account_balance').style('font-size:30px;opacity:.35')
                    ui.label(f'Tanımlı {TIP_LABEL[state["tip"]].lower()} yok').style('font-size:12.5px')
                    ui.label('"YENİ" ile ekleyin').style('font-size:11px;opacity:.7')
                return
            for h in hesaplar:
                sec = (h['id'] == state['secili'])
                bakiye = float(h['bakiye'] or 0)
                brenk = '#dc2626' if bakiye < 0 else '#059669'
                with ui.row().classes('w-full items-center no-wrap cursor-pointer bnk-item' + (' bnk-item-sec' if sec else '')) \
                        .on('click', lambda hid=h['id']: _sec(hid)):
                    ui.icon('credit_card' if is_kart_tip else 'account_balance').style(
                        f"font-size:19px;color:{'#7c3aed' if sec else '#94a3b8'}")
                    with ui.column().classes('gap-0').style('flex:1;min-width:0'):
                        ui.label(h['ad']).classes('bnk-ad')
                        ui.label(f"{fmt_para(bakiye)} ₺").style(f'font-size:11.5px;font-weight:700;color:{brenk}')

    def _sec(hid):
        state['secili'] = hid
        _refresh()

    def _hareket():
        hareket_box.clear()
        hid = state['secili']
        with hareket_box:
            h = get_banka_hesap(hid) if hid else None
            if not h or h['tip'] != state['tip']:
                with ui.column().classes('w-full items-center justify-center text-grey-5').style('min-height:320px;gap:8px'):
                    ui.icon('touch_app').style('font-size:34px;opacity:.3')
                    ui.label('Soldan bir hesap seçin').style('font-size:13px')
                return
            hareketler = get_banka_hareketler(hid)
            bakiye = next((float(x['bakiye']) for x in get_tum_banka_bakiyeler() if x['id'] == hid), 0.0)
            is_kart = h['tip'] == 'KREDI_KARTI'
            # Baslik: ad + IBAN + bakiye + duzenle/sil
            with ui.row().classes('w-full items-center justify-between no-wrap q-mb-xs'):
                with ui.row().classes('items-center no-wrap gap-2'):
                    ui.icon('credit_card' if is_kart else 'account_balance').style('font-size:22px;color:#7c3aed')
                    with ui.column().classes('gap-0'):
                        ui.label(h['ad']).style('font-size:16px;font-weight:800;color:#0f172a;line-height:1.15')
                        _alt = (f"{h['iban']}  ·  " if h.get('iban') else '')
                        if is_kart and h.get('kart_limiti'):
                            _alt += f"Kullanılabilir {fmt_para(float(h['kart_limiti']) + bakiye)} ₺  ·  "
                        _alt += f"{len(hareketler)} hareket"
                        ui.label(_alt).style('font-size:11px;color:#94a3b8;line-height:1.2')
                with ui.row().classes('items-center no-wrap gap-3'):
                    with ui.column().classes('gap-0 items-end'):
                        ui.label('Bakiye').style('font-size:9px;color:#94a3b8;font-weight:700;letter-spacing:.4px')
                        ui.label(f"{fmt_para(bakiye)} ₺").style(f"font-size:18px;font-weight:800;color:{'#dc2626' if bakiye < 0 else '#059669'}")
                    ui.button(icon='edit', on_click=lambda: _form(get_banka_hesap(hid))).props('flat round dense color=grey-7').tooltip('Düzenle')
                    ui.button(icon='delete', on_click=lambda: _sil(get_banka_hesap(hid))).props('flat round dense color=grey-6').tooltip('Sil')
            acilis = float(h.get('acilis_bakiye', 0) or 0)
            _bk = acilis
            for r in reversed(hareketler):
                _t2 = float(r.get('tutar', 0) or 0)
                _bk += _t2 if r.get('tur') == 'GELIR' else -_t2
                r['_yuruyen'] = _bk
            import html as _h
            _tr = ''
            for r in hareketler:
                giris = r.get('tur') == 'GELIR'
                tur_bg, tur_fg = ('#dcfce7', '#15803d') if giris else ('#fee2e2', '#b91c1c')
                amt_fg = '#059669' if giris else '#dc2626'
                tarih = '.'.join(reversed((r.get('tarih') or '')[:10].split('-'))) if r.get('tarih') else ''
                _tr += (
                    '<tr>'
                    f'<td style="text-align:left;">{_h.escape(tarih)}</td>'
                    f'<td style="text-align:center;"><span style="background:{tur_bg};color:{tur_fg};'
                    'display:inline-block;padding:1px 8px;border-radius:999px;font-size:10.5px;font-weight:700;">'
                    f'{"Giriş" if giris else "Çıkış"}</span></td>'
                    f'<td style="text-align:right;color:{amt_fg};font-weight:700;">{_h.escape(fmt_para(r.get("tutar", 0)))} ₺</td>'
                    f'<td style="text-align:right;">{_h.escape(fmt_para(r.get("_yuruyen", 0)))} ₺</td>'
                    f'<td style="text-align:left;">{_h.escape(r.get("aciklama", "") or "")}</td>'
                    '</tr>'
                )
            if not _tr:
                _tr = '<tr><td colspan="5" class="c-empty">Bu hesapta henüz hareket yok.</td></tr>'
            ui.html(
                '<div class="bnk-scroll w-full"><table class="bnk-htbl"><thead><tr>'
                '<th style="width:108px;text-align:left;">Tarih</th>'
                '<th style="width:84px;text-align:center;">G/Ç</th>'
                '<th style="width:135px;text-align:right;">Tutar</th>'
                '<th style="width:135px;text-align:right;">Bakiye</th>'
                '<th style="text-align:left;">Açıklama</th>'
                f'</tr></thead><tbody>{_tr}</tbody></table></div>'
            )

    def _form(h=None):
        duzenle = h is not None
        is_kart = state['tip'] == 'KREDI_KARTI'
        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 520px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('credit_card' if is_kart else 'account_balance').classes('im-ic')
                ui.label(('Kart' if is_kart else 'Hesap') + (' Düzenle' if duzenle else ' Ekle')).classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Ad + IBAN/Kart No
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('AD').classes('im-flabel')
                        inp_ad = ui.input(value=h['ad'] if duzenle else '').props('outlined dense').classes('w-full bk-ad')
                    with ui.element('div').classes('im-field col'):
                        ui.label('IBAN' if not is_kart else 'KART NO (SON 4)').classes('im-flabel')
                        inp_iban = ui.input(value=h.get('iban', '') if duzenle else '').props('outlined dense').classes('w-full bk-iban')
                # Satir 2: Acilis Bakiyesi + (kart ise) Limit + Aktif
                with ui.row().classes('w-full gap-sm no-wrap items-end'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('AÇILIŞ BAKİYESİ').classes('im-flabel')
                        inp_acilis = ui.number(value=float(h['acilis_bakiye']) if duzenle else 0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full bk-acilis')
                    inp_limit = None
                    if is_kart:
                        with ui.element('div').classes('im-field col'):
                            ui.label('KART LİMİTİ').classes('im-flabel')
                            inp_limit = ui.number(value=float(h.get('kart_limiti', 0)) if duzenle else 0, format='%.2f').props(
                                'outlined dense input-class=text-right').classes('w-full bk-limit')
                    inp_aktif = ui.switch('Aktif', value=bool(h['aktif']) if duzenle else True).props('dense')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def _save():
                    if not inp_ad.value or not inp_ad.value.strip():
                        notify_err('Ad zorunlu'); return
                    data = {'ad': inp_ad.value, 'tip': state['tip'], 'iban': inp_iban.value or '',
                            'acilis_bakiye': inp_acilis.value or 0, 'aktif': inp_aktif.value,
                            'kart_limiti': (inp_limit.value or 0) if inp_limit else 0}
                    try:
                        if duzenle:
                            update_banka_hesap(h['id'], data); notify_ok('Güncellendi')
                        else:
                            add_banka_hesap(data); notify_ok('Eklendi')
                        dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                btn_kaydet = ui.button('Kaydet', on_click=_save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')
        dlg.open()
        # Acilinca odak Ad'a
        ui.timer(0.2, lambda: inp_ad.run_method('focus'), once=True)
        # Enter zinciri (CLIENT-SIDE): ad -> iban -> acilis -> (limit) -> Kaydet
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__bkFlow) return;
            modal.__bkFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const sira = ['.bk-ad', '.bk-iban', '.bk-acilis', '.bk-limit'];
            sira.forEach((cls, i) => {
                const el = modal.querySelector(cls + ' input');
                if(!el) return;
                el.addEventListener('keydown', (e) => {
                    if(e.key !== 'Enter') return;
                    e.preventDefault();
                    for(let j = i + 1; j < sira.length; j++){
                        const n = modal.querySelector(sira[j] + ' input');
                        if(n){ n.focus(); if(n.select) n.select(); return; }
                    }
                    if(kaydet) kaydet.focus();
                });
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

    def _sil(h):
        def _ok():
            try:
                delete_banka_hesap(h['id']); notify_ok('Silindi')
                if state['secili'] == h['id']:
                    state['secili'] = None
                _refresh()
            except Exception as e:
                notify_err(f'{e}')
        confirm_dialog(f"{h['ad']} silinsin mi?", _ok)

    def _transfer():
        opts = {'__nakit__': 'NAKİT KASA'}
        for hh in list_banka_hesaplari(sadece_aktif=True):
            opts[str(hh['id'])] = hh['ad']
        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 520px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('swap_horiz').classes('im-ic')
                ui.label('Hesaplar Arası Transfer').classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Kaynak + Hedef
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('KAYNAK (ÇIKAN)').classes('im-flabel')
                        ik = ui.select(opts, value='__nakit__').props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('HEDEF (GİREN)').classes('im-flabel')
                        ih = ui.select(opts).props('outlined dense').classes('w-full')
                # Satir 2: Tutar + Tarih
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TUTAR').classes('im-flabel')
                        it = ui.number(value=0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full tr-tutar')
                    with ui.element('div').classes('im-field col'):
                        ui.label('TARİH').classes('im-flabel')
                        itar = ui.input(value=date.today().isoformat()).props(
                            'outlined dense type=date').classes('w-full tr-tarih')
                # Aciklama
                with ui.element('div').classes('im-field w-full'):
                    ui.label('AÇIKLAMA').classes('im-flabel')
                    ia = ui.input().props('outlined dense').classes('w-full tr-aciklama')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def _save():
                    try:
                        k = None if ik.value == '__nakit__' else int(ik.value)
                        hd = None if ih.value == '__nakit__' else int(ih.value)
                        transfer(k, hd, it.value, itar.value, ia.value or '')
                        notify_ok('Transfer kaydedildi'); dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'{e}')

                btn_kaydet = ui.button('Transfer Et', on_click=_save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

                # Enter akisi (sunucu): Kaynak listesi -> Hedef listesi -> Tutar
                _tnav = {'kaynak': False, 'hedef': False}

                def _tac(sel, flag):
                    _tnav[flag] = True
                    sel.run_method('focus')
                    sel.run_method('showPopup')

                def _ik_hide():
                    if _tnav['kaynak']:
                        _tnav['kaynak'] = False
                        _tac(ih, 'hedef')
                ik.on('popup-hide', _ik_hide)

                def _ih_hide():
                    if _tnav['hedef']:
                        _tnav['hedef'] = False
                        ui.run_javascript(
                            "const el=[...document.querySelectorAll('.im-modal .tr-tutar input')].pop();"
                            "if(el){el.focus();el.select();}")
                ih.on('popup-hide', _ih_hide)
        dlg.open()
        # Acilinca Kaynak listesi acilir (Enter secer -> Hedef -> Tutar ...)
        ui.timer(0.25, lambda: _tac(ik, 'kaynak'), once=True)
        # Klavye akisi (CLIENT-SIDE): tutar -> tarih -> aciklama -> Transfer Et
        ui.timer(0.35, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__trFlow) return;
            modal.__trFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const sira = ['.tr-tutar', '.tr-tarih', '.tr-aciklama'];
            sira.forEach((cls, i) => {
                const el = modal.querySelector(cls + ' input');
                if(!el) return;
                el.addEventListener('keydown', (e) => {
                    if(e.key !== 'Enter') return;
                    e.preventDefault();
                    const nxt = sira[i + 1];
                    if(nxt){ const n = modal.querySelector(nxt + ' input'); if(n) n.focus(); }
                    else if(kaydet){ kaydet.focus(); }
                });
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

    def _tab_degis(tip):
        state['tip'] = tip
        state['secili'] = None
        if btn_banka and btn_kredi:
            if tip == 'BANKA':
                btn_banka.classes('bnk-tab-act'); btn_kredi.classes(remove='bnk-tab-act')
            else:
                btn_banka.classes(remove='bnk-tab-act'); btn_kredi.classes('bnk-tab-act')
        _refresh()

    # --- PAGE ---
    with ui.column().classes('w-full').style('padding:6px 14px 4px;gap:0;'):
        # Iki panel bitisik (tek cizgi ayrac, tam yukseklik). Toolbar yok — her sey panellerde.
        with ui.row().classes('w-full items-stretch no-wrap bnk-wrap'):
            # SOL: ikonsuz segment sekmeler + toplam ozet + liste + Yeni/Transfer footer
            with ui.column().classes('bnk-menu2'):
                with ui.row().classes('bnk-seg'):
                    btn_banka = ui.button('Bankalar', on_click=lambda: _tab_degis('BANKA')) \
                        .props('flat no-caps dense').classes('bnk-tab bnk-tab-act')
                    btn_kredi = ui.button('Kartlar', on_click=lambda: _tab_degis('KREDI_KARTI')) \
                        .props('flat no-caps dense').classes('bnk-tab')
                ozet_box = ui.column().classes('bnk-ozet w-full gap-0')
                kartlar_box = ui.column().classes('bnk-list w-full gap-0')
                with ui.row().classes('bnk-foot w-full no-wrap'):
                    with ui.element('div').style('position:relative;flex:1;display:flex'):
                        ui.button('Yeni', icon='add', on_click=lambda: _form(), color=None) \
                            .props('unelevated dense no-caps') \
                            .style('flex:1;height:34px;font-size:12px;background:#0f172a;color:#fff;border-radius:9px')
                        ui.label('F2').classes('fkey-hint')
                    ui.button(icon='swap_horiz', on_click=_transfer).props('flat dense round color=grey-7') \
                        .tooltip('Hesaplar arası transfer')
            # SAG: secili hesap detayi
            with ui.column().classes('bnk-detay2'):
                hareket_box = ui.column().classes('w-full').style('padding:12px 16px;')
    ui.add_css(IM_MODAL_CSS)
    f2_kisayolu(lambda: _form())
    _refresh()
