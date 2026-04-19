"""ALSE Plastik Hammadde - Stok Detay Sayfası"""
from nicegui import ui
from layout import create_layout, fmt_miktar, MIKTAR_SLOT, PARA_SLOT, TARIH_SLOT, normalize_search
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

    hareketler = get_urun_hareketleri(urun_kod)
    uretim_hareketleri = get_urun_uretim_hareketleri(urun_kod)

    def _filter(rows, q, fields):
        q = normalize_search(q)
        if not q:
            return rows
        return [r for r in rows if any(q in normalize_search(r.get(f, '')) for f in fields)]

    hareket_rows = [{**r, '_rid': f"h{i}"} for i, r in enumerate(hareketler)]
    uretim_rows = [{**r, '_rid': f"u{i}"} for i, r in enumerate(uretim_hareketleri)]

    def _pdf_stok_hareket():
        _open_pdf(
            generate_table_pdf(
                f"Stok Hareketleri - {urun['ad']}",
                ['Tarih', 'Tür', 'Firma', 'Miktar', 'Birim Fiyat', 'Toplam'],
                [[r.get('tarih', ''), r.get('tur', ''), r.get('firma_ad', ''),
                  r.get('miktar', 0), r.get('birim_fiyat', 0), r.get('toplam', 0)] for r in hareketler],
            ),
            f"stok_hareket_{urun_kod}.pdf",
        )

    with ui.column().classes('w-full q-pa-sm gap-2'):
        with ui.card().classes('w-full q-pa-sm'):
            with ui.row().classes('w-full items-center no-wrap gap-2'):
                with ui.row().classes('items-center no-wrap gap-1'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/stok')).props('flat round dense')
                    search = ui.input(placeholder='Ara (firma, tür, tip)...').props('outlined dense clearable').classes('w-72')

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
                        h_table = ui.table(
                            columns=hareket_cols, rows=hareket_rows, row_key='_rid',
                            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
                        ).classes('w-full')
                        h_table.props('flat bordered dense')
                        h_table.add_slot('body-cell-tarih', TARIH_SLOT)
                        h_table.add_slot('body-cell-miktar', MIKTAR_SLOT)
                        h_table.add_slot('body-cell-birim_fiyat', PARA_SLOT)
                        h_table.add_slot('body-cell-toplam', PARA_SLOT)
                        h_table.add_slot('body-cell-tur', r'''
                            <q-td :props="props">
                                <q-chip dense size="sm" text-color="white"
                                    :color="props.value === 'ALIS' ? 'blue' : 'green'">
                                    {{ props.value === 'ALIS' ? 'Alış' : 'Satış' }}
                                </q-chip>
                            </q-td>
                        ''')
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
