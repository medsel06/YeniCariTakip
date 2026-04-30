"""ALSE Plastik Hammadde - Stok Detay Sayfası"""
from nicegui import ui
from layout import create_layout, fmt_miktar, MIKTAR_SLOT, PARA_SLOT, TARIH_SLOT, normalize_search, donem_secici
from services.stok_service import get_urun_stok, get_urun_hareketleri, get_urun_uretim_hareketleri
from services.pdf_service import generate_table_pdf, save_pdf_preview


@ui.page('/stok/{urun_kod}')
def stok_detay_page(urun_kod: str):
    def _open_pdf(pdf_bytes, filename: str):
        preview_url = save_pdf_preview(pdf_bytes, filename)
        ui.run_javascript(f"window.open('{preview_url}', '_blank')")

    urun = get_urun_stok(urun_kod)
    if not urun:
        if not create_layout(active_path='/stok', page_title='Stok Detay'):
            return
        with ui.column().classes('w-full q-pa-sm'):
            ui.label('Ürün bulunamadı').classes('text-h6 text-negative')
            ui.button('Geri Dön', icon='arrow_back', on_click=lambda: ui.navigate.to('/stok')).props('flat')
        return

    if not create_layout(active_path='/stok', page_title=urun['ad']):
        return

    all_hareketler = get_urun_hareketleri(urun_kod)
    uretim_hareketleri = get_urun_uretim_hareketleri(urun_kod)
    state = {'yil': None}
    h_table_ref = [None]

    def _get_filtered_hareketler():
        if state['yil']:
            return [r for r in all_hareketler if r.get('tarih', '')[:4] == str(state['yil'])]
        return all_hareketler

    def _filter(rows, q, fields):
        q = normalize_search(q)
        if not q:
            return rows
        return [r for r in rows if any(q in normalize_search(r.get(f, '')) for f in fields)]

    def _make_rows(rows):
        return [{**r, '_rid': f"h{i}"} for i, r in enumerate(rows)]

    hareket_rows = _make_rows(all_hareketler)
    uretim_rows = [{**r, '_rid': f"u{i}"} for i, r in enumerate(uretim_hareketleri)]

    def _on_yil_change(yil, ay):
        state['yil'] = yil
        filtered = _get_filtered_hareketler()
        nonlocal hareket_rows
        hareket_rows = _make_rows(filtered)
        if h_table_ref[0]:
            h_table_ref[0].rows = hareket_rows
            h_table_ref[0].update()

    def _pdf_stok_hareket():
        filtered = _get_filtered_hareketler()
        yil_label = f" ({state['yil']})" if state['yil'] else ""
        _open_pdf(
            generate_table_pdf(
                f"Stok Hareketleri - {urun['ad']}{yil_label}",
                ['Tarih', 'Tür', 'Firma', 'Miktar', 'Birim Fiyat', 'Toplam'],
                [[r.get('tarih', ''), r.get('tur', ''), r.get('firma_ad', ''),
                  r.get('miktar', 0), r.get('birim_fiyat', 0), r.get('toplam', 0)] for r in filtered],
            ),
            f"stok_hareket_{urun_kod}.pdf",
        )

    ui.add_css('''
    .stk-alis { background: #eff6ff !important; }
    .stk-satis { background: #f0fdf4 !important; }
    tr:hover .stk-alis { background: #dbeafe !important; }
    tr:hover .stk-satis { background: #dcfce7 !important; }
    ''')

    with ui.column().classes('w-full q-pa-sm gap-2'):
        with ui.card().classes('w-full q-pa-sm'):
            with ui.row().classes('w-full items-center no-wrap gap-2'):
                with ui.row().classes('items-center no-wrap gap-1'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/stok')).props('flat round dense')
                    search = ui.input(placeholder='Ara (firma, tür, tip)...').props('outlined dense clearable').classes('w-72')
                    donem_secici(_on_yil_change, include_all=True)

                with ui.row().classes('items-center justify-center no-wrap gap-1').style('flex:1; min-width:0;'):
                    with ui.element('q-chip').props('icon="badge" dense outline color="grey-7"'):
                        ui.label(f"Kod: {urun['kod']}")
                    if urun.get('kategori'):
                        with ui.element('q-chip').props('icon="category" dense outline color="grey-7"'):
                            ui.label(f"Kategori: {urun['kategori']}")
                    with ui.element('q-chip').props('icon="inventory_2" dense color="primary" text-color="white"'):
                        ui.label(f"Net: {fmt_miktar(urun.get('stok', 0))} {urun.get('birim','KG')}")

                ui.button(
                    'PDF', icon='picture_as_pdf', color='primary',
                    on_click=_pdf_stok_hareket
                ).props('dense')

        # Sekmeli yapi: Stok Hareketleri | Uretim Hareketleri
        with ui.card().classes('w-full q-pa-none'):
            with ui.tabs().classes('w-full').props('dense no-caps') as tabs:
                stok_tab = ui.tab('Stok Hareketleri', icon='swap_horiz')
                uretim_tab = ui.tab('Üretim Hareketleri', icon='precision_manufacturing')

            with ui.tab_panels(tabs, value=stok_tab).classes('w-full').props('animated'):
                with ui.tab_panel(stok_tab).classes('q-pa-sm'):
                    if hareketler:
                        hareket_cols = [
                            {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                            {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
                            {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
                            {'name': 'miktar', 'label': 'Miktar', 'field': 'miktar', 'align': 'right', 'sortable': True},
                            {'name': 'birim_fiyat', 'label': 'Birim Fiyat', 'field': 'birim_fiyat', 'align': 'right', 'sortable': True},
                            {'name': 'toplam', 'label': 'Toplam', 'field': 'toplam', 'align': 'right', 'sortable': True},
                        ]
                        _rc = "props.row.tur==='ALIS'?'stk-alis':'stk-satis'"
                        h_table = ui.table(
                            columns=hareket_cols, rows=hareket_rows, row_key='_rid',
                            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
                        ).classes('w-full')
                        h_table.props('flat bordered dense')
                        h_table_ref[0] = h_table
                        h_table.add_slot('body-cell-tarih', r'''
                            <q-td :props="props" :class="%s">
                                {{ props.value ? props.value.split('-').reverse().join('.') : '' }}
                            </q-td>
                        ''' % _rc)
                        h_table.add_slot('body-cell-miktar', r'''
                            <q-td :props="props" :class="%s">
                                {{ props.value != null && props.value !== 0 ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}
                            </q-td>
                        ''' % _rc)
                        h_table.add_slot('body-cell-birim_fiyat', r'''
                            <q-td :props="props" :class="%s">
                                {{ props.value != null && props.value !== 0
                                    ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                                    : '' }}
                            </q-td>
                        ''' % _rc)
                        h_table.add_slot('body-cell-toplam', r'''
                            <q-td :props="props" :class="%s">
                                {{ props.value != null && props.value !== 0
                                    ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                                    : '' }}
                            </q-td>
                        ''' % _rc)
                        h_table.add_slot('body-cell-firma_ad', r'''
                            <q-td :props="props" :class="%s">{{ props.value }}</q-td>
                        ''' % _rc)
                        h_table.add_slot('body-cell-tur', r'''
                            <q-td :props="props" :class="%s">
                                <span style="font-weight:600;"
                                    :style="props.value === 'ALIS' ? 'color:#1d4ed8;' : 'color:#15803d;'">
                                    {{ props.value === 'ALIS' ? 'Alış' : 'Satış' }}
                                </span>
                            </q-td>
                        ''' % _rc)
                        search.on('update:model-value', lambda e: (setattr(h_table, 'rows', _filter(hareket_rows, e.args, ['firma_ad', 'tur'])), h_table.update()))
                    else:
                        ui.label('Hareket bulunamadı').classes('text-grey-5 q-pa-md')

                with ui.tab_panel(uretim_tab).classes('q-pa-sm'):
                    if uretim_hareketleri:
                        uretim_cols = [
                            {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                            {'name': 'tip', 'label': 'Tip', 'field': 'tip', 'align': 'center', 'sortable': True},
                            {'name': 'miktar', 'label': 'Miktar', 'field': 'miktar', 'align': 'right', 'sortable': True},
                        ]
                        u_table = ui.table(
                            columns=uretim_cols, rows=uretim_rows, row_key='_rid',
                            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
                        ).classes('w-full')
                        u_table.props('flat bordered dense')
                        u_table.add_slot('body-cell-tarih', TARIH_SLOT)
                        u_table.add_slot('body-cell-miktar', MIKTAR_SLOT)
                        u_table.add_slot('body-cell-tip', r'''
                            <q-td :props="props">
                                <q-chip dense size="sm" text-color="white"
                                    :color="props.value === 'GIRDI' ? 'orange' : 'teal'">
                                    {{ props.value }}
                                </q-chip>
                            </q-td>
                        ''')
                        search.on('update:model-value', lambda e: (setattr(u_table, 'rows', _filter(uretim_rows, e.args, ['tip'])), u_table.update()))
                    else:
                        ui.label('Üretim hareketi bulunamadı').classes('text-grey-5 q-pa-md')
