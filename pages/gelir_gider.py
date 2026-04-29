"""ALSE Plastik Hammadde - Gelir/Gider Sayfasi"""
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, fmt_para, PARA_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog, normalize_search, donem_secici,
)
from services.gelir_gider_service import (
    get_gelir_gider_list, get_gelir_gider_ozet,
    add_gelir_gider, update_gelir_gider, delete_gelir_gider,
    GELIR_KATEGORILER, GIDER_KATEGORILER, ONE_CIKAN_GIDER_KATEGORILER,
)
from services.kasa_service import add_kasa
from services.cari_service import get_firma_list, add_firma, generate_firma_kod
from services.pdf_service import generate_table_pdf, save_pdf_preview


@ui.page('/gelir-gider')
def gelir_gider_page():
    if not create_layout(active_path='/gelir-gider', page_title='Gelir / Gider'):
        return

    table_ref = None
    all_rows = []
    lbl_gelir = None
    lbl_gider = None
    lbl_net = None
    now = datetime.now()
    # Default: yil=mevcut, ay=None (Tumu) — UI donem_secici default_ay=0 ile sync
    state = {'yil': now.year, 'ay': None}

    columns = [
        {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
        {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
        {'name': 'kategori', 'label': 'Kategori', 'field': 'kategori', 'align': 'left', 'sortable': True},
        {'name': 'firma_ad', 'label': 'Cari', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
        {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
        {'name': 'toplam', 'label': 'Toplam', 'field': 'toplam', 'align': 'right', 'sortable': True},
        {'name': 'odeme_durumu', 'label': 'Durum', 'field': 'odeme_durumu', 'align': 'center'},
        {'name': 'odeme_sekli', 'label': 'Ödeme', 'field': 'odeme_sekli', 'align': 'center'},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center'},
    ]

    def load_data():
        nonlocal all_rows
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        if table_ref:
            table_ref.rows = all_rows
            table_ref.update()
        ozet = get_gelir_gider_ozet(yil=state['yil'], ay=state['ay'])
        if lbl_gelir:
            lbl_gelir.set_text(f'Gelir: {fmt_para(ozet["gelir"])} TL')
        if lbl_gider:
            lbl_gider.set_text(f'Gider: {fmt_para(ozet["gider"])} TL')
        if lbl_net:
            lbl_net.set_text(f'Net: {fmt_para(ozet["net"])} TL')

    def do_filter(query):
        if not query:
            return all_rows
        q = normalize_search(query)
        return [r for r in all_rows if
                q in normalize_search(r.get('kategori', '')) or
                q in normalize_search(r.get('aciklama', '')) or
                q in normalize_search(r.get('firma_ad', '')) or
                q in normalize_search(r.get('tur', ''))]

    def _build_kategori_options(tur):
        """Kategori secenekleri - one cikanlar en ustte, renkli iconlu."""
        if tur == 'GELIR':
            return {k: k for k in GELIR_KATEGORILER}
        # GIDER - one cikanlari emoji ile vurgula
        opts = {}
        for k in GIDER_KATEGORILER:
            if k == 'Nakliye':
                opts[k] = '🚚 Nakliye'
            elif k == 'Ardiye':
                opts[k] = '📦 Ardiye'
            else:
                opts[k] = k
        return opts

    def open_quick_firma_dialog(on_added):
        """Hizli firma ekleme dialogu."""
        with ui.dialog() as qdlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 420px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('add_business')
                ui.label('Yeni Cari Ekle').classes('dialog-title')
            inp_ad = ui.input('Firma / Cari Adı').props('outlined dense').classes('w-full q-mt-sm')
            inp_tel = ui.input('Telefon').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=qdlg.close).props('flat color=grey')
                def _save():
                    ad = (inp_ad.value or '').strip()
                    if not ad:
                        notify_err('Firma adı zorunlu')
                        return
                    try:
                        kod = generate_firma_kod()
                        add_firma({
                            'kod': kod, 'ad': ad, 'tel': inp_tel.value or '', 'adres': '',
                        })
                        notify_ok(f'Cari eklendi: {ad}')
                        qdlg.close()
                        on_added(kod, ad)
                    except Exception as e:
                        notify_err(f'Hata: {e}')
                ui.button('Kaydet', color='primary', on_click=_save).props('unelevated')
        qdlg.open()

    def open_dialog(edit_row=None):
        is_edit = edit_row is not None
        title = 'Kayıt Düzenle' if is_edit else 'Yeni Gelir/Gider'

        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 640px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('payments' if not is_edit else 'edit')
                ui.label(title).classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                # Tarih
                inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_tarih.add_slot('append'):
                    icon_t = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_t:
                        ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu_t.close()))
                    icon_t.on('click', menu_t.open)

                with ui.row().classes('w-full gap-md'):
                    inp_tur = ui.select(
                        options={'GELIR': 'Gelir', 'GIDER': 'Gider'},
                        label='Tür', value='GIDER'
                    ).props('outlined dense').classes('col')

                    inp_kategori = ui.select(
                        options=_build_kategori_options('GIDER'),
                        label='Kategori', value='Nakliye'
                    ).props('outlined dense').classes('col')

                # One cikan uyari (Nakliye/Ardiye icin)
                lbl_one_cikan = ui.label('').classes('text-caption text-orange-9 q-pl-sm')

                def on_tur_change(e):
                    opts = _build_kategori_options(e.value)
                    inp_kategori.options = opts
                    first_key = next(iter(opts))
                    inp_kategori.value = first_key
                    inp_kategori.update()
                    on_kategori_change(None)
                inp_tur.on_value_change(on_tur_change)

                # --- CARI SECIMI (opsiyonel tum giderlerde, Nakliye/Ardiye icin otomatik acilir) ---
                cari_container = ui.column().classes('w-full')
                with cari_container:
                    with ui.row().classes('w-full gap-sm items-center no-wrap'):
                        inp_firma = ui.select(
                            options=firma_options, label='Cari (Opsiyonel)',
                            with_input=True, clearable=True,
                        ).props('outlined dense').classes('col')
                        ui.button(icon='add', color='primary',
                                  on_click=lambda: open_quick_firma_dialog(_on_firma_added)
                                  ).props('round dense flat').tooltip('Yeni Cari Ekle')

                    lbl_firma_bakiye = ui.label('').classes('text-caption text-grey-7 q-pl-sm')

                def _on_firma_added(kod, ad):
                    firmalar2 = get_firma_list()
                    new_opts = {f['kod']: f['ad'] for f in firmalar2}
                    inp_firma.options = new_opts
                    inp_firma.value = kod
                    inp_firma.update()

                def on_kategori_change(_e):
                    kat = inp_kategori.value or ''
                    if kat in ONE_CIKAN_GIDER_KATEGORILER:
                        lbl_one_cikan.set_text(f'⭐ {kat}: Cari seçerek borç takibi yapabilirsiniz')
                    else:
                        lbl_one_cikan.set_text('')
                inp_kategori.on_value_change(on_kategori_change)

                with ui.row().classes('w-full gap-md'):
                    inp_tutar = ui.number(label='Tutar (Net)', value=0, format='%.2f').props('outlined dense').classes('col')
                    inp_kdv = ui.select(
                        options={0: '%0', 1: '%1', 10: '%10', 20: '%20'},
                        label='KDV Oranı', value=20
                    ).props('outlined dense').classes('col')

                # Odeme Durumu
                ui.label('Ödeme Durumu').classes('text-subtitle2 text-weight-medium q-mt-sm')
                inp_durum = ui.radio(
                    options={
                        'NAKIT': 'Nakit (Kasa)',
                        'HAVALE': 'Havale / EFT (Banka)',
                        'CEK': 'Çek',
                        'SENET': 'Senet',
                        'ODENMEDI': 'Ödenmedi (Cari borç)',
                    },
                    value='NAKIT',
                ).props('inline')

                # Odenen tutar ve banka alanlari
                odeme_container = ui.column().classes('w-full gap-sm')
                with odeme_container:
                    with ui.row().classes('w-full gap-md items-center no-wrap'):
                        inp_odenen = ui.number(
                            label='Ödenen Tutar', value=0, format='%.2f'
                        ).props('outlined dense').classes('col')
                        lbl_kalan_borc = ui.label('').classes('text-caption text-orange-9').style('min-width: 140px')

                    banka_row = ui.row().classes('w-full')
                    banka_row.set_visibility(False)
                    with banka_row:
                        inp_banka = ui.input('Banka (isteğe bağlı)').props('outlined dense').classes('col')

                # Vade tarih - ODENMEDI secilince gorunsun
                vade_container = ui.row().classes('w-full')
                vade_container.set_visibility(False)
                with vade_container:
                    inp_vade = ui.input('Vade Tarihi', value='').props('outlined dense').classes('col')
                    with inp_vade.add_slot('append'):
                        icon_v = ui.icon('event').classes('cursor-pointer')
                        with ui.menu() as menu_v:
                            ui.date(on_change=lambda e: (inp_vade.set_value(e.value), menu_v.close()))
                        icon_v.on('click', menu_v.open)

                inp_aciklama = ui.input('Açıklama').props('outlined dense').classes('w-full')

                # Hesaplama alani
                ui.separator()
                with ui.row().classes('w-full gap-md items-center'):
                    lbl_tutar = ui.label('Tutar: 0,00 TL').classes('text-subtitle2 col')
                    lbl_kdv = ui.label('KDV: 0,00 TL').classes('text-subtitle2 col')
                    lbl_toplam = ui.label('Toplam: 0,00 TL').classes('text-subtitle2 text-weight-bold col text-primary')

                def fmt_tr(val):
                    s = f"{abs(val):,.2f}"
                    return s.replace(',', 'X').replace('.', ',').replace('X', '.')

                def _guncel_toplam():
                    t = float(inp_tutar.value or 0)
                    ko = float(inp_kdv.value or 0)
                    kdv = t * ko / 100
                    return t + kdv

                def recalc():
                    t = float(inp_tutar.value or 0)
                    ko = float(inp_kdv.value or 0)
                    kdv = t * ko / 100
                    toplam = t + kdv
                    lbl_tutar.set_text(f'Tutar: {fmt_tr(t)} TL')
                    lbl_kdv.set_text(f'KDV: {fmt_tr(kdv)} TL')
                    lbl_toplam.set_text(f'Toplam: {fmt_tr(toplam)} TL')

                    # Odenen varsayilan: toplam (sadece ODENMEDI degilse ve kullanici ellemediyse guncellenir)
                    if (inp_durum.value or 'NAKIT') != 'ODENMEDI':
                        inp_odenen.value = toplam
                    _recalc_kalan()

                def _recalc_kalan():
                    toplam = _guncel_toplam()
                    odenen = float(inp_odenen.value or 0)
                    if (inp_durum.value or 'NAKIT') == 'ODENMEDI':
                        lbl_kalan_borc.set_text(f'Borç: {fmt_tr(toplam)} TL')
                        lbl_kalan_borc.classes('text-caption text-red-7 text-weight-bold', remove='text-orange-9')
                    else:
                        kalan = toplam - odenen
                        if kalan > 0.01:
                            lbl_kalan_borc.set_text(f'Kalan Borç: {fmt_tr(kalan)} TL')
                            lbl_kalan_borc.classes('text-caption text-red-7 text-weight-bold', remove='text-orange-9')
                        elif kalan < -0.01:
                            lbl_kalan_borc.set_text(f'Fazla Ödeme: {fmt_tr(-kalan)} TL')
                            lbl_kalan_borc.classes('text-caption text-orange-9', remove='text-red-7 text-weight-bold')
                        else:
                            lbl_kalan_borc.set_text('✓ Tam ödeme')
                            lbl_kalan_borc.classes('text-caption text-green-7 text-weight-bold', remove='text-red-7 text-orange-9')

                def on_durum_change(_e):
                    val = inp_durum.value or 'NAKIT'
                    vade_container.set_visibility(val == 'ODENMEDI')
                    odeme_container.set_visibility(val != 'ODENMEDI')
                    banka_row.set_visibility(val == 'HAVALE')
                    if val != 'ODENMEDI':
                        # Odenen'i toplamla eslestir
                        inp_odenen.value = _guncel_toplam()
                    _recalc_kalan()
                inp_durum.on_value_change(on_durum_change)

                inp_tutar.on_value_change(lambda _: recalc())
                inp_kdv.on_value_change(lambda _: recalc())
                inp_odenen.on_value_change(lambda _: _recalc_kalan())

            # Duzenleme modunda doldur
            if is_edit:
                inp_tarih.value = edit_row.get('tarih', '')
                inp_tur.value = edit_row.get('tur', 'GIDER')
                cats = _build_kategori_options(edit_row.get('tur', 'GIDER'))
                inp_kategori.options = cats
                inp_kategori.value = edit_row.get('kategori', next(iter(cats)))
                inp_kategori.update()
                inp_tutar.value = edit_row.get('tutar', 0)
                inp_kdv.value = int(edit_row.get('kdv_orani', 0))
                inp_firma.value = edit_row.get('firma_kod', '') or None
                # Duzenleme: durum → mevcut odeme_sekli'nden cikar
                odm_sk = (edit_row.get('odeme_sekli') or 'NAKIT').upper()
                od_dr = edit_row.get('odeme_durumu') or ''
                if od_dr == 'ODENMEDI':
                    inp_durum.value = 'ODENMEDI'
                elif odm_sk == 'HAVALE':
                    inp_durum.value = 'HAVALE'
                else:
                    inp_durum.value = 'NAKIT'
                vade_container.set_visibility(inp_durum.value == 'ODENMEDI')
                odeme_container.set_visibility(inp_durum.value != 'ODENMEDI')
                banka_row.set_visibility(inp_durum.value == 'HAVALE')
                inp_vade.value = edit_row.get('vade_tarih', '') or ''
                inp_aciklama.value = edit_row.get('aciklama', '')
                recalc()
                on_kategori_change(None)
            else:
                # Yeni kayit: recalc ve initial state
                on_durum_change(None)
                recalc()

            # Initial kategori uyari cek
            on_kategori_change(None)

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    t = float(inp_tutar.value or 0)
                    if t <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return

                    ko = float(inp_kdv.value or 0)
                    kdv = t * ko / 100
                    toplam = t + kdv

                    durum = inp_durum.value or 'NAKIT'
                    odenen = float(inp_odenen.value or 0) if durum != 'ODENMEDI' else 0
                    banka_val = (inp_banka.value or '').strip() if durum == 'HAVALE' else ''

                    if durum == 'HAVALE':
                        odeme_sekli = 'HAVALE'
                    elif durum == 'ODENMEDI':
                        odeme_sekli = ''
                    else:
                        odeme_sekli = 'NAKIT'

                    # Odeme durumu: ODENDI / KISMI / ODENMEDI
                    if durum == 'ODENMEDI' or odenen <= 0.001:
                        odeme_durumu = 'ODENMEDI'
                    elif odenen >= toplam - 0.001:
                        odeme_durumu = 'ODENDI'
                    else:
                        odeme_durumu = 'KISMI'

                    firma_kod = inp_firma.value or ''
                    firma_ad = firma_options.get(firma_kod, '') if firma_kod else ''
                    if not firma_ad and firma_kod:
                        firmalar_current = get_firma_list()
                        for f in firmalar_current:
                            if f['kod'] == firma_kod:
                                firma_ad = f['ad']
                                break

                    data = {
                        'tarih': inp_tarih.value,
                        'tur': inp_tur.value,
                        'kategori': inp_kategori.value or '',
                        'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        'tutar': t,
                        'kdv_orani': ko,
                        'kdv_tutar': kdv,
                        'toplam': toplam,
                        'odeme_sekli': odeme_sekli,
                        'firma_kod': firma_kod,
                        'firma_ad': firma_ad,
                        'odeme_durumu': odeme_durumu,
                        'vade_tarih': inp_vade.value if durum == 'ODENMEDI' else '',
                    }

                    try:
                        if is_edit:
                            update_gelir_gider(edit_row['id'], data)
                            notify_ok('Kayıt güncellendi')
                        else:
                            gg_id = add_gelir_gider(data)

                            # Odenen > 0 ise kasa kaydi olustur (kismi veya tam)
                            if odenen > 0.001:
                                kasa_tur = 'GELIR' if inp_tur.value == 'GELIR' else 'GIDER'
                                kat = inp_kategori.value or ''
                                kasa_aciklama = f'{kat}'
                                if data['aciklama']:
                                    kasa_aciklama += f': {data["aciklama"]}'
                                if banka_val:
                                    kasa_aciklama += f' ({banka_val})'
                                if odeme_durumu == 'KISMI':
                                    kasa_aciklama += f' [Kismi ödeme: {odenen:.2f} / {toplam:.2f}]'
                                add_kasa({
                                    'tarih': inp_tarih.value,
                                    'firma_kod': firma_kod,
                                    'firma_ad': firma_ad,
                                    'tur': kasa_tur,
                                    'tutar': odenen,
                                    'odeme_sekli': odeme_sekli,
                                    'aciklama': kasa_aciklama,
                                    'gelir_gider_id': gg_id,
                                    'banka': banka_val,
                                })

                            if odeme_durumu == 'KISMI':
                                notify_ok(f'Kayıt eklendi (Kısmi ödeme - {fmt_tr(toplam-odenen)} TL borç)')
                            elif odeme_durumu == 'ODENMEDI':
                                notify_ok('Kayıt eklendi (Ödenmedi - Cari borç)')
                            else:
                                notify_ok('Kayıt eklendi')

                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def do_delete(rec_id):
        def confirmed():
            try:
                delete_gelir_gider(rec_id)
                notify_ok('Kayıt silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu kaydı silmek istediğinize emin misiniz?', confirmed)

    def on_donem_change(yil, ay):
        state['yil'] = yil
        state['ay'] = ay
        load_data()

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        ozet = get_gelir_gider_ozet(yil=state['yil'], ay=state['ay'])

        with ui.card().classes('w-full q-pa-xs q-mb-xs'):
            net_color = 'positive' if ozet['net'] >= 0 else 'negative'
            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                search_input = ui.input(
                    placeholder='Ara (kategori, açıklama)...',
                    on_change=lambda e: (setattr(table_ref, 'rows', do_filter(e.value)), table_ref.update()),
                ).props('outlined dense clearable').classes('w-64')
                donem_secici(on_donem_change, include_all=True)
                with ui.element('q-chip').props('color="green-2" text-color="green-9" icon="trending_up" dense'):
                    lbl_gelir = ui.label(f'Gelir: {fmt_para(ozet["gelir"])} TL').classes('text-weight-medium')
                with ui.element('q-chip').props('color="red-2" text-color="red-9" icon="trending_down" dense'):
                    lbl_gider = ui.label(f'Gider: {fmt_para(ozet["gider"])} TL').classes('text-weight-medium')
                with ui.element('q-chip').props(f'color="{net_color}" text-color="white" icon="account_balance" dense'):
                    lbl_net = ui.label(f'Net: {fmt_para(ozet["net"])} TL').classes('text-weight-bold')
                ui.space()

                def _open_pdf(pdf_bytes, filename):
                    preview_url = save_pdf_preview(pdf_bytes, filename)
                    ui.run_javascript(f"window.open('{preview_url}', '_blank')")

                def _pdf_gelir_gider():
                    try:
                        rows_src = table_ref.rows if table_ref and table_ref.rows else all_rows
                        headers = ['Tarih', 'Tür', 'Kategori', 'Cari', 'Açıklama', 'Toplam', 'Durum', 'Ödeme']

                        def _durum_txt(d):
                            return {'ODENDI': 'Ödendi', 'KISMI': 'Kısmi', 'ODENMEDI': 'Ödenmedi'}.get(d, d or '')

                        def _tur_txt(t):
                            return 'Gelir' if t == 'GELIR' else 'Gider'

                        data_rows = [
                            [
                                r.get('tarih', '') or '',
                                _tur_txt(r.get('tur', '')),
                                r.get('kategori', '') or '',
                                r.get('firma_ad', '') or '',
                                r.get('aciklama', '') or '',
                                f"{float(r.get('toplam', 0) or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                                _durum_txt(r.get('odeme_durumu', '')),
                                r.get('odeme_sekli', '') or '',
                            ]
                            for r in rows_src
                        ]
                        from datetime import datetime as _dt
                        baslik = f"Gelir / Gider Raporu - {_dt.now().strftime('%d.%m.%Y')}"
                        _open_pdf(generate_table_pdf(baslik, headers, data_rows), 'gelir_gider_raporu.pdf')
                    except Exception as e:
                        notify_err(f'PDF hatası: {e}')

                ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_gelir_gider).props('dense')
                ui.button('Yeni Kayıt', icon='add', color='primary', on_click=lambda: open_dialog()).props('dense')

        # Table
        table_ref = ui.table(
            columns=columns, rows=all_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full').style('--table-extra-rows: 2;')
        table_ref.props('flat bordered dense')

        table_ref.add_slot('body-cell-tarih', TARIH_SLOT)
        table_ref.add_slot('body-cell-toplam', PARA_SLOT)

        table_ref.add_slot('body-cell-tur', r'''
            <q-td :props="props">
                <q-chip dense :color="props.value === 'GELIR' ? 'positive' : 'negative'" text-color="white" size="sm">
                    {{ props.value === 'GELIR' ? 'Gelir' : 'Gider' }}
                </q-chip>
            </q-td>
        ''')

        # Kategori - Nakliye/Ardiye one cikan
        table_ref.add_slot('body-cell-kategori', r'''
            <q-td :props="props">
                <q-chip v-if="props.value === 'Nakliye'" dense color="orange-7" text-color="white" size="sm" icon="local_shipping">
                    Nakliye
                </q-chip>
                <q-chip v-else-if="props.value === 'Ardiye'" dense color="purple-6" text-color="white" size="sm" icon="warehouse">
                    Ardiye
                </q-chip>
                <span v-else>{{ props.value }}</span>
            </q-td>
        ''')

        # Firma / Cari adi
        table_ref.add_slot('body-cell-firma_ad', r'''
            <q-td :props="props">
                <span v-if="props.value" class="text-weight-medium text-indigo-8">{{ props.value }}</span>
                <span v-else class="text-grey-5">-</span>
            </q-td>
        ''')

        # Odeme durumu
        table_ref.add_slot('body-cell-odeme_durumu', r'''
            <q-td :props="props">
                <q-chip v-if="props.value === 'ODENMEDI'" dense color="red-7" text-color="white" size="sm" icon="schedule">
                    Ödenmedi
                </q-chip>
                <q-chip v-else-if="props.value === 'KISMI'" dense color="orange-8" text-color="white" size="sm" icon="hourglass_bottom">
                    Kısmi
                </q-chip>
                <q-chip v-else dense color="green-7" text-color="white" size="sm" icon="check">
                    Ödendi
                </q-chip>
            </q-td>
        ''')

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

        table_ref.on('edit', lambda e: open_dialog(edit_row=e.args))
        table_ref.on('delete', lambda e: do_delete(e.args['id']))
