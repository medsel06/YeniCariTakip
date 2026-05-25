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

    def _refresh():
        _kartlar()
        _hareket()

    def _kartlar():
        kartlar_box.clear()
        hesaplar = [h for h in get_tum_banka_bakiyeler() if h['tip'] == state['tip']]
        with kartlar_box:
            if not hesaplar:
                ui.label(f"Tanımlı {TIP_LABEL[state['tip']].lower()} yok. \"Yeni\" ile ekleyin.").classes('text-grey-6 q-pa-sm')
                return
            with ui.row().classes('w-full q-gutter-sm'):
                for h in hesaplar:
                    bakiye = h['bakiye']
                    is_kart = h['tip'] == 'KREDI_KARTI'
                    # Kart icin bakiye negatif = borc. Renk ona gore.
                    renk = 'text-negative' if bakiye < 0 else 'text-positive'
                    sel = state['secili'] == h['id']
                    card = ui.card().classes('q-pa-sm cursor-pointer').style(
                        f"min-width: 190px; max-width: 230px; border:1px solid {'#1976d2' if sel else '#e0e0e0'};"
                        f"border-radius:10px; {'background:#e3f2fd;' if sel else ''}")
                    with card.on('click', lambda hid=h['id']: _sec(hid)):
                        with ui.row().classes('items-center justify-between w-full no-wrap'):
                            ui.label(h['ad']).classes('text-weight-bold text-body2').style('overflow:hidden;text-overflow:ellipsis')
                            ui.icon('credit_card' if is_kart else 'account_balance',
                                    color='deep-purple' if is_kart else 'indigo').style('font-size:18px')
                        ui.label(f"{fmt_para(bakiye)} TL").classes(f'text-subtitle1 text-weight-bold {renk}')
                        if is_kart and h.get('kart_limiti'):
                            kullanilabilir = float(h['kart_limiti']) + bakiye  # bakiye negatif
                            ui.label(f"Limit: {fmt_para(h['kart_limiti'])} | Kullanılabilir: {fmt_para(kullanilabilir)}").classes('text-caption text-grey-6')
                        with ui.row().classes('w-full justify-end gap-0'):
                            ui.button(icon='edit', on_click=lambda e, hh=h: _form(hh)).props('flat round dense size=sm color=primary')
                            ui.button(icon='delete', on_click=lambda e, hh=h: _sil(hh)).props('flat round dense size=sm color=negative')

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
                {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
            ]
            rows = [{'tarih': (r.get('tarih') or '')[:10],
                     'tur': 'Giriş' if r.get('tur') == 'GELIR' else 'Çıkış',
                     'tutar': fmt_para(r.get('tutar', 0)),
                     'aciklama': r.get('aciklama', '') or ''} for r in hareketler]
            ui.table(columns=cols, rows=rows, row_key='aciklama',
                     pagination={'rowsPerPage': 20}).classes('w-full').props('flat bordered dense')

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
        _refresh()

    # --- PAGE ---
    with ui.column().classes('w-full q-pa-sm gap-1'):
        with ui.row().classes('w-full items-center justify-between'):
            with ui.row().classes('gap-1'):
                ui.button('Banka Hesapları', icon='account_balance',
                          on_click=lambda: _tab_degis('BANKA')).props('flat no-caps').bind_visibility_from(state, 'tip', lambda t: True)
                ui.button('Kredi Kartları', icon='credit_card',
                          on_click=lambda: _tab_degis('KREDI_KARTI')).props('flat no-caps')
            with ui.row().classes('gap-2'):
                ui.button('Transfer', icon='swap_horiz', on_click=_transfer).props('outline color=primary dense')
                ui.button('Yeni', icon='add', on_click=lambda: _form(), color='primary').props('unelevated dense')
        kartlar_box = ui.column().classes('w-full')
        hareket_box = ui.column().classes('w-full')
    _refresh()
