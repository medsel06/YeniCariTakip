"""Banka Hesaplari ve Hareketleri Sayfasi"""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog
from services.banka_service import (
    list_banka_hesaplari, get_tum_banka_bakiyeler, add_banka_hesap,
    update_banka_hesap, delete_banka_hesap, get_banka_hareketler,
    transfer, delete_transfer,
)

TIP_LABEL = {'BANKA': 'Banka', 'KREDI_KARTI': 'Kredi Kartı'}


@ui.page('/banka')
def banka_page():
    if not create_layout(active_path='/banka', page_title='Banka'):
        return

    state = {'secili_hesap': None}
    kartlar_container = None
    hareket_container = None

    def _refresh_kartlar():
        kartlar_container.clear()
        hesaplar = get_tum_banka_bakiyeler()
        with kartlar_container:
            if not hesaplar:
                ui.label('Henüz banka hesabı tanımlı değil. "Yeni Hesap" ile ekleyin.').classes('text-grey-7 q-pa-md')
                return
            with ui.row().classes('w-full q-gutter-md'):
                for h in hesaplar:
                    renk = 'deep-purple' if h['tip'] == 'KREDI_KARTI' else 'indigo'
                    ikon = 'credit_card' if h['tip'] == 'KREDI_KARTI' else 'account_balance'
                    with ui.card().classes('q-pa-md cursor-pointer').style('min-width: 240px') \
                            .on('click', lambda hid=h['id']: _select_hesap(hid)):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon(ikon, color=renk).style('font-size: 28px')
                                with ui.column().classes('gap-0'):
                                    ui.label(h['ad']).classes('text-weight-bold')
                                    ui.label(TIP_LABEL.get(h['tip'], h['tip'])).classes('text-caption text-grey-6')
                            if not h['aktif']:
                                ui.badge('Pasif', color='grey')
                        ui.separator().classes('q-my-xs')
                        bakiye = h['bakiye']
                        renk_bakiye = 'text-negative' if bakiye < 0 else 'text-positive'
                        ui.label(f"{fmt_para(bakiye)} TL").classes(f'text-h6 text-weight-bold {renk_bakiye}')
                        ui.label(f"↑ {fmt_para(h['giris'])}  ↓ {fmt_para(h['cikis'])}").classes('text-caption text-grey-6')
                        with ui.row().classes('w-full justify-end gap-1 q-mt-xs'):
                            ui.button(icon='edit', on_click=lambda e, hh=h: _open_edit(hh)).props('flat round dense size=sm color=primary')
                            ui.button(icon='delete', on_click=lambda e, hh=h: _delete(hh)).props('flat round dense size=sm color=negative')

    def _select_hesap(hesap_id):
        state['secili_hesap'] = hesap_id
        _refresh_hareketler()

    def _refresh_hareketler():
        hareket_container.clear()
        hid = state['secili_hesap']
        if hid is None:
            return
        hesaplar = {h['id']: h for h in list_banka_hesaplari()}
        h = hesaplar.get(hid)
        hareketler = get_banka_hareketler(hid)
        with hareket_container:
            ui.label(f"{h['ad']} — Hareketler ({len(hareketler)})").classes('text-subtitle1 text-weight-bold q-mt-md')
            if not hareketler:
                ui.label('Bu hesapta hareket yok.').classes('text-grey-7')
                return
            columns = [
                {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'left', 'sortable': True},
                {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center'},
                {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
                {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
            ]
            rows = []
            for r in hareketler:
                rows.append({
                    'tarih': (r.get('tarih') or '')[:10],
                    'tur': 'Giriş' if r.get('tur') == 'GELIR' else 'Çıkış',
                    'tutar': fmt_para(r.get('tutar', 0)),
                    'aciklama': r.get('aciklama', '') or '',
                })
            ui.table(columns=columns, rows=rows, row_key='aciklama').classes('w-full').props('flat bordered dense')

    # --- HESAP EKLE / DUZENLE ---
    def _open_add():
        _open_form(None)

    def _open_edit(h):
        _open_form(h)

    def _open_form(h):
        duzenle = h is not None
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 380px'):
            ui.label('Hesap Düzenle' if duzenle else 'Yeni Banka Hesabı').classes('text-h6')
            inp_ad = ui.input('Hesap Adı', value=h['ad'] if duzenle else '').props('outlined dense').classes('w-full')
            inp_tip = ui.select({'BANKA': 'Banka', 'KREDI_KARTI': 'Kredi Kartı'},
                                value=h['tip'] if duzenle else 'BANKA', label='Tip').props('outlined dense').classes('w-full')
            inp_iban = ui.input('IBAN', value=h.get('iban', '') if duzenle else '').props('outlined dense').classes('w-full')
            inp_acilis = ui.number('Açılış Bakiyesi', value=float(h['acilis_bakiye']) if duzenle else 0, format='%.2f').props('outlined dense').classes('w-full')
            inp_aktif = ui.switch('Aktif', value=bool(h['aktif']) if duzenle else True)
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    if not inp_ad.value or not inp_ad.value.strip():
                        notify_err('Hesap adı zorunlu')
                        return
                    try:
                        data = {
                            'ad': inp_ad.value, 'tip': inp_tip.value, 'iban': inp_iban.value or '',
                            'acilis_bakiye': inp_acilis.value or 0, 'aktif': inp_aktif.value,
                        }
                        if duzenle:
                            update_banka_hesap(h['id'], data)
                            notify_ok('Hesap güncellendi')
                        else:
                            add_banka_hesap(data)
                            notify_ok('Hesap eklendi')
                        dlg.close()
                        _refresh_kartlar()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=_save).props('unelevated')
        dlg.open()

    def _delete(h):
        def _confirmed():
            try:
                delete_banka_hesap(h['id'])
                notify_ok('Hesap silindi')
                if state['secili_hesap'] == h['id']:
                    state['secili_hesap'] = None
                    hareket_container.clear()
                _refresh_kartlar()
            except Exception as e:
                notify_err(f'{e}')
        confirm_dialog(f"{h['ad']} hesabını silmek istediğinize emin misiniz?", _confirmed)

    # --- TRANSFER ---
    def _open_transfer():
        hesaplar = list_banka_hesaplari(sadece_aktif=True)
        # Secenekler: NAKIT (None) + her banka hesabi
        opts = {'__nakit__': 'NAKİT KASA'}
        for h in hesaplar:
            opts[str(h['id'])] = h['ad']
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 400px'):
            ui.label('Hesaplar Arası Transfer').classes('text-h6')
            inp_kaynak = ui.select(opts, label='Kaynak (çıkan)', value='__nakit__').props('outlined dense').classes('w-full')
            inp_hedef = ui.select(opts, label='Hedef (giren)').props('outlined dense').classes('w-full')
            inp_tutar = ui.number('Tutar', value=0, format='%.2f').props('outlined dense').classes('w-full')
            inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
            with inp_tarih.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu:
                    ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu.close()))
                ic.on('click', menu.open)
            inp_aciklama = ui.input('Açıklama').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    def _resolve(v):
                        return None if v == '__nakit__' else int(v)
                    try:
                        k = _resolve(inp_kaynak.value)
                        hd = _resolve(inp_hedef.value)
                        transfer(k, hd, inp_tutar.value, inp_tarih.value, inp_aciklama.value or '')
                        notify_ok('Transfer kaydedildi')
                        dlg.close()
                        _refresh_kartlar()
                        _refresh_hareketler()
                    except Exception as e:
                        notify_err(f'{e}')

                ui.button('Transfer Et', color='primary', on_click=_save).props('unelevated')
        dlg.open()

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        with ui.row().classes('w-full items-center justify-between q-mb-sm'):
            ui.label('Banka Hesapları').classes('text-h6 text-weight-bold')
            with ui.row().classes('gap-2'):
                ui.button('Transfer', icon='swap_horiz', on_click=_open_transfer).props('outline color=primary')
                ui.button('Yeni Hesap', icon='add', on_click=_open_add, color='primary').props('unelevated')

        kartlar_container = ui.column().classes('w-full')
        hareket_container = ui.column().classes('w-full')

    _refresh_kartlar()
