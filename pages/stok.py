"""Cari Takip - Stok Sayfasi"""
from nicegui import ui
from layout import create_layout, fmt_miktar, MIKTAR_SLOT, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, confirm_dialog, normalize_search
from services.stok_service import get_stok_list, get_urun_list, add_urun, update_urun, delete_urun, generate_urun_kod, get_kategori_list
from services.settings_service import get_company_settings
from services.pdf_service import generate_stok_raporu_pdf, save_pdf_preview


@ui.page('/stok')
def stok_page():
    if not create_layout(active_path='/stok', page_title='Stok'):
        return

    table_ref = None
    search_val = {'text': ''}

    columns = [
        {'name': 'ad', 'label': 'Ürün Adı', 'field': 'ad', 'align': 'left', 'sortable': True},
        {'name': 'kategori', 'label': 'Kategori', 'field': 'kategori', 'align': 'left', 'sortable': True},
        {'name': 'alis', 'label': 'Alış (KG)', 'field': 'alis', 'align': 'right', 'sortable': True},
        {'name': 'satis', 'label': 'Satış (KG)', 'field': 'satis', 'align': 'right', 'sortable': True},
        {'name': 'uretim_girdi', 'label': 'Üretim Girdi', 'field': 'uretim_girdi', 'align': 'right',
         'sortable': True},
        {'name': 'uretim_cikti', 'label': 'Üretim Çıktı', 'field': 'uretim_cikti', 'align': 'right',
         'sortable': True},
        {'name': 'stok', 'label': 'Net Stok', 'field': 'stok', 'align': 'right', 'sortable': True},
        {'name': 'birim', 'label': 'Birim', 'field': 'birim', 'align': 'center', 'sortable': True},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center', 'sortable': False},
    ]

    def load_data():
        nonlocal table_ref, all_rows
        all_rows = get_stok_list()
        if table_ref:
            table_ref.rows = all_rows
            table_ref.update()

    def open_add_dialog():
        auto_kod = generate_urun_kod()
        kategoriler = get_kategori_list()

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('add_circle')
                ui.label('Yeni Ürün Ekle').classes('dialog-title')

            inp_kod = ui.input('Ürün Kodu', value=auto_kod).classes('w-full q-mt-sm').props('outlined dense readonly')
            inp_ad = ui.input('Ürün Adı').classes('w-full').props('outlined dense')
            inp_kat = ui.select(
                options=kategoriler, label='Kategori', with_input=True,
                new_value_mode='add-unique'
            ).classes('w-full').props('outlined dense')
            inp_birim = ui.select(
                options=['KG', 'ADET', 'METRE', 'LITRE', 'PAKET', 'M3'],
                value='KG', label='Birim'
            ).classes('w-full').props('outlined dense')

            # DESİ alani (sadece uretim takibi aciksa)
            _ayar = get_company_settings()
            inp_desi = None
            if _ayar.get('uretim_takibi'):
                with ui.card().classes('w-full q-pa-sm').style('background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('straighten', color='orange-8').style('font-size: 18px')
                        ui.label('Üretim / DESİ Bilgisi').classes('text-caption text-weight-bold text-orange-9')
                    inp_desi = ui.number('DESİ Değeri (birim başına hammadde)', value=0, format='%.2f').classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_ad.value:
                        notify_err('Urun adi zorunlu')
                        return
                    try:
                        kat_val = inp_kat.value
                        if isinstance(kat_val, str):
                            kat_val = kat_val.strip()
                        else:
                            kat_val = ''
                        add_urun({
                            'kod': inp_kod.value.strip(),
                            'ad': inp_ad.value.strip(),
                            'kategori': kat_val,
                            'birim': inp_birim.value or 'KG',
                            'desi_degeri': float(inp_desi.value or 0) if inp_desi else 0,
                        })
                        notify_ok('Ürün eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_edit_dialog(row):
        try:
            kategoriler = get_kategori_list()
        except Exception:
            kategoriler = []

        # Mevcut desi degerini DB'den al
        from db import get_db as _get_db
        _current_desi = 0
        try:
            with _get_db() as _conn:
                _urow = _conn.execute('SELECT desi_degeri FROM urunler WHERE kod=?', (row['kod'],)).fetchone()
                if _urow:
                    _current_desi = float(_urow['desi_degeri'] or 0)
        except Exception:
            pass

        # None / nonstandart degerleri normalize et — Quasar select degeri options
        # disinda olunca bazen render sirasinda dialog acilmiyor (ABS GRANÜL(K) bug).
        _kat_val = (row.get('kategori') or '').strip()
        if _kat_val and _kat_val not in kategoriler:
            kategoriler = list(kategoriler) + [_kat_val]
        _birim_options = ['KG', 'ADET', 'METRE', 'LITRE', 'PAKET', 'M3']
        _birim_val = (row.get('birim') or 'KG').strip().upper() or 'KG'
        if _birim_val not in _birim_options:
            _birim_options = _birim_options + [_birim_val]

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('edit')
                ui.label('Ürün Düzenle').classes('dialog-title')

            ui.label(f'Kod: {row["kod"]}').classes('text-subtitle2 text-grey-7 q-mt-md')
            inp_ad = ui.input('Ürün Adı', value=row.get('ad', '') or '').classes('w-full q-mt-sm').props('outlined dense')
            inp_kat = ui.select(
                options=kategoriler, label='Kategori', with_input=True,
                new_value_mode='add-unique', value=_kat_val
            ).classes('w-full').props('outlined dense')
            inp_birim = ui.select(
                options=_birim_options,
                value=_birim_val, label='Birim',
                with_input=True, new_value_mode='add-unique',
            ).classes('w-full').props('outlined dense')

            # DESİ alani (sadece uretim takibi aciksa)
            _ayar = get_company_settings()
            inp_desi = None
            if _ayar.get('uretim_takibi'):
                with ui.card().classes('w-full q-pa-sm q-mt-sm').style('background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('straighten', color='orange-8').style('font-size: 18px')
                        ui.label('Üretim / DESİ Bilgisi').classes('text-caption text-weight-bold text-orange-9')
                    inp_desi = ui.number('DESİ Değeri (birim başına hammadde)', value=_current_desi, format='%.2f').classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_ad.value:
                        notify_err('Ürün adı zorunlu')
                        return
                    try:
                        kat_val = inp_kat.value
                        if isinstance(kat_val, str):
                            kat_val = kat_val.strip()
                        else:
                            kat_val = ''
                        update_urun(row['kod'], {
                            'ad': inp_ad.value.strip(),
                            'kategori': kat_val,
                            'birim': inp_birim.value or 'KG',
                            'desi_degeri': float(inp_desi.value or 0) if inp_desi else _current_desi,
                        })
                        notify_ok('Ürün güncellendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_stok_list()

        def do_filter(query):
            if not query:
                return all_rows
            q = normalize_search(query)
            return [r for r in all_rows if q in normalize_search(r.get('kod', '')) or q in normalize_search(r.get('ad', ''))
                    or q in normalize_search(r.get('kategori', ''))]

        def _open_pdf(pdf_bytes, filename: str):
            preview_url = save_pdf_preview(pdf_bytes, filename)
            ui.run_javascript(f"window.open('{preview_url}', '_blank')")

        def _pdf_stok_listesi():
            try:
                _open_pdf(generate_stok_raporu_pdf(all_rows), 'stok_listesi.pdf')
            except Exception as e:
                notify_err(f'PDF hatası: {e}')

        with ui.row().classes('w-full items-center gap-2 q-mb-xs'):
            search_input = ui.input(
                placeholder='Ara (kod, ad, kategori)...',
                on_change=lambda e: (setattr(table_ref, 'rows', do_filter(e.value)), table_ref.update()),
            ).props('outlined dense clearable').classes('w-64')
            ui.space()
            ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_stok_listesi).props('dense')
            ui.button('Yeni Ürün', icon='add', color='primary', on_click=open_add_dialog)

        table_ref = ui.table(
            columns=columns, rows=all_rows, row_key='kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'kod'}
        ).classes('w-full').style('--table-extra-rows: 3;')
        table_ref.props('flat bordered dense')

        # Slot for negative stock coloring
        table_ref.add_slot('body-cell-stok', r'''
            <q-td :props="props">
                <span :style="props.value < 0 ? 'color: red; font-weight: bold' : ''">
                    {{ props.value != null ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '0,00' }}
                </span>
            </q-td>
        ''')

        # Miktar slotlari - NaN fix
        table_ref.add_slot('body-cell-alis', MIKTAR_SLOT)
        table_ref.add_slot('body-cell-satis', MIKTAR_SLOT)
        table_ref.add_slot('body-cell-uretim_girdi', MIKTAR_SLOT)
        table_ref.add_slot('body-cell-uretim_cikti', MIKTAR_SLOT)

        table_ref.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn v-if="(!props.row.alis || props.row.alis === 0) && (!props.row.satis || props.row.satis === 0) && (!props.row.uretim_girdi || props.row.uretim_girdi === 0) && (!props.row.uretim_cikti || props.row.uretim_cikti === 0)"
                    flat round dense icon="delete_outline" color="negative" size="sm"
                    @click.stop="$parent.$emit('remove', props.row)">
                    <q-tooltip>Sil (boş stok)</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        def do_delete(row):
            def confirmed():
                try:
                    delete_urun(row['kod'])
                    notify_ok(f'Ürün silindi: {row.get("ad", "")}')
                    load_data()
                except Exception as e:
                    notify_err(f'Hata: {e}')
            confirm_dialog(
                f"'{row.get('ad', '')}' ürününü silmek istediğinize emin misiniz?",
                confirmed
            )

        def _safe_open_edit(e):
            try:
                open_edit_dialog(e.args)
            except Exception as ex:
                import traceback
                traceback.print_exc()
                notify_err(f'Düzenleme açılamadı: {ex}')

        table_ref.on('edit', _safe_open_edit)
        table_ref.on('remove', lambda e: do_delete(e.args))

        # Satir tiklama - stok detay sayfasina git
        table_ref.on('rowClick', lambda e: ui.navigate.to(f'/stok/{e.args[1]["kod"]}'))





