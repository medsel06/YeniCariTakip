"""ALSE Plastik Hammadde - Kasa Sayfası"""
from datetime import date, datetime
from nicegui import ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, confirm_dialog, normalize_search, donem_popover_btn
from services.kasa_service import get_kasa_list, get_kasa_bakiye, add_kasa, delete_kasa, update_kasa, get_kasa_by_id
from services.cari_service import get_firma_list
from services.cek_service import list_cekler_portfoyde, generate_firma_cek_no, add_cek, change_durum
from services.pdf_service import generate_kasa_raporu_pdf, save_pdf_preview
from services.gelir_gider_service import GIDER_KATEGORILER, GELIR_KATEGORILER


@ui.page('/kasa')
def kasa_page():
    if not create_layout(active_path='/kasa', page_title='Kasa'):
        return

    def _open_pdf(pdf_bytes, filename: str):
        preview_url = save_pdf_preview(pdf_bytes, filename)
        ui.run_javascript(f"window.open('{preview_url}', '_blank')")

    now = datetime.now()
    # Default: yillik mod + mevcut yil (donem_popover_btn default_mode='YIL' ile sync)
    state = {'yil': now.year, 'ay': None}

    table_ref = None
    card_giris = None
    card_cikis = None
    card_bakiye = None
    search_val = {'text': ''}

    columns = [
        {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'left', 'sortable': True},
        {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
        {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
        {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
        {'name': 'odeme_sekli', 'label': 'Ödeme Şekli', 'field': 'odeme_sekli', 'align': 'center',
         'sortable': True},
        {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left', 'sortable': False},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center', 'sortable': False},
    ]

    def _filter_rows(rows):
        q = normalize_search(search_val['text'])
        if not q:
            return rows
        return [r for r in rows if q in normalize_search(r.get('firma_ad', ''))
                or q in normalize_search(r.get('aciklama', ''))
                or q in normalize_search(r.get('odeme_sekli', ''))]

    def apply_filters():
        if table_ref:
            table_ref.rows = _filter_rows(all_rows)
            table_ref.update()

    def load_data():
        nonlocal table_ref, all_rows
        all_rows = get_kasa_list(yil=state['yil'], ay=state['ay'])
        apply_filters()
        bakiye = get_kasa_bakiye(yil=state['yil'], ay=state['ay'])
        if card_giris:
            card_giris.set_text(fmt_para(bakiye['giris']) + ' TL')
        if card_cikis:
            card_cikis.set_text(fmt_para(bakiye['cikis']) + ' TL')
        if card_bakiye:
            card_bakiye.set_text(fmt_para(bakiye['bakiye']) + ' TL')

    def open_add_dialog():
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 550px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('add_circle')
                ui.label('Yeni Kasa Kaydı').classes('dialog-title')

            # Tarih
            inp_tarih = ui.input('Tarih', value=date.today().isoformat()).classes('w-full q-mt-sm').props('outlined dense')
            with inp_tarih.add_slot('append'):
                icon = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu:
                    dp = ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu.close()))
                icon.on('click', menu.open)

            # Firma
            inp_firma = ui.select(
                options=firma_options, label='Firma', with_input=True
            ).classes('w-full').props('outlined dense')

            # Tur
            inp_tur = ui.select(
                options={'GELIR': 'Gelir', 'GIDER': 'Gider'}, label='Tür', value='GIDER'
            ).classes('w-full').props('outlined dense')

            # Kategori (Gider secildiginde gorunur)
            kat_options = {k: k for k in GIDER_KATEGORILER}
            inp_kategori = ui.select(
                options=kat_options, label='Kategori', with_input=True
            ).classes('w-full').props('outlined dense clearable')
            inp_kategori.set_visibility(True)

            def on_tur_change(e):
                if e.value == 'GIDER':
                    inp_kategori.options = {k: k for k in GIDER_KATEGORILER}
                    inp_kategori.set_visibility(True)
                elif e.value == 'GELIR':
                    inp_kategori.options = {k: k for k in GELIR_KATEGORILER}
                    inp_kategori.set_visibility(True)
                inp_kategori.value = None
            inp_tur.on_value_change(on_tur_change)

            # Tutar
            inp_tutar = ui.number(label='Tutar', value=0, format='%.2f').classes('w-full').props('outlined dense')

            # Odeme Sekli
            inp_odeme = ui.select(
                options={'NAKIT': 'Nakit', 'HAVALE': 'Havale', 'CEK': 'Çek', 'SENET': 'Senet', 'DIGER': 'Diğer'},
                label='Ödeme Şekli', value='NAKIT'
            ).classes('w-full').props('outlined dense')

            # --- Çek ek alanları (başlangıçta gizli) ---
            cek_container = ui.column().classes('w-full')
            cek_container.set_visibility(False)

            with cek_container:
                ui.separator().classes('q-my-xs')
                ui.label('Çek Bilgileri').classes('text-subtitle2 text-weight-medium')

                inp_cek_turu = ui.select(
                    options={'FIRMA': 'Firma Çeki', 'CIRO': 'Ciro Çeki'},
                    label='Çek Türü', value='FIRMA'
                ).classes('w-full').props('outlined dense')

                # Firma çeki alanları
                firma_cek_container = ui.column().classes('w-full')
                with firma_cek_container:
                    auto_cek_no = generate_firma_cek_no()
                    inp_cek_no = ui.input('Çek No', value=auto_cek_no).classes('w-full').props('outlined dense')
                    inp_cek_vade = ui.input('Çek Vade Tarihi', value=date.today().isoformat()).classes('w-full').props('outlined dense')
                    with inp_cek_vade.add_slot('append'):
                        icon_cv = ui.icon('event').classes('cursor-pointer')
                        with ui.menu() as menu_cv:
                            ui.date(on_change=lambda e: (inp_cek_vade.set_value(e.value), menu_cv.close()))
                        icon_cv.on('click', menu_cv.open)

                # Ciro çeki alanları
                ciro_container = ui.column().classes('w-full')
                ciro_container.set_visibility(False)
                with ciro_container:
                    portfoydeki = list_cekler_portfoyde()
                    ciro_tutar_map = {str(c['id']): float(c.get('tutar', 0) or 0) for c in portfoydeki}
                    cek_options = {str(c['id']): f"{c['cek_no']} - {c.get('firma_ad', '')} - {fmt_para(c.get('tutar', 0))} TL" for c in portfoydeki}
                    inp_ciro_cek = ui.select(
                        options=cek_options, label='Ciro Edilecek Çek', with_input=True
                    ).classes('w-full').props('outlined dense')
                    inp_ciro_cek.on_value_change(
                        lambda e: inp_tutar.set_value(ciro_tutar_map.get(str(e.value), inp_tutar.value))
                    )

                def on_cek_turu_change(e):
                    firma_cek_container.set_visibility(e.value == 'FIRMA')
                    ciro_container.set_visibility(e.value == 'CIRO')
                inp_cek_turu.on_value_change(on_cek_turu_change)

            def on_odeme_change(e):
                cek_container.set_visibility(e.value == 'CEK')
            inp_odeme.on_value_change(on_odeme_change)

            # Açıklama
            inp_aciklama = ui.input('Açıklama').classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return

                    firma_kod = inp_firma.value or ''
                    firma_ad = ''
                    if firma_kod and firma_kod in firma_options:
                        firma_ad = firma_options[firma_kod]

                    odeme_secili = inp_odeme.value or ''
                    tutar_val = float(inp_tutar.value)
                    cek_id_ref = None

                    try:
                        if odeme_secili == 'CEK':
                            cek_turu_val = inp_cek_turu.value

                            if cek_turu_val == 'FIRMA':
                                # Firma çeki: yeni çek oluştur
                                cek_no_val = inp_cek_no.value.strip() if inp_cek_no.value else ''
                                if not cek_no_val:
                                    notify_err('Çek No zorunlu')
                                    return
                                cek_vade_val = inp_cek_vade.value or ''

                                # Duplicate çek no kontrolü
                                from services.cek_service import get_cek_by_id
                                from db import get_db
                                with get_db() as conn:
                                    existing = conn.execute(
                                        'SELECT id FROM cekler WHERE cek_no=?', (cek_no_val,)
                                    ).fetchone()
                                    if existing:
                                        notify_err(f'Bu çek numarası zaten mevcut: {cek_no_val}')
                                        return

                                cek_id_ref = add_cek({
                                    'cek_no': cek_no_val,
                                    'firma_kod': firma_kod,
                                    'firma_ad': firma_ad,
                                    'kesim_tarih': inp_tarih.value or '',
                                    'vade_tarih': cek_vade_val,
                                    'tutar': tutar_val,
                                    'cek_turu': 'VERILEN',
                                    'notlar': inp_aciklama.value.strip() if inp_aciklama.value else '',
                                })

                            elif cek_turu_val == 'CIRO':
                                # Ciro çeki: portföydeki çeki ciro et — KASA KAYDI OLUŞTURULMAZ
                                # Ciro nakit hareketi değil, sadece çek el değiştirir.
                                # Cari etki (yeni firmaya ödeme) merkezi ledger'dan otomatik gelir.
                                secili_cek_id = inp_ciro_cek.value
                                if not secili_cek_id:
                                    notify_err('Ciro edilecek çek seçmelisiniz')
                                    return
                                cek_id_ref = int(secili_cek_id)
                                ok, msg = change_durum(
                                    cek_id_ref, 'CIRO_EDILDI',
                                    aciklama=f'Kasa kaydı ile ciro: {inp_aciklama.value or ""}',
                                    ciro_firma_kod=firma_kod,
                                    ciro_firma_ad=firma_ad
                                )
                                if not ok:
                                    notify_err(f'Çek ciro hatası: {msg}')
                                    return
                                # Ciro: kasa kaydı yok, dialog kapat
                                notify_ok('Çek ciro edildi (cari etkisi otomatik)')
                                dlg.close()
                                load_data()
                                return

                        kasa_data = {
                            'tarih': inp_tarih.value,
                            'firma_kod': firma_kod,
                            'firma_ad': firma_ad,
                            'tur': inp_tur.value,
                            'tutar': tutar_val,
                            'odeme_sekli': odeme_secili,
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                            'kategori': inp_kategori.value or '',
                        }
                        if cek_id_ref:
                            kasa_data['cek_id'] = cek_id_ref

                        add_kasa(kasa_data)
                        notify_ok('Kasa kaydı eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_edit_dialog(row):
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('edit')
                ui.label('Kasa Kaydı Düzenle').classes('dialog-title')

            inp_tarih = ui.input('Tarih', value=row.get('tarih', '')).classes('w-full q-mt-sm').props('outlined dense')
            with inp_tarih.add_slot('append'):
                icon = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu:
                    dp = ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu.close()))
                icon.on('click', menu.open)

            inp_firma = ui.select(
                options=firma_options, label='Firma', with_input=True,
                value=row.get('firma_kod', '')
            ).classes('w-full').props('outlined dense')

            inp_tur = ui.select(
                options={'GELIR': 'Gelir', 'GIDER': 'Gider'}, label='Tür',
                value=row.get('tur', 'GIDER')
            ).classes('w-full').props('outlined dense')

            inp_tutar = ui.number(label='Tutar', value=row.get('tutar', 0), format='%.2f').classes('w-full').props('outlined dense')

            inp_odeme = ui.select(
                options={'NAKIT': 'Nakit', 'HAVALE': 'Havale', 'CEK': 'Çek', 'SENET': 'Senet', 'DIGER': 'Diğer'},
                label='Ödeme Şekli', value=row.get('odeme_sekli', 'NAKIT')
            ).classes('w-full').props('outlined dense')

            inp_aciklama = ui.input('Açıklama', value=row.get('aciklama', '')).classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return

                    firma_kod = inp_firma.value or ''
                    firma_ad = ''
                    if firma_kod and firma_kod in firma_options:
                        firma_ad = firma_options[firma_kod]

                    try:
                        update_kasa(row['id'], {
                            'tarih': inp_tarih.value,
                            'firma_kod': firma_kod,
                            'firma_ad': firma_ad,
                            'tur': inp_tur.value,
                            'tutar': float(inp_tutar.value),
                            'odeme_sekli': inp_odeme.value or '',
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        })
                        notify_ok('Kasa kaydı güncellendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_detail_dialog(row):
        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width:90vw; max-width:500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('account_balance_wallet')
                ui.label('Kasa Kaydı Detayı').classes('dialog-title')

            tarih = row.get('tarih', '')
            if tarih and '-' in tarih:
                parts = tarih.split('-')
                tarih = f'{parts[2]}.{parts[1]}.{parts[0]}'

            tur = row.get('tur', '')
            tur_label = 'Gelir' if tur == 'GELIR' else 'Gider'
            tur_color = 'positive' if tur == 'GELIR' else 'negative'

            info_pairs = [
                ('Tarih', tarih),
                ('Firma', row.get('firma_ad', '-') or '-'),
                ('Tutar', f'{fmt_para(row.get("tutar", 0))} TL'),
                ('Ödeme Şekli', row.get('odeme_sekli', '-') or '-'),
            ]
            with ui.element('div').classes('q-mt-sm'):
                for label, value in info_pairs:
                    with ui.row().classes('w-full items-center q-py-xs'):
                        ui.label(label).classes('text-body2 text-grey-7').style('width:120px')
                        ui.label(str(value)).classes('text-body2 text-weight-medium')

            with ui.row().classes('items-center q-py-xs'):
                ui.label('Tür').classes('text-body2 text-grey-7').style('width:120px')
                with ui.element('q-chip').props(f'dense color="{tur_color}" text-color="white" size="sm"'):
                    ui.label(tur_label).classes('text-weight-bold')

            if row.get('aciklama'):
                ui.separator().classes('q-my-xs')
                ui.label(f'Not: {row["aciklama"]}').classes('text-body2 text-grey-7')

            if row.get('cek_id'):
                ui.separator().classes('q-my-xs')
                ui.label('Bağlı Çek Bilgisi').classes('text-subtitle2 text-weight-medium')
                from services.cek_service import get_cek_by_id
                cek = get_cek_by_id(row['cek_id'])
                if cek:
                    cek_pairs = [
                        ('Çek No', cek.get('cek_no', '-')),
                        ('Tutar', f'{fmt_para(cek.get("tutar", 0))} TL'),
                        ('Durum', cek.get('durum', '-')),
                    ]
                    for label, value in cek_pairs:
                        with ui.row().classes('w-full items-center q-py-xs'):
                            ui.label(label).classes('text-body2 text-grey-7').style('width:120px')
                            ui.label(str(value)).classes('text-body2 text-weight-medium')

            ui.separator().classes('q-my-xs')
            with ui.row().classes('w-full justify-end'):
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    def do_delete(row_id):
        def confirmed():
            try:
                delete_kasa(row_id)
                notify_ok('Kayıt silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu kasa kaydını silmek istediğinize emin misiniz?', confirmed)

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_kasa_list(yil=state['yil'], ay=state['ay'])

        bakiye = get_kasa_bakiye(yil=state['yil'], ay=state['ay'])

        def _on_search_change(e):
            search_val['text'] = e.value or ''
            apply_filters()

        # --- Tek satir toolbar: filtreler + ozet chipleri + aksiyonlar ---
        with ui.row().classes('w-full items-center gap-2 q-mb-sm no-wrap'):
            # Sol grup: arama + donem
            search_input = ui.input(
                placeholder='Ara (firma, açıklama)...',
                on_change=_on_search_change,
            ).props('outlined dense clearable').classes('w-64')

            def _donem_changed(yil, ay):
                state['yil'] = yil
                state['ay'] = ay
                load_data()

            donem_popover_btn(_donem_changed, default_mode='YIL')

            # Ayirici bosluk
            ui.element('div').style('flex:1')

            # Orta grup: ozet chipleri (kompakt — tek satira sigsin)
            def _summary_chip(icon, label_text, value_label_ref, accent_bg, accent_fg, accent_border):
                with ui.element('div').style(
                    f'display:inline-flex;align-items:center;gap:6px;padding:4px 10px;'
                    f'background:{accent_bg};border:1px solid {accent_border};border-radius:999px;'
                    f'white-space:nowrap;'
                ):
                    ui.icon(icon).style(f'font-size:14px;color:{accent_fg};')
                    ui.label(label_text).classes('text-caption').style(
                        f'color:{accent_fg};font-weight:600;font-size:11px;line-height:1;'
                    )
                    value_label_ref['ref'] = ui.label(f'{fmt_para(0)} TL').style(
                        f'color:{accent_fg};font-weight:700;font-size:12.5px;line-height:1;'
                        'font-variant-numeric:tabular-nums;'
                    )

            _giris_ref = {}
            _cikis_ref = {}
            _bakiye_ref = {}
            _summary_chip('arrow_downward', 'Giriş', _giris_ref, '#dcfce7', '#15803d', '#86efac')
            _summary_chip('arrow_upward', 'Çıkış', _cikis_ref, '#fee2e2', '#b91c1c', '#fca5a5')
            _summary_chip('account_balance', 'Bakiye', _bakiye_ref, '#dbeafe', '#1d4ed8', '#93c5fd')
            card_giris = _giris_ref['ref']
            card_cikis = _cikis_ref['ref']
            card_bakiye = _bakiye_ref['ref']
            card_giris.set_text(f'{fmt_para(bakiye["giris"])} TL')
            card_cikis.set_text(f'{fmt_para(bakiye["cikis"])} TL')
            card_bakiye.set_text(f'{fmt_para(bakiye["bakiye"])} TL')

            ui.element('div').style('flex:1')

            # Sag grup: aksiyon butonlari
            def _download_pdf():
                pdf_bytes = generate_kasa_raporu_pdf(all_rows, get_kasa_bakiye(yil=state['yil'], ay=state['ay']))
                _open_pdf(pdf_bytes, 'kasa_hizli_rapor.pdf')

            ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_download_pdf).props('dense')
            ui.button('Yeni Kayıt', icon='add', color='primary', on_click=open_add_dialog).props('dense')

        # Table
        table_ref = ui.table(
            columns=columns, rows=all_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full').style('--table-extra-rows: 2;')
        table_ref.props('flat bordered dense')

        # Slot - tarih ve tutar NaN fix
        table_ref.add_slot('body-cell-tarih', TARIH_SLOT)
        table_ref.add_slot('body-cell-tutar', PARA_SLOT)

        # Row coloring by tur (GELIR=green, GIDER=red)
        table_ref.add_slot('body-cell-tur', r'''
            <q-td :props="props">
                <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
                    <q-chip dense :color="props.value === 'GELIR' ? 'positive' : 'negative'" text-color="white" size="sm">
                        {{ props.value === 'GELIR' ? 'Gelir' : 'Gider' }}
                    </q-chip>
                    <q-chip v-if="props.row.aciklama && props.row.aciklama.startsWith('Maaş Ödeme:')"
                        dense color="pink-3" text-color="pink-9" size="sm">Maaş</q-chip>
                    <q-chip v-else-if="props.row.aciklama && props.row.aciklama.startsWith('Avans:')"
                        dense color="orange-3" text-color="orange-9" size="sm">Avans</q-chip>
                    <q-chip v-else-if="props.row.kategori"
                        dense color="blue-grey-2" text-color="blue-grey-8" size="sm">
                        {{ props.row.kategori }}
                    </q-chip>
                </div>
            </q-td>
        ''')

        # Actions slot - edit + delete
        table_ref.add_slot('body-cell-actions', r'''
            <q-td :props="props">
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
        table_ref.on('edit', lambda e: open_edit_dialog(e.args))
        table_ref.on('delete', lambda e: do_delete(e.args['id']))

        # Satir tiklama - detay dialog
        table_ref.on('rowClick', lambda e: open_detail_dialog(e.args[1]))









