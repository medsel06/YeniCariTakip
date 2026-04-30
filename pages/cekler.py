"""ALSE Plastik Hammadde - Cekler Sayfası"""
from datetime import datetime, date
from nicegui import ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, confirm_dialog, normalize_search
from services.cek_service import (
    list_cekler, add_cek, change_durum, delete_cek, update_cek, get_cek_by_id, get_cek_hareketleri,
    get_valid_transitions, DURUM_LABELS, DURUM_COLORS
)
from services.cari_service import get_firma_list
from services.pdf_service import generate_cek_raporu_pdf, save_pdf_preview


@ui.page('/cekler')
def cekler_page():
    if not create_layout(active_path='/cekler', page_title='Çekler'):
        return

    def _open_pdf(pdf_bytes, filename: str):
        preview_url = save_pdf_preview(pdf_bytes, filename)
        ui.run_javascript(f"window.open('{preview_url}', '_blank')")

    alinan_table = None
    verilen_table = None
    today_str = datetime.now().strftime('%Y-%m-%d')

    _base_cols = [
        {'name': 'evrak_tipi', 'label': 'Tip', 'field': 'evrak_tipi', 'align': 'center', 'sortable': True},
        {'name': 'cek_no', 'label': 'Evrak No', 'field': 'cek_no', 'align': 'left', 'sortable': True},
    ]
    _end_cols = [
        {'name': 'kesim_tarih', 'label': 'Kesim Tarihi', 'field': 'kesim_tarih', 'align': 'center', 'sortable': True},
        {'name': 'vade_tarih', 'label': 'Vade Tarihi', 'field': 'vade_tarih', 'align': 'center', 'sortable': True},
        {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
        {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center', 'sortable': True},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center', 'sortable': False},
    ]
    alinan_columns = _base_cols + [
        {'name': 'firma_ad', 'label': 'Alındığı Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
        {'name': 'ciro_firma_ad', 'label': 'Ciro Edildiği Firma', 'field': 'ciro_firma_ad', 'align': 'left', 'sortable': True},
    ] + _end_cols
    verilen_columns = _base_cols + [
        {'name': 'firma_ad', 'label': 'Verildiği Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
    ] + _end_cols

    def load_data():
        if alinan_table:
            alinan_table.rows = list_cekler('ALINAN')
            alinan_table.update()
        if verilen_table:
            verilen_table.rows = list_cekler('VERILEN')
            verilen_table.update()

    def _filter(rows, query):
        q = normalize_search(query)
        if not q:
            return rows
        return [
            r for r in rows
            if q in normalize_search(r.get('cek_no', ''))
            or q in normalize_search(r.get('firma_ad', ''))
            or q in normalize_search(r.get('ciro_firma_ad', ''))
            or q in normalize_search(r.get('durum', ''))
        ]

    def open_add_dialog(cek_turu='ALINAN'):
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            turu_label = 'Alınan' if cek_turu == 'ALINAN' else 'Verilen'
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('add_circle')
                ui.label(f'Yeni {turu_label} Çek/Senet').classes('dialog-title')

            inp_evrak_tipi = ui.radio(
                options={'CEK': 'Çek', 'SENET': 'Senet'},
                value='CEK',
            ).props('inline').classes('q-mt-sm')

            inp_cek_no = ui.input('Evrak No').classes('w-full').props('outlined dense')

            inp_firma = ui.select(
                options=firma_options, label='Firma', with_input=True
            ).classes('w-full').props('outlined dense')

            inp_kesim = ui.input('Kesim Tarihi', value=date.today().isoformat()).classes('w-full').props('outlined dense')
            with inp_kesim.add_slot('append'):
                icon_k = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_k:
                    ui.date(on_change=lambda e: (inp_kesim.set_value(e.value), menu_k.close()))
                icon_k.on('click', menu_k.open)

            inp_vade = ui.input('Vade Tarihi', value=date.today().isoformat()).classes('w-full').props('outlined dense')
            with inp_vade.add_slot('append'):
                icon_v = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_v:
                    ui.date(on_change=lambda e: (inp_vade.set_value(e.value), menu_v.close()))
                icon_v.on('click', menu_v.open)

            inp_tutar = ui.number(label='Tutar', value=0, format='%.2f').classes('w-full').props('outlined dense')
            inp_notlar = ui.textarea('Notlar').classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    evrak_label = 'Senet' if inp_evrak_tipi.value == 'SENET' else 'Çek'
                    if not inp_cek_no.value:
                        notify_err(f'{evrak_label} No zorunlu')
                        return
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return

                    firma_kod = inp_firma.value or ''
                    firma_ad = ''
                    if firma_kod and firma_kod in firma_options:
                        firma_ad = firma_options[firma_kod]

                    try:
                        add_cek({
                            'cek_no': inp_cek_no.value.strip(),
                            'firma_kod': firma_kod,
                            'firma_ad': firma_ad,
                            'kesim_tarih': inp_kesim.value or '',
                            'vade_tarih': inp_vade.value or '',
                            'tutar': float(inp_tutar.value),
                            'cek_turu': cek_turu,
                            'evrak_tipi': inp_evrak_tipi.value or 'CEK',
                            'notlar': inp_notlar.value.strip() if inp_notlar.value else '',
                        })
                        notify_ok('Çek eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_edit_dialog(cek):
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('edit')
                ui.label('Çek Düzenle').classes('dialog-title')

            inp_cek_no = ui.input('Çek No', value=cek.get('cek_no', '')).classes('w-full q-mt-sm').props('outlined dense')

            inp_firma = ui.select(
                options=firma_options, label='Firma', with_input=True,
                value=cek.get('firma_kod', '')
            ).classes('w-full').props('outlined dense')

            inp_kesim = ui.input('Kesim Tarihi', value=cek.get('kesim_tarih', '')).classes('w-full').props('outlined dense')
            with inp_kesim.add_slot('append'):
                icon_k = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_k:
                    ui.date(on_change=lambda e: (inp_kesim.set_value(e.value), menu_k.close()))
                icon_k.on('click', menu_k.open)

            inp_vade = ui.input('Vade Tarihi', value=cek.get('vade_tarih', '')).classes('w-full').props('outlined dense')
            with inp_vade.add_slot('append'):
                icon_v = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_v:
                    ui.date(on_change=lambda e: (inp_vade.set_value(e.value), menu_v.close()))
                icon_v.on('click', menu_v.open)

            inp_tutar = ui.number(label='Tutar', value=cek.get('tutar', 0), format='%.2f').classes('w-full').props('outlined dense')
            inp_notlar = ui.textarea('Notlar', value=cek.get('notlar', '')).classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_cek_no.value:
                        notify_err('Çek No zorunlu')
                        return
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return

                    firma_kod = inp_firma.value or ''
                    firma_ad = ''
                    if firma_kod and firma_kod in firma_options:
                        firma_ad = firma_options[firma_kod]

                    try:
                        update_cek(cek['id'], {
                            'cek_no': inp_cek_no.value.strip(),
                            'firma_kod': firma_kod,
                            'firma_ad': firma_ad,
                            'kesim_tarih': inp_kesim.value or '',
                            'vade_tarih': inp_vade.value or '',
                            'tutar': float(inp_tutar.value),
                            'notlar': inp_notlar.value.strip() if inp_notlar.value else '',
                        })
                        notify_ok('Çek güncellendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_detail_dialog(cek):
        hareketler = get_cek_hareketleri(cek['id'])

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width:90vw; max-width:600px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('receipt_long')
                ui.label('Çek Detayı').classes('dialog-title')

            kesim = cek.get('kesim_tarih', '')
            if kesim and '-' in kesim:
                parts = kesim.split('-')
                kesim = f'{parts[2]}.{parts[1]}.{parts[0]}'
            vade = cek.get('vade_tarih', '')
            if vade and '-' in vade:
                parts = vade.split('-')
                vade = f'{parts[2]}.{parts[1]}.{parts[0]}'

            durum = cek.get('durum', '')
            durum_label = DURUM_LABELS.get(durum, durum)
            durum_color = DURUM_COLORS.get(durum, 'grey')

            info_pairs = [
                ('Çek No', cek.get('cek_no', '-')),
                ('Firma', cek.get('firma_ad', '-') or '-'),
                ('Ciro Firması', cek.get('ciro_firma_ad', '') or '-'),
                ('Kesim Tarihi', kesim or '-'),
                ('Vade Tarihi', vade or '-'),
                ('Tutar', f'{fmt_para(cek.get("tutar", 0))} TL'),
            ]
            with ui.element('div').classes('q-mt-sm'):
                for label, value in info_pairs:
                    with ui.row().classes('w-full items-center q-py-xs'):
                        ui.label(label).classes('text-body2 text-grey-7').style('width:120px')
                        ui.label(value).classes('text-body2 text-weight-medium')

            with ui.row().classes('q-mt-xs items-center'):
                ui.label('Durum').classes('text-body2 text-grey-7').style('width:120px')
                with ui.element('q-chip').props(f'dense color="{durum_color}" text-color="white"'):
                    ui.label(durum_label).classes('text-weight-bold')

            if cek.get('notlar'):
                ui.separator().classes('q-my-xs')
                ui.label(f'Not: {cek["notlar"]}').classes('text-body2 text-grey-7')

            if hareketler:
                ui.separator().classes('q-my-xs')
                ui.label('Durum Geçmişi').classes('text-subtitle2 text-weight-medium')
                from layout import TARIH_SLOT
                hareket_cols = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                    {'name': 'eski_durum', 'label': 'Eski Durum', 'field': 'eski_durum', 'align': 'center'},
                    {'name': 'yeni_durum', 'label': 'Yeni Durum', 'field': 'yeni_durum', 'align': 'center'},
                    {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                ]
                h_table = ui.table(columns=hareket_cols, rows=hareketler, row_key='id').classes('w-full q-mb-xs')
                h_table.props('flat dense bordered')
                h_table.add_slot('body-cell-tarih', TARIH_SLOT)
                h_table.add_slot('body-cell-eski_durum', r"""
                    <q-td :props="props">
                        <q-chip v-if="props.value" dense size="sm" text-color="white"
                            :color="props.value === 'PORTFOYDE' ? 'blue' :
                                    props.value === 'TAHSILE_VERILDI' ? 'orange' :
                                    props.value === 'TAHSIL_EDILDI' ? 'green' :
                                    props.value === 'CIRO_EDILDI' ? 'purple' :
                                    props.value === 'IADE_EDILDI' ? 'grey' :
                                    props.value === 'KARSILIKSIZ' ? 'red' :
                                    props.value === 'KESILDI' ? 'blue' :
                                    props.value === 'ODENDI' ? 'green' : 'grey'">
                            {{ props.value === 'PORTFOYDE' ? 'Portföyde' :
                               props.value === 'TAHSILE_VERILDI' ? 'Tahsile Verildi' :
                               props.value === 'TAHSIL_EDILDI' ? 'Tahsil Edildi' :
                               props.value === 'CIRO_EDILDI' ? 'Ciro Edildi' :
                               props.value === 'IADE_EDILDI' ? 'İade Edildi' :
                               props.value === 'KARSILIKSIZ' ? 'Karşılıksız' :
                               props.value === 'KESILDI' ? 'Kesildi' :
                               props.value === 'ODENDI' ? 'Ödendi' : props.value }}
                        </q-chip>
                        <span v-else class="text-grey-5">-</span>
                    </q-td>
                """)
                h_table.add_slot('body-cell-yeni_durum', r"""
                    <q-td :props="props">
                        <q-chip v-if="props.value" dense size="sm" text-color="white"
                            :color="props.value === 'PORTFOYDE' ? 'blue' :
                                    props.value === 'TAHSILE_VERILDI' ? 'orange' :
                                    props.value === 'TAHSIL_EDILDI' ? 'green' :
                                    props.value === 'CIRO_EDILDI' ? 'purple' :
                                    props.value === 'IADE_EDILDI' ? 'grey' :
                                    props.value === 'KARSILIKSIZ' ? 'red' :
                                    props.value === 'KESILDI' ? 'blue' :
                                    props.value === 'ODENDI' ? 'green' : 'grey'">
                            {{ props.value === 'PORTFOYDE' ? 'Portföyde' :
                               props.value === 'TAHSILE_VERILDI' ? 'Tahsile Verildi' :
                               props.value === 'TAHSIL_EDILDI' ? 'Tahsil Edildi' :
                               props.value === 'CIRO_EDILDI' ? 'Ciro Edildi' :
                               props.value === 'IADE_EDILDI' ? 'İade Edildi' :
                               props.value === 'KARSILIKSIZ' ? 'Karşılıksız' :
                               props.value === 'KESILDI' ? 'Kesildi' :
                               props.value === 'ODENDI' ? 'Ödendi' : props.value }}
                        </q-chip>
                        <span v-else class="text-grey-5">-</span>
                    </q-td>
                """)
            else:
                ui.label('Hareket bulunamadı').classes('text-grey-5 q-mb-xs')

            ui.separator().classes('q-my-xs')
            with ui.row().classes('w-full justify-end'):
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    def open_durum_dialog(cek):
        cek_id = cek['id']
        cek_turu = cek.get('cek_turu', 'ALINAN')
        current_durum = cek['durum']
        transitions = get_valid_transitions(cek_turu, current_durum)

        if not transitions:
            notify_err('Bu çek için geçerli durum geçişi yok')
            return

        transition_options = {t: DURUM_LABELS.get(t, t) for t in transitions}
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('swap_horiz')
                ui.label('Durum Değiştir').classes('dialog-title')

            ui.label(f'Mevcut Durum: {DURUM_LABELS.get(current_durum, current_durum)}').classes(
                'text-subtitle2 q-mb-sm q-mt-sm')
            ui.label(f'Çek No: {cek.get("cek_no", "")}').classes('text-caption text-grey-7 q-mb-md')

            inp_yeni = ui.select(
                options=transition_options, label='Yeni Durum'
            ).classes('w-full').props('outlined dense')

            inp_aciklama = ui.input('Açıklama').classes('w-full').props('outlined dense')

            ciro_container = ui.column().classes('w-full')
            ciro_container.set_visibility(False)
            with ciro_container:
                inp_ciro_firma = ui.select(
                    options=firma_options, label='Ciro Edilecek Firma', with_input=True
                ).classes('w-full').props('outlined dense')

            def on_durum_change(e):
                ciro_container.set_visibility(e.value == 'CIRO_EDILDI')

            inp_yeni.on_value_change(on_durum_change)

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_yeni.value:
                        notify_err('Yeni durum seçmelisiniz')
                        return

                    ciro_kod = ''
                    ciro_ad = ''
                    if inp_yeni.value == 'CIRO_EDILDI':
                        ciro_kod = inp_ciro_firma.value or ''
                        if ciro_kod and ciro_kod in firma_options:
                            ciro_ad = firma_options[ciro_kod]

                    try:
                        ok, msg = change_durum(
                            cek_id, inp_yeni.value,
                            aciklama=inp_aciklama.value.strip() if inp_aciklama.value else '',
                            ciro_firma_kod=ciro_kod,
                            ciro_firma_ad=ciro_ad
                        )
                        if ok:
                            notify_ok(msg)
                            dlg.close()
                            load_data()
                        else:
                            notify_err(msg)
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def do_delete(cek_id):
        def confirmed():
            try:
                delete_cek(cek_id)
                notify_ok('Çek silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu çeki silmek istediğinize emin misiniz?', confirmed)

    # --- Slot template'leri ---
    tarih_slot_tpl = r'''
        <q-td :props="props">
            {{ props.value ? props.value.split('-').reverse().join('.') : '' }}
        </q-td>
    '''

    vade_slot = f'''
        <q-td :props="props">
            <span :style="props.value < '{today_str}' ? 'color:red;font-weight:bold' : ''">
                {{{{ props.value ? props.value.split('-').reverse().join('.') : '' }}}}
            </span>
        </q-td>
    '''

    tutar_slot = r'''
        <q-td :props="props">
            {{ props.value != null && props.value !== 0
                ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                : '' }}
        </q-td>
    '''

    durum_slot = r'''
        <q-td :props="props">
            <span style="display:inline-block;min-width:100px;text-align:center;padding:3px 10px;border-radius:4px;font-size:11.5px;font-weight:600;letter-spacing:0.3px;"
                :style="props.value === 'PORTFOYDE' ? 'background:#dbeafe;color:#1d4ed8;' :
                        props.value === 'TAHSILE_VERILDI' ? 'background:#fef3c7;color:#92400e;' :
                        props.value === 'TAHSIL_EDILDI' ? 'background:#dcfce7;color:#15803d;' :
                        props.value === 'CIRO_EDILDI' ? 'background:#ede9fe;color:#6d28d9;' :
                        props.value === 'IADE_EDILDI' ? 'background:#f1f5f9;color:#475569;' :
                        props.value === 'KARSILIKSIZ' ? 'background:#fee2e2;color:#b91c1c;' :
                        props.value === 'KESILDI' ? 'background:#dbeafe;color:#1d4ed8;' :
                        props.value === 'ODENDI' ? 'background:#dcfce7;color:#15803d;' : 'background:#f1f5f9;color:#64748b;'">
                {{ props.value === 'PORTFOYDE' ? 'Portföyde' :
                   props.value === 'TAHSILE_VERILDI' ? 'Tahsile Verildi' :
                   props.value === 'TAHSIL_EDILDI' ? 'Tahsil Edildi' :
                   props.value === 'CIRO_EDILDI' ? 'Ciro Edildi' :
                   props.value === 'IADE_EDILDI' ? 'İade Edildi' :
                   props.value === 'KARSILIKSIZ' ? 'Karşılıksız' :
                   props.value === 'KESILDI' ? 'Kesildi' :
                   props.value === 'ODENDI' ? 'Ödendi' : props.value }}
            </span>
        </q-td>
    '''

    actions_slot = r'''
        <q-td :props="props">
            <q-btn flat round dense icon="edit" color="primary" size="sm"
                @click.stop="$parent.$emit('edit', props.row)">
                <q-tooltip>Düzenle</q-tooltip>
            </q-btn>
            <q-btn flat round dense icon="swap_horiz" color="primary" size="sm"
                @click.stop="$parent.$emit('change_durum', props.row)">
                <q-tooltip>Durum Değiştir</q-tooltip>
            </q-btn>
            <q-btn flat round dense icon="delete" color="negative" size="sm"
                @click.stop="$parent.$emit('delete', props.row)">
                <q-tooltip>Sil</q-tooltip>
            </q-btn>
        </q-td>
    '''

    evrak_tipi_slot = r'''
        <q-td :props="props">
            <q-chip dense size="sm" text-color="white"
                :color="props.value === 'SENET' ? 'orange-8' : 'blue-7'">
                {{ props.value === 'SENET' ? 'Senet' : 'Çek' }}
            </q-chip>
        </q-td>
    '''

    def setup_table(tbl, cek_turu):
        tbl.props('flat bordered dense')
        tbl.add_slot('body-cell-evrak_tipi', evrak_tipi_slot)
        tbl.add_slot('body-cell-kesim_tarih', tarih_slot_tpl)
        tbl.add_slot('body-cell-vade_tarih', vade_slot)
        tbl.add_slot('body-cell-tutar', tutar_slot)
        tbl.add_slot('body-cell-durum', durum_slot)
        tbl.add_slot('body-cell-actions', actions_slot)
        tbl.on('edit', lambda e: open_edit_dialog(e.args))
        tbl.on('change_durum', lambda e: open_durum_dialog(e.args))
        tbl.on('delete', lambda e: do_delete(e.args['id']))
        tbl.on('rowClick', lambda e: open_detail_dialog(e.args[1]))

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-xs'):
        with ui.tabs().classes('w-full').props('dense no-caps') as tabs:
            tab_alinan = ui.tab('alinan', label='Alınan Çek / Senet')
            tab_verilen = ui.tab('verilen', label='Verilen Çek / Senet')

        with ui.tab_panels(tabs, value='alinan').classes('w-full'):
            with ui.tab_panel('alinan'):
                alinan_rows = list_cekler('ALINAN')
                with ui.card().classes('w-full q-pa-xs q-mb-xs'):
                    with ui.row().classes('w-full items-center gap-2 no-wrap'):
                        ui.input(
                            placeholder='Ara (çek no, firma, durum)...',
                            on_change=lambda e: (setattr(alinan_table, 'rows', _filter(alinan_rows, e.value)), alinan_table.update())
                        ).props('outlined dense clearable').classes('w-80')
                        ui.space()
                        ui.button(
                            'PDF', icon='picture_as_pdf', color='primary',
                            on_click=lambda: _open_pdf(generate_cek_raporu_pdf(alinan_rows), 'alinan_cekler.pdf')
                        ).props('dense')
                        ui.button('Yeni Çek/Senet', icon='add', color='primary',
                                  on_click=lambda: open_add_dialog('ALINAN')).props('dense')

                alinan_table = ui.table(
                    columns=alinan_columns, rows=alinan_rows, row_key='id',
                    pagination={'rowsPerPage': 50, 'sortBy': 'vade_tarih', 'descending': True}
                ).classes('w-full')
                setup_table(alinan_table, 'ALINAN')

            with ui.tab_panel('verilen'):
                verilen_rows = list_cekler('VERILEN')
                with ui.card().classes('w-full q-pa-xs q-mb-xs'):
                    with ui.row().classes('w-full items-center gap-2 no-wrap'):
                        ui.input(
                            placeholder='Ara (çek no, firma, durum)...',
                            on_change=lambda e: (setattr(verilen_table, 'rows', _filter(verilen_rows, e.value)), verilen_table.update())
                        ).props('outlined dense clearable').classes('w-80')
                        ui.space()
                        ui.button(
                            'PDF', icon='picture_as_pdf', color='primary',
                            on_click=lambda: _open_pdf(generate_cek_raporu_pdf(verilen_rows), 'verilen_cekler.pdf')
                        ).props('dense')
                        ui.button('Yeni Çek/Senet', icon='add', color='primary',
                                  on_click=lambda: open_add_dialog('VERILEN')).props('dense')

                verilen_table = ui.table(
                    columns=verilen_columns, rows=verilen_rows, row_key='id',
                    pagination={'rowsPerPage': 50, 'sortBy': 'vade_tarih', 'descending': True}
                ).classes('w-full')
                setup_table(verilen_table, 'VERILEN')






