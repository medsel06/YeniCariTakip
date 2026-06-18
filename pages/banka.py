"""Banka Hesapları + Kredi Kartları Sayfası"""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog
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
        if not hesaplar:
            return
        if state['tip'] == 'KREDI_KARTI':
            borc = sum(-float(h['bakiye']) for h in hesaplar if float(h['bakiye']) < 0)
            limit = sum(float(h.get('kart_limiti', 0) or 0) for h in hesaplar)
            segs = [('Kart Borcu', borc, '#b91c1c'), ('Limit', limit, '#4338ca'),
                    ('Kullanılabilir', limit - borc, '#15803d')]
        else:
            toplam = sum(float(h['bakiye']) for h in hesaplar)
            segs = [('Toplam Bakiye', toplam, '#15803d' if toplam >= 0 else '#b91c1c')]
        with ozet_box:
            with ui.row().classes('items-center no-wrap').style(
                'border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;background:#fff;height:34px'
            ):
                for i, (lbl, val, fg) in enumerate(segs):
                    sep = 'border-right:1px solid #eef2f6;' if i < len(segs) - 1 else ''
                    with ui.row().classes('items-center no-wrap').style(f'padding:0 12px;gap:6px;height:100%;{sep}'):
                        ui.label(lbl).style('font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.4px')
                        ui.label(f"{fmt_para(val)} ₺").style(f'font-size:13px;font-weight:800;color:{fg}')

    def _kartlar():
        kartlar_box.clear()
        hesaplar = [h for h in get_tum_banka_bakiyeler() if h['tip'] == state['tip']]
        is_kart_tip = state['tip'] == 'KREDI_KARTI'
        with kartlar_box:
            if not hesaplar:
                ui.label(f"Tanımlı {TIP_LABEL[state['tip']].lower()} yok. \"Yeni\" ile ekleyin.").classes('text-grey-6 q-pa-sm')
                return
            # Tablo gorunumu (Islemler referans: zebra + tablo, cerceve degil)
            cols = [
                {'name': 'ad', 'label': 'Hesap', 'field': 'ad', 'align': 'left', 'sortable': True},
                {'name': 'bakiye', 'label': 'Bakiye', 'field': 'bakiye', 'align': 'right', 'sortable': True},
                {'name': 'actions', 'label': 'İşlem', 'field': 'actions', 'align': 'right'},
            ]
            if is_kart_tip:
                cols.insert(1, {'name': 'limit', 'label': 'Limit / Kullanılabilir', 'field': 'limit', 'align': 'right'})
            rows = []
            for h in hesaplar:
                bakiye = h['bakiye']
                row = {'id': h['id'], 'ad': h['ad'], 'bakiye': float(bakiye or 0)}
                if is_kart_tip:
                    if h.get('kart_limiti'):
                        kullanilabilir = float(h['kart_limiti']) + bakiye
                        row['limit'] = f"Limit {fmt_para(h['kart_limiti'])} · Kull. {fmt_para(kullanilabilir)}"
                    else:
                        row['limit'] = ''
                rows.append(row)
            htbl = ui.table(columns=cols, rows=rows, row_key='id',
                            pagination={'rowsPerPage': 0}).classes('w-full').props('flat dense')
            htbl.add_slot('body-cell-bakiye', r'''
                <q-td :props="props" class="text-right">
                    <span :class="(Number(props.value)||0) < 0 ? 'text-negative text-weight-bold' : 'text-positive text-weight-bold'">
                        {{ ((Number(props.value)||0)<0?'-':'') + Math.abs(Number(props.value)||0).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}) }} TL
                    </span>
                </q-td>''')
            htbl.add_slot('body-cell-actions', r'''
                <q-td :props="props" class="text-right">
                    <q-btn flat round dense size="sm" color="primary" icon="edit" @click.stop="$parent.$emit('duzenle', props.row)" />
                    <q-btn flat round dense size="sm" color="negative" icon="delete" @click.stop="$parent.$emit('sil', props.row)" />
                </q-td>''')
            htbl.on('rowClick', lambda e: _sec(e.args[1]['id']))
            htbl.on('duzenle', lambda e: _form(get_banka_hesap(e.args['id'])))
            htbl.on('sil', lambda e: _sil(get_banka_hesap(e.args['id'])))

    def _sec(hid):
        state['secili'] = hid
        _refresh()

    def _hareket():
        hareket_box.clear()
        hid = state['secili']
        if hid is None:
            return
        h = get_banka_hesap(hid)
        if not h or h['tip'] != state['tip']:
            return
        hareketler = get_banka_hareketler(hid)
        with hareket_box:
            ui.label(f"{h['ad']} — Hareketler ({len(hareketler)})").classes('text-subtitle2 text-weight-bold q-mt-sm')
            if not hareketler:
                ui.label('Hareket yok.').classes('text-grey-6'); return
            cols = [
                {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'left', 'sortable': True},
                {'name': 'tur', 'label': 'G/Ç', 'field': 'tur', 'align': 'center'},
                {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
                {'name': 'bakiye', 'label': 'Bakiye', 'field': 'bakiye', 'align': 'right'},
                {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
            ]
            # Yuruyen (birikmis) bakiye: acilistan baslayip eskiden yeniye birikir.
            # hareketler yeni->eski sirali; ters cevirip hesapla, sirayi koru.
            acilis = float(h.get('acilis_bakiye', 0) or 0)
            _bk = acilis
            for r in reversed(hareketler):
                tutar = float(r.get('tutar', 0) or 0)
                _bk += tutar if r.get('tur') == 'GELIR' else -tutar
                r['_yuruyen'] = _bk
            rows = [{'tarih': (r.get('tarih') or '')[:10],
                     'tur': 'Giriş' if r.get('tur') == 'GELIR' else 'Çıkış',
                     'tutar': fmt_para(r.get('tutar', 0)),
                     'bakiye': fmt_para(r.get('_yuruyen', 0)),
                     'aciklama': r.get('aciklama', '') or ''} for r in hareketler]
            ui.table(columns=cols, rows=rows, row_key='aciklama',
                     pagination={'rowsPerPage': 20}).classes('w-full').props('flat dense')

    def _form(h=None):
        duzenle = h is not None
        is_kart = state['tip'] == 'KREDI_KARTI'
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 380px'):
            ui.label(('Kart' if is_kart else 'Hesap') + (' Düzenle' if duzenle else ' Ekle')).classes('text-h6')
            inp_ad = ui.input('Ad', value=h['ad'] if duzenle else '').props('outlined dense').classes('w-full')
            inp_iban = ui.input('IBAN' if not is_kart else 'Kart No (son 4)', value=h.get('iban', '') if duzenle else '').props('outlined dense').classes('w-full')
            inp_acilis = ui.number('Açılış Bakiyesi', value=float(h['acilis_bakiye']) if duzenle else 0, format='%.2f').props('outlined dense').classes('w-full')
            inp_limit = None
            if is_kart:
                inp_limit = ui.number('Kart Limiti', value=float(h.get('kart_limiti', 0)) if duzenle else 0, format='%.2f').props('outlined dense').classes('w-full')
            inp_aktif = ui.switch('Aktif', value=bool(h['aktif']) if duzenle else True)
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

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
                ui.button('Kaydet', color='primary', on_click=_save).props('unelevated')
        dlg.open()

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
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 400px'):
            ui.label('Hesaplar Arası Transfer').classes('text-h6')
            ik = ui.select(opts, label='Kaynak (çıkan)', value='__nakit__').props('outlined dense').classes('w-full')
            ih = ui.select(opts, label='Hedef (giren)').props('outlined dense').classes('w-full')
            it = ui.number('Tutar', value=0, format='%.2f').props('outlined dense').classes('w-full')
            itar = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
            with itar.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as m:
                    ui.date(on_change=lambda e: (itar.set_value(e.value), m.close()))
                ic.on('click', m.open)
            ia = ui.input('Açıklama').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    try:
                        k = None if ik.value == '__nakit__' else int(ik.value)
                        hd = None if ih.value == '__nakit__' else int(ih.value)
                        transfer(k, hd, it.value, itar.value, ia.value or '')
                        notify_ok('Transfer kaydedildi'); dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'{e}')
                ui.button('Transfer Et', color='primary', on_click=_save).props('unelevated')
        dlg.open()

    def _tab_degis(tip):
        state['tip'] = tip
        state['secili'] = None
        
        # Sekme butonlarının stillerini dinamik olarak güncelle
        if btn_banka and btn_kredi:
            if tip == 'BANKA':
                btn_banka.classes('bg-white text-slate-900 shadow-sm', remove='text-slate-500 hover:text-slate-900')
                btn_kredi.classes('text-slate-500 hover:text-slate-900', remove='bg-white text-slate-900 shadow-sm')
            else:
                btn_banka.classes('text-slate-500 hover:text-slate-900', remove='bg-white text-slate-900 shadow-sm')
                btn_kredi.classes('bg-white text-slate-900 shadow-sm', remove='text-slate-500 hover:text-slate-900')
                
        _refresh()

    # --- PAGE ---
    with ui.column().classes('w-full q-pa-md gap-4'):
        # Üst Arayüz Satırı (Sekmeler ve İşlem Butonları)
        with ui.row().classes('w-full items-center justify-between border-b border-slate-100 pb-4'):
            
            # 1. SOL TARAF: Modern Tab Görünümü (Segmented Control)
            with ui.row().classes('bg-slate-100 p-1 rounded-lg gap-1 items-center'):
                # Banka Hesapları Sekmesi
                btn_banka = ui.button('Banka Hesapları', icon='account_balance',
                           on_click=lambda: _tab_degis('BANKA')).props('flat no-caps dense')
                btn_banka.classes('px-4 py-1.5 text-sm font-medium rounded-md transition-all')
                
                # Kredi Kartları Sekmesi
                btn_kredi = ui.button('Kredi Kartları', icon='credit_card',
                           on_click=lambda: _tab_degis('KREDI_KARTI')).props('flat no-caps dense')
                btn_kredi.classes('px-4 py-1.5 text-sm font-medium rounded-md transition-all')

                # Başlangıç durumu (BANKA aktif)
                btn_banka.classes('bg-white text-slate-900 shadow-sm')
                btn_kredi.classes('text-slate-500 hover:text-slate-900')

            # 2. SAĞ TARAF: Dengeli İşlem Butonları
            with ui.row().classes('items-center gap-3'):
                ozet_box = ui.row().classes('items-center no-wrap')
                
                # Transfer Butonu (İkincil - İnce Çerçeveli)
                ui.button('Transfer', icon='swap_horiz', on_click=_transfer) \
                    .props('unelevated no-caps') \
                    .classes('h-10 px-4 border border-slate-300 text-slate-700 hover:bg-slate-50 font-medium rounded-lg transition-all')
                
                # Yeni Butonu (Birincil - Koyu Slate)
                ui.button('Yeni', icon='account_balance', on_click=lambda: _form()) \
                    .props('unelevated') \
                    .classes('h-10 px-4 bg-slate-900 text-white hover:bg-slate-800 font-medium rounded-lg shadow-sm transition-all')
                    
        kartlar_box = ui.column().classes('w-full')
        hareket_box = ui.column().classes('w-full')
    _refresh()
