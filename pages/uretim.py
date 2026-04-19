"""ALSE Plastik Hammadde - Uretim Kayitlari Sayfasi"""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_miktar, MIKTAR_SLOT, TARIH_SLOT, notify_ok, notify_err, confirm_dialog
from db import get_db
from services.stok_service import get_urun_list


def _load_uretim_list():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM uretim ORDER BY tarih DESC, id DESC').fetchall()
        result = []
        for r in rows:
            girdiler = [dict(g) for g in conn.execute(
                'SELECT * FROM uretim_girdi WHERE uretim_id=?', (r['id'],)
            ).fetchall()]
            ciktilar = [dict(c) for c in conn.execute(
                'SELECT * FROM uretim_cikti WHERE uretim_id=?', (r['id'],)
            ).fetchall()]
            toplam_girdi = sum(g['miktar'] for g in girdiler)
            toplam_cikti = sum(c['miktar'] for c in ciktilar)
            result.append({
                'id': r['id'], 'tarih': r['tarih'], 'aciklama': r['aciklama'],
                'girdiler': girdiler, 'ciktilar': ciktilar,
                'toplam_girdi': toplam_girdi, 'toplam_cikti': toplam_cikti,
                'fire': toplam_girdi - toplam_cikti
            })
        return result


@ui.page('/uretim')
def uretim_page():
    if not create_layout(active_path='/uretim', page_title='Üretim'):
        return

    table_ref = None

    columns = [
        {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
        {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left', 'sortable': True},
        {'name': 'toplam_girdi', 'label': 'Toplam Girdi (KG)', 'field': 'toplam_girdi', 'align': 'right',
         'sortable': True},
        {'name': 'toplam_cikti', 'label': 'Toplam Çıktı (KG)', 'field': 'toplam_cikti', 'align': 'right',
         'sortable': True},
        {'name': 'fire', 'label': 'Fire (KG)', 'field': 'fire', 'align': 'right', 'sortable': True},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center', 'sortable': False},
    ]

    def load_data():
        nonlocal table_ref
        rows = _load_uretim_list()
        if table_ref:
            table_ref.rows = rows
            table_ref.update()
        return rows

    def open_detail_dialog(row):
        with ui.dialog() as dlg, ui.card().classes('q-pa-md shadow-10').style('width: 90vw; max-width: 900px'):
            with ui.row().classes('items-center q-mb-xs'):
                ui.icon('precision_manufacturing', color='primary').classes('text-h5')
                tarih_display = row.get('tarih', '')
                if tarih_display and '-' in tarih_display:
                    parts = tarih_display.split('-')
                    tarih_display = f'{parts[2]}.{parts[1]}.{parts[0]}'
                ui.label(f'Üretim Detayı - {tarih_display}').classes('text-h6 text-weight-bold q-ml-sm')
            ui.separator()

            if row['aciklama']:
                ui.label(row['aciklama']).classes('text-body2 text-grey-7 q-mt-xs q-mb-xs')

            ui.label('Girdiler').classes('text-subtitle1 text-weight-medium q-mt-xs')
            if row['girdiler']:
                girdi_cols = [
                    {'name': 'urun_ad', 'label': 'Ürün', 'field': 'urun_ad', 'align': 'left'},
                    {'name': 'miktar', 'label': 'Miktar (KG)', 'field': 'miktar', 'align': 'right'},
                ]
                girdi_table = ui.table(columns=girdi_cols, rows=row['girdiler'], row_key='id').classes(
                    'w-full q-mb-xs')
                girdi_table.props('flat dense bordered')
                girdi_table.add_slot('body-cell-miktar', MIKTAR_SLOT)
            else:
                ui.label('Girdi yok').classes('text-grey-5 q-mb-xs')

            ui.label('Çıktılar').classes('text-subtitle1 text-weight-medium q-mt-xs')
            if row['ciktilar']:
                cikti_cols = [
                    {'name': 'urun_ad', 'label': 'Ürün', 'field': 'urun_ad', 'align': 'left'},
                    {'name': 'miktar', 'label': 'Miktar (KG)', 'field': 'miktar', 'align': 'right'},
                ]
                cikti_table = ui.table(columns=cikti_cols, rows=row['ciktilar'], row_key='id').classes(
                    'w-full q-mb-xs')
                cikti_table.props('flat dense bordered')
                cikti_table.add_slot('body-cell-miktar', MIKTAR_SLOT)
            else:
                ui.label('Çıktı yok').classes('text-grey-5 q-mb-xs')

            ui.separator().classes('q-my-xs')
            with ui.row().classes('w-full justify-between'):
                ui.label(f'Toplam Girdi: {fmt_miktar(row["toplam_girdi"])} KG').classes('text-weight-medium')
                ui.label(f'Toplam Çıktı: {fmt_miktar(row["toplam_cikti"])} KG').classes('text-weight-medium')
                ui.label(f'Fire: {fmt_miktar(row["fire"])} KG').classes('text-weight-medium text-orange-8')

            ui.separator().classes('q-my-xs')
            with ui.row().classes('w-full justify-end'):
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    def open_edit_dialog(row):
        urunler = get_urun_list()
        urun_options = {u['kod']: f"{u['kod']} - {u['ad']}" for u in urunler}
        urun_ad_map = {u['kod']: u['ad'] for u in urunler}

        girdi_rows = []
        cikti_rows = []
        girdi_container = None
        cikti_container = None

        with ui.dialog() as dlg, ui.card().classes('q-pa-lg shadow-10').style('width: 90vw; max-width: 900px'):
            with ui.column().classes('w-full'):
                with ui.row().classes('items-center q-mb-sm'):
                    ui.icon('edit', color='primary').classes('text-h5')
                    ui.label('Üretim Kaydı Düzenle').classes('text-h6 text-weight-bold q-ml-sm')
                ui.separator()

                inp_tarih = ui.input('Tarih', value=row.get('tarih', date.today().isoformat())).classes(
                    'w-full q-mt-md').props('outlined dense')
                with inp_tarih:
                    with ui.menu().props('no-parent-event') as tarih_menu:
                        with ui.date(mask='YYYY-MM-DD').bind_value(inp_tarih) as dp:
                            with ui.row().classes('justify-end'):
                                ui.button('Kapat', on_click=tarih_menu.close).props('flat')
                    with inp_tarih.add_slot('append'):
                        ui.icon('edit_calendar').on('click', tarih_menu.open).classes('cursor-pointer')

                inp_aciklama = ui.input('Açıklama', value=row.get('aciklama', '')).classes('w-full').props(
                    'outlined dense')

                # --- Girdiler ---
                ui.label('Girdiler (Hammadde)').classes('text-subtitle1 text-weight-medium q-mt-md')
                girdi_container = ui.column().classes('w-full')

                def add_girdi_row(urun_kod='', miktar=0):
                    row_data = {'urun_kod': urun_kod, 'miktar': miktar}
                    girdi_rows.append(row_data)
                    with girdi_container:
                        with ui.row().classes('w-full items-center gap-2') as row_el:
                            sel = ui.select(
                                options=urun_options, label='Ürün', with_input=True,
                                value=urun_kod if urun_kod else None
                            ).classes('flex-grow').props('outlined dense')
                            mik = ui.number('Miktar (KG)', value=miktar, min=0, step=0.01).classes(
                                'w-32').props('outlined dense')

                            def update_row(s=sel, m=mik, rd=row_data):
                                rd['urun_kod'] = s.value or ''
                                rd['miktar'] = m.value or 0

                            sel.on('update:model-value', lambda e, u=update_row: u())
                            mik.on('update:model-value', lambda e, u=update_row: u())

                            def remove_girdi(r_el=row_el, rd=row_data):
                                if rd in girdi_rows:
                                    girdi_rows.remove(rd)
                                r_el.delete()

                            ui.button(icon='close', on_click=remove_girdi).props(
                                'flat round dense color=negative size=sm')

                ui.button('Girdi Satiri Ekle', icon='add', on_click=lambda: add_girdi_row()).props(
                    'flat color=primary size=sm').classes('q-mt-xs')

                # --- Ciktilar ---
                ui.label('Çıktılar (Üretilen)').classes('text-subtitle1 text-weight-medium q-mt-md')
                cikti_container = ui.column().classes('w-full')

                def add_cikti_row(urun_kod='', miktar=0):
                    row_data = {'urun_kod': urun_kod, 'miktar': miktar}
                    cikti_rows.append(row_data)
                    with cikti_container:
                        with ui.row().classes('w-full items-center gap-2') as row_el:
                            sel = ui.select(
                                options=urun_options, label='Ürün', with_input=True,
                                value=urun_kod if urun_kod else None
                            ).classes('flex-grow').props('outlined dense')
                            mik = ui.number('Miktar (KG)', value=miktar, min=0, step=0.01).classes(
                                'w-32').props('outlined dense')

                            def update_row(s=sel, m=mik, rd=row_data):
                                rd['urun_kod'] = s.value or ''
                                rd['miktar'] = m.value or 0

                            sel.on('update:model-value', lambda e, u=update_row: u())
                            mik.on('update:model-value', lambda e, u=update_row: u())

                            def remove_cikti(r_el=row_el, rd=row_data):
                                if rd in cikti_rows:
                                    cikti_rows.remove(rd)
                                r_el.delete()

                            ui.button(icon='close', on_click=remove_cikti).props(
                                'flat round dense color=negative size=sm')

                ui.button('Cikti Satiri Ekle', icon='add', on_click=lambda: add_cikti_row()).props(
                    'flat color=primary size=sm').classes('q-mt-xs')

            ui.separator().classes('q-my-md')
            with ui.row().classes('w-full justify-end'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    valid_girdiler = [g for g in girdi_rows if g['urun_kod'] and g['miktar'] > 0]
                    valid_ciktilar = [c for c in cikti_rows if c['urun_kod'] and c['miktar'] > 0]

                    if not valid_girdiler and not valid_ciktilar:
                        notify_err('Geçerli girdi veya çıktı satırları ekleyin')
                        return

                    try:
                        with get_db() as conn:
                            conn.execute('UPDATE uretim SET tarih=?, aciklama=? WHERE id=?',
                                         (inp_tarih.value or date.today().isoformat(),
                                          inp_aciklama.value or '', row['id']))
                            # Mevcut girdi/ciktilari sil
                            conn.execute('DELETE FROM uretim_girdi WHERE uretim_id=?', (row['id'],))
                            conn.execute('DELETE FROM uretim_cikti WHERE uretim_id=?', (row['id'],))
                            # Yenilerini ekle
                            for g in valid_girdiler:
                                conn.execute(
                                    'INSERT INTO uretim_girdi (uretim_id, urun_kod, urun_ad, miktar) VALUES (?,?,?,?)',
                                    (row['id'], g['urun_kod'], urun_ad_map.get(g['urun_kod'], ''), g['miktar'])
                                )
                            for c in valid_ciktilar:
                                conn.execute(
                                    'INSERT INTO uretim_cikti (uretim_id, urun_kod, urun_ad, miktar) VALUES (?,?,?,?)',
                                    (row['id'], c['urun_kod'], urun_ad_map.get(c['urun_kod'], ''), c['miktar'])
                                )

                        notify_ok('Üretim kaydı güncellendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')

        # Mevcut girdileri doldur
        for g in row.get('girdiler', []):
            add_girdi_row(g.get('urun_kod', ''), g.get('miktar', 0))
        for c in row.get('ciktilar', []):
            add_cikti_row(c.get('urun_kod', ''), c.get('miktar', 0))
        if not row.get('girdiler'):
            add_girdi_row()
        if not row.get('ciktilar'):
            add_cikti_row()
        dlg.open()

    def open_new_dialog():
        urunler = get_urun_list()
        urun_options = {u['kod']: f"{u['kod']} - {u['ad']}" for u in urunler}

        girdi_rows = []
        cikti_rows = []
        girdi_container = None
        cikti_container = None

        with ui.dialog() as dlg, ui.card().classes('q-pa-lg shadow-10').style('width: 90vw; max-width: 900px'):
            with ui.column().classes('w-full'):
                with ui.row().classes('items-center q-mb-sm'):
                    ui.icon('add_circle', color='primary').classes('text-h5')
                    ui.label('Yeni Üretim Kaydı').classes('text-h6 text-weight-bold q-ml-sm')
                ui.separator()

                inp_tarih = ui.input('Tarih', value=date.today().isoformat()).classes('w-full q-mt-md').props(
                    'outlined dense')
                with inp_tarih:
                    with ui.menu().props('no-parent-event') as tarih_menu:
                        with ui.date(mask='YYYY-MM-DD').bind_value(inp_tarih) as dp:
                            with ui.row().classes('justify-end'):
                                ui.button('Kapat', on_click=tarih_menu.close).props('flat')
                    with inp_tarih.add_slot('append'):
                        ui.icon('edit_calendar').on('click', tarih_menu.open).classes('cursor-pointer')

                inp_aciklama = ui.input('Açıklama').classes('w-full').props('outlined dense')

                # --- Girdiler ---
                ui.label('Girdiler (Hammadde)').classes('text-subtitle1 text-weight-medium q-mt-md')
                girdi_container = ui.column().classes('w-full')

                def add_girdi_row():
                    row_data = {'urun_kod': '', 'miktar': 0}
                    girdi_rows.append(row_data)
                    with girdi_container:
                        with ui.row().classes('w-full items-center gap-2') as row_el:
                            sel = ui.select(
                                options=urun_options, label='Ürün', with_input=True
                            ).classes('flex-grow').props('outlined dense')
                            mik = ui.number('Miktar (KG)', value=0, min=0, step=0.01).classes(
                                'w-32').props('outlined dense')

                            def update_row(s=sel, m=mik, rd=row_data):
                                rd['urun_kod'] = s.value or ''
                                rd['miktar'] = m.value or 0

                            sel.on('update:model-value', lambda e, u=update_row: u())
                            mik.on('update:model-value', lambda e, u=update_row: u())

                            def remove_girdi(r_el=row_el, rd=row_data):
                                if rd in girdi_rows:
                                    girdi_rows.remove(rd)
                                r_el.delete()

                            ui.button(icon='close', on_click=remove_girdi).props(
                                'flat round dense color=negative size=sm')

                ui.button('Girdi Satiri Ekle', icon='add', on_click=add_girdi_row).props(
                    'flat color=primary size=sm').classes('q-mt-xs')

                # --- Ciktilar ---
                ui.label('Çıktılar (Üretilen)').classes('text-subtitle1 text-weight-medium q-mt-md')
                cikti_container = ui.column().classes('w-full')

                def add_cikti_row():
                    row_data = {'urun_kod': '', 'miktar': 0}
                    cikti_rows.append(row_data)
                    with cikti_container:
                        with ui.row().classes('w-full items-center gap-2') as row_el:
                            sel = ui.select(
                                options=urun_options, label='Ürün', with_input=True
                            ).classes('flex-grow').props('outlined dense')
                            mik = ui.number('Miktar (KG)', value=0, min=0, step=0.01).classes(
                                'w-32').props('outlined dense')

                            def update_row(s=sel, m=mik, rd=row_data):
                                rd['urun_kod'] = s.value or ''
                                rd['miktar'] = m.value or 0

                            sel.on('update:model-value', lambda e, u=update_row: u())
                            mik.on('update:model-value', lambda e, u=update_row: u())

                            def remove_cikti(r_el=row_el, rd=row_data):
                                if rd in cikti_rows:
                                    cikti_rows.remove(rd)
                                r_el.delete()

                            ui.button(icon='close', on_click=remove_cikti).props(
                                'flat round dense color=negative size=sm')

                ui.button('Cikti Satiri Ekle', icon='add', on_click=add_cikti_row).props(
                    'flat color=primary size=sm').classes('q-mt-xs')

            ui.separator().classes('q-my-md')
            with ui.row().classes('w-full justify-end'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not girdi_rows and not cikti_rows:
                        notify_err('En az bir girdi veya çıktı ekleyin')
                        return

                    valid_girdiler = [g for g in girdi_rows if g['urun_kod'] and g['miktar'] > 0]
                    valid_ciktilar = [c for c in cikti_rows if c['urun_kod'] and c['miktar'] > 0]

                    if not valid_girdiler and not valid_ciktilar:
                        notify_err('Geçerli girdi veya çıktı satırları ekleyin')
                        return

                    # Build urun_ad lookup
                    urun_ad_map = {u['kod']: u['ad'] for u in urunler}

                    try:
                        with get_db() as conn:
                            cur = conn.execute(
                                'INSERT INTO uretim (tarih, aciklama) VALUES (?,?) RETURNING id',
                                (inp_tarih.value or date.today().isoformat(),
                                 inp_aciklama.value or '')
                            )
                            uretim_id = cur.fetchone()['id']

                            for g in valid_girdiler:
                                conn.execute(
                                    'INSERT INTO uretim_girdi (uretim_id, urun_kod, urun_ad, miktar) VALUES (?,?,?,?)',
                                    (uretim_id, g['urun_kod'], urun_ad_map.get(g['urun_kod'], ''), g['miktar'])
                                )
                            for c in valid_ciktilar:
                                conn.execute(
                                    'INSERT INTO uretim_cikti (uretim_id, urun_kod, urun_ad, miktar) VALUES (?,?,?,?)',
                                    (uretim_id, c['urun_kod'], urun_ad_map.get(c['urun_kod'], ''), c['miktar'])
                                )

                        notify_ok('Üretim kaydı eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')

        # Add initial rows
        add_girdi_row()
        add_cikti_row()
        dlg.open()

    def do_delete(uretim_id):
        def confirmed():
            try:
                with get_db() as conn:
                    conn.execute('DELETE FROM uretim_girdi WHERE uretim_id=?', (uretim_id,))
                    conn.execute('DELETE FROM uretim_cikti WHERE uretim_id=?', (uretim_id,))
                    conn.execute('DELETE FROM uretim WHERE id=?', (uretim_id,))
                notify_ok('Üretim kaydı silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu üretim kaydını silmek istediğinize emin misiniz?', confirmed)

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        with ui.row().classes('w-full items-center justify-end q-mb-xs'):
            ui.button('Yeni Üretim', icon='add', color='primary', on_click=open_new_dialog)

        rows = _load_uretim_list()
        table_ref = ui.table(
            columns=columns, rows=rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full')
        table_ref.props('flat bordered dense')

        # Slot - tarih ve miktar NaN fix
        table_ref.add_slot('body-cell-tarih', TARIH_SLOT)
        table_ref.add_slot('body-cell-toplam_girdi', MIKTAR_SLOT)
        table_ref.add_slot('body-cell-toplam_cikti', MIKTAR_SLOT)

        # Fire renklendirme
        table_ref.add_slot('body-cell-fire', r"""
            <q-td :props="props">
                <span :style="props.value > 0 ? 'color: orange; font-weight: bold' : ''">
                    {{ props.value != null && props.value !== 0 ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}
                </span>
            </q-td>
        """)

        # Actions slot - edit + detay + delete
        table_ref.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="visibility" color="primary" size="sm"
                    @click.stop="$parent.$emit('detail', props.row)">
                    <q-tooltip>Detay</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="edit" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        table_ref.on('detail', lambda e: open_detail_dialog(e.args))
        table_ref.on('edit', lambda e: open_edit_dialog(e.args))
        table_ref.on('delete', lambda e: do_delete(e.args['id']))

        # Satir tiklama - detay dialog
        table_ref.on('rowClick', lambda e: open_detail_dialog(e.args[1]))



