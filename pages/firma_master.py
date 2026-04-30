"""Firma master veri yönetimi."""
from nicegui import ui

from layout import create_layout, notify_ok, notify_err, confirm_dialog, PARA_SLOT, normalize_search
from services.cari_service import (
    get_firma_master_list, add_firma, update_firma, delete_firma, generate_firma_kod
)


@ui.page('/firma-master')
def firma_master_page():
    if not create_layout(active_path='/firma-master', page_title='Firma Master'):
        return
    all_rows = get_firma_master_list()

    def _filter_rows(query):
        q = normalize_search(query)
        if not q:
            return all_rows
        return [
            r for r in all_rows
            if q in normalize_search(r.get('kod', ''))
            or q in normalize_search(r.get('ad', ''))
            or q in normalize_search(r.get('vkn_tckn', ''))
            or q in normalize_search(r.get('email', ''))
        ]

    def _refresh():
        nonlocal all_rows
        all_rows = get_firma_master_list()
        table.rows = _filter_rows(search.value)
        table.update()
        lbl_toplam.set_text(f'Toplam Firma: {len(all_rows)}')

    def _open_detail(row):
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:560px'):
            ui.label(f"Firma Detayı - {row.get('ad', '')}").classes('text-h6')
            ui.separator().classes('q-my-sm')
            pairs = [
                ('Kod', row.get('kod', '-')),
                ('Firma', row.get('ad', '-')),
                ('VKN / TCKN', row.get('vkn_tckn', '-')),
                ('Telefon', row.get('tel', '-')),
                ('E-posta', row.get('email', '-')),
                ('Adres', row.get('adres', '-')),
                ('NACE', row.get('nace', '-')),
                ('İş Alanı', row.get('is_alani', '-')),
                ('Risk Limiti', f"{(row.get('risk_limiti') or 0):,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')),
            ]
            for label, value in pairs:
                with ui.row().classes('w-full items-center q-py-xs'):
                    ui.label(label).classes('text-grey-7').style('width:140px')
                    ui.label(str(value or '-')).classes('text-weight-medium')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    def _open_add():
        auto_kod = generate_firma_kod()
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:520px'):
            ui.label('Yeni Firma').classes('text-h6')
            ui.input('Kod', value=auto_kod).props('outlined dense readonly').classes('w-full')
            inp_ad = ui.input('Firma Adı').props('outlined dense').classes('w-full')
            inp_vkn = ui.input('VKN / TCKN').props('outlined dense').classes('w-full')
            inp_vergi = ui.input('Vergi Dairesi').props('outlined dense').classes('w-full')
            inp_tel = ui.input('Telefon').props('outlined dense').classes('w-full')
            inp_mail = ui.input('E-posta').props('outlined dense').classes('w-full')
            inp_adres = ui.input('Adres').props('outlined dense').classes('w-full')
            inp_nace = ui.input('NACE').props('outlined dense').classes('w-full')
            inp_is = ui.input('İş Alanı').props('outlined dense').classes('w-full')
            inp_risk = ui.number('Risk Limiti', value=0, format='%.2f').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('İptal', on_click=dlg.close).props('flat')

                def _save():
                    if not (inp_ad.value or '').strip():
                        notify_err('Firma adı zorunlu')
                        return
                    try:
                        is_alani = (inp_is.value or '').strip()
                        if inp_vergi.value:
                            is_alani = (is_alani + f" | VD: {inp_vergi.value.strip()}").strip()
                        add_firma({
                            'kod': auto_kod,
                            'ad': inp_ad.value.strip(),
                            'vkn_tckn': inp_vkn.value or '',
                            'tel': inp_tel.value or '',
                            'adres': inp_adres.value or '',
                            'email': inp_mail.value or '',
                            'nace': inp_nace.value or '',
                            'is_alani': is_alani,
                            'risk_limiti': float(inp_risk.value or 0),
                        })
                        notify_ok('Firma eklendi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=_save)
        dlg.open()

    def _open_edit(row):
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:520px'):
            ui.label(f"Firma Düzenle - {row.get('kod', '')}").classes('text-h6')
            inp_ad = ui.input('Firma Adı', value=row.get('ad', '')).props('outlined dense').classes('w-full')
            inp_vkn = ui.input('VKN / TCKN', value=row.get('vkn_tckn', '')).props('outlined dense').classes('w-full')
            inp_tel = ui.input('Telefon', value=row.get('tel', '')).props('outlined dense').classes('w-full')
            inp_mail = ui.input('E-posta', value=row.get('email', '')).props('outlined dense').classes('w-full')
            inp_adres = ui.input('Adres', value=row.get('adres', '')).props('outlined dense').classes('w-full')
            inp_nace = ui.input('NACE', value=row.get('nace', '')).props('outlined dense').classes('w-full')
            inp_is = ui.input('İş Alanı', value=row.get('is_alani', '')).props('outlined dense').classes('w-full')
            inp_risk = ui.number('Risk Limiti', value=row.get('risk_limiti', 0) or 0, format='%.2f').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('İptal', on_click=dlg.close).props('flat')

                def _save():
                    if not (inp_ad.value or '').strip():
                        notify_err('Firma adı zorunlu')
                        return
                    try:
                        update_firma(row['kod'], {
                            'ad': inp_ad.value.strip(),
                            'vkn_tckn': inp_vkn.value or '',
                            'tel': inp_tel.value or '',
                            'adres': inp_adres.value or '',
                            'email': inp_mail.value or '',
                            'nace': inp_nace.value or '',
                            'is_alani': inp_is.value or '',
                            'risk_limiti': float(inp_risk.value or 0),
                        })
                        notify_ok('Firma güncellendi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=_save)
        dlg.open()

    def _delete(row):
        confirm_dialog(
            f"{row.get('ad', '')} kaydını silmek istediğinize emin misiniz?",
            lambda: (delete_firma(row['kod']), notify_ok('Firma silindi'), _refresh()),
        )

    with ui.column().classes('w-full q-pa-xs gap-1'):
        with ui.row().classes('w-full items-center gap-2 no-wrap q-px-xs'):
            search = ui.input(
                placeholder='Ara (kod, ad, vkn, e-posta)...',
                on_change=lambda e: (setattr(table, 'rows', _filter_rows(e.value)), table.update()),
            ).props('outlined dense clearable').classes('w-64')
            lbl_toplam = ui.label(f'Toplam Firma: {len(all_rows)}').classes('text-caption text-grey-7')
            ui.space()
            ui.button('Yeni Firma', icon='add', color='primary', on_click=_open_add).props('dense')

        columns = [
            {'name': 'ad', 'label': 'Firma', 'field': 'ad', 'align': 'left', 'sortable': True},
            {'name': 'vkn_tckn', 'label': 'VKN/TCKN', 'field': 'vkn_tckn', 'align': 'left', 'sortable': True},
            {'name': 'tel', 'label': 'Telefon', 'field': 'tel', 'align': 'left', 'sortable': True},
            {'name': 'email', 'label': 'E-posta', 'field': 'email', 'align': 'left', 'sortable': True},
            {'name': 'risk_limiti', 'label': 'Risk Limiti', 'field': 'risk_limiti', 'align': 'right', 'sortable': True},
            {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center'},
        ]
        table = ui.table(
            columns=columns,
            rows=all_rows,
            row_key='kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'ad', 'descending': False},
        ).classes('w-full').style('--table-extra-rows: 3;')
        table.props('flat bordered dense')
        table.add_slot('body-cell-risk_limiti', PARA_SLOT)
        table.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="visibility" color="grey-8" size="sm"
                    @click.stop="$parent.$emit('detail', props.row)" />
                <q-btn flat round dense icon="edit" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)" />
                <q-btn flat round dense icon="delete" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')
        table.on('detail', lambda e: _open_detail(e.args))
        table.on('edit', lambda e: _open_edit(e.args))
        table.on('delete', lambda e: _delete(e.args))
        table.on('rowClick', lambda e: _open_detail(e.args[1]))
