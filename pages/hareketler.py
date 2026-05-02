"""ALSE Plastik Hammadde - Alis/Satis Hareketleri Sayfasi"""
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, PARA_SLOT, MIKTAR_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog, normalize_search, donem_secici, segment_group
)
from services.kasa_service import get_hareketler, add_hareket, update_hareket, delete_hareket
from services.cari_service import get_firma_list, add_firma, generate_firma_kod, get_firma_risk_durumu
from services.stok_service import get_urun_list, add_urun, generate_urun_kod


@ui.page('/hareketler')
def hareketler_page():
    if not create_layout(active_path='/hareketler', page_title='Hareketler'):
        return

    ui.add_css('''
    .hrk-alis { background: #eff6ff !important; }
    .hrk-satis { background: #f0fdf4 !important; }
    .hrk-tahsilat { background: #fefce8 !important; }
    .hrk-odeme { background: #fef2f2 !important; }
    tr:hover .hrk-alis { background: #dbeafe !important; }
    tr:hover .hrk-satis { background: #dcfce7 !important; }
    tr:hover .hrk-tahsilat { background: #fef9c3 !important; }
    tr:hover .hrk-odeme { background: #fee2e2 !important; }
    .hrk-table td { border-right: 1px solid #e8edf2; }
    .hrk-table td:last-child { border-right: none; }
    .hrk-table th { border-right: 1px solid rgba(255,255,255,0.15); text-align: center !important; }
    .hrk-table th:last-child { border-right: none; }
    ''')

    table_ref = None
    all_rows = []
    state = {'yil': None, 'ay': None}

    columns = [
        {'name': 'tarih', 'label': 'TARİH', 'field': 'tarih', 'align': 'center', 'sortable': True},
        {'name': 'belge_no', 'label': 'BELGE NO', 'field': 'belge_no', 'align': 'left', 'sortable': True},
        {'name': 'firma_ad', 'label': 'FİRMA', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
        {'name': 'tur', 'label': 'TÜR', 'field': 'tur', 'align': 'center', 'sortable': True},
        {'name': 'urun_ad', 'label': 'ÜRÜN', 'field': 'urun_ad', 'align': 'left', 'sortable': True},
        {'name': 'miktar', 'label': 'MİKTAR', 'field': 'miktar', 'align': 'right', 'sortable': True},
        {'name': 'birim_fiyat', 'label': 'BİRİM FİYAT', 'field': 'birim_fiyat', 'align': 'right', 'sortable': True},
        {'name': 'toplam', 'label': 'TOPLAM', 'field': 'toplam', 'align': 'right', 'sortable': True},
        {'name': 'kdvli_toplam', 'label': 'KDV\'Lİ TOPLAM', 'field': 'kdvli_toplam', 'align': 'right', 'sortable': True},
        {'name': 'tevkifat_orani', 'label': 'TEVKİFAT', 'field': 'tevkifat_orani', 'align': 'center', 'sortable': True},
        {'name': 'aciklama', 'label': 'AÇIKLAMA', 'field': 'aciklama', 'align': 'left', 'sortable': False},
        {'name': 'actions', 'label': 'İŞLEMLER', 'field': 'actions', 'align': 'center', 'sortable': False},
    ]

    search_text = {'value': ''}
    tur_filter = {'value': None}

    def apply_filters():
        rows = all_rows
        q = search_text['value']
        if q:
            qn = normalize_search(q)
            rows = [r for r in rows if
                    qn in normalize_search(r.get('firma_ad', '')) or
                    qn in normalize_search(r.get('urun_ad', '')) or
                    qn in normalize_search(r.get('tur', ''))]
        if tur_filter['value']:
            rows = [r for r in rows if r.get('tur') == tur_filter['value']]
        if table_ref:
            table_ref.rows = rows
            table_ref.update()

    def load_data():
        nonlocal all_rows
        all_rows = get_hareketler(yil=None, ay=None)
        apply_filters()

    def hesapla(miktar, birim_fiyat, kdv_orani, tevkifat_str='0'):
        m = float(miktar or 0)
        bf = float(birim_fiyat or 0)
        ko = float(kdv_orani or 0)
        matrah = m * bf
        kdv = matrah * ko / 100
        tevkifat_pay = 0
        if tevkifat_str and tevkifat_str != '0':
            parts = str(tevkifat_str).split('/')
            if len(parts) == 2:
                try:
                    tevkifat_pay = int(parts[0])
                except ValueError:
                    pass
        tevkifat_tutar = kdv * tevkifat_pay / 10
        odenecek_kdv = kdv - tevkifat_tutar
        kdvli_toplam = matrah + odenecek_kdv
        return matrah, kdv, tevkifat_tutar, odenecek_kdv, kdvli_toplam

    # --- Mini firma ekleme dialogu ---
    def open_mini_firma_dialog(firma_select):
        with ui.dialog() as mini_dlg, ui.card().classes('alse-dialog').style('min-width: 400px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('business')
                ui.label('Yeni Firma Ekle').classes('dialog-title')
            auto_kod = generate_firma_kod()
            ui.input('Firma Kodu', value=auto_kod).props('outlined dense readonly').classes('w-full q-mt-sm')
            inp_ad = ui.input('Firma Adı').props('outlined dense').classes('w-full')
            inp_tel = ui.input('Telefon').props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=mini_dlg.close).props('flat color=grey')

                def save_firma():
                    kod = auto_kod
                    ad = inp_ad.value.strip() if inp_ad.value else ''
                    if not ad:
                        notify_err('Firma adi zorunlu')
                        return
                    try:
                        add_firma({'kod': kod, 'ad': ad, 'tel': inp_tel.value.strip() if inp_tel.value else ''})
                        notify_ok('Firma eklendi')
                        mini_dlg.close()
                        # Firma select'i guncelle
                        firmalar = get_firma_list()
                        new_opts = {f['kod']: f['ad'] for f in firmalar}
                        firma_select.options = new_opts
                        firma_select.value = kod
                        firma_select.update()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save_firma).props('unelevated')
        mini_dlg.open()

    # --- Mini urun ekleme dialogu ---
    def open_mini_urun_dialog(urun_select):
        with ui.dialog() as mini_dlg, ui.card().classes('alse-dialog').style('min-width: 400px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('inventory_2')
                ui.label('Yeni Ürün Ekle').classes('dialog-title')
            auto_kod = generate_urun_kod()
            ui.input('Urun Kodu', value=auto_kod).props('outlined dense readonly').classes('w-full q-mt-sm')
            inp_ad = ui.input('Ürün Adı').props('outlined dense').classes('w-full')
            inp_kategori = ui.input('Kategori').props('outlined dense').classes('w-full')
            inp_birim = ui.select(
                options=['KG', 'TON', 'ADET', 'METRE', 'LITRE'],
                label='Birim', value='KG'
            ).props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=mini_dlg.close).props('flat color=grey')

                def save_urun():
                    kod = auto_kod
                    ad = inp_ad.value.strip() if inp_ad.value else ''
                    if not ad:
                        notify_err('Urun adi zorunlu')
                        return
                    try:
                        add_urun({
                            'kod': kod, 'ad': ad,
                            'kategori': inp_kategori.value.strip() if inp_kategori.value else '',
                            'birim': inp_birim.value or 'KG'
                        })
                        notify_ok('Ürün eklendi')
                        mini_dlg.close()
                        # Urun select'i guncelle
                        urunler = get_urun_list()
                        new_opts = {u['kod']: u['ad'] for u in urunler}
                        urun_select.options = new_opts
                        urun_select.value = kod
                        urun_select.update()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save_urun).props('unelevated')
        mini_dlg.open()

    # --- Hareket ekleme/duzenleme dialogu ---
    def open_hareket_dialog(edit_row=None):
        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}
        urunler = get_urun_list()
        urun_options = {u['kod']: u['ad'] for u in urunler}

        is_edit = edit_row is not None
        title = 'İşlem Düzenle' if is_edit else 'Yeni İşlem'

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 800px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('drive_file_rename_outline' if is_edit else 'add_circle_outline')
                ui.label(title).classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm').style('background:#f3f4f6;padding:16px;border-radius:8px;'):
                # Tarih
                inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense label-color=cyan-8').classes('w-full')
                with inp_tarih.add_slot('append'):
                    icon_t = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_t:
                        dp = ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu_t.close()))
                    icon_t.on('click', menu_t.open)

                # Irsaliye / Fatura No
                inp_belge = ui.input('İrsaliye/Fatura No').classes('w-full').props('outlined dense label-color=cyan-8')

                with ui.row().classes('w-full gap-md'):
                    # Tur
                    inp_tur = ui.select(
                        options={'ALIS': 'Alış', 'SATIS': 'Satış'},
                        label='Tür', value='ALIS'
                    ).props('outlined dense label-color=cyan-8').classes('col')

                    # KDV Oranı
                    inp_kdv = ui.select(
                        options={0: '%0', 1: '%1', 8: '%8', 10: '%10', 18: '%18', 20: '%20'},
                        label='KDV Oranı', value=20
                    ).props('outlined dense label-color=cyan-8').classes('col')

                    # Tevkifat Oranı
                    inp_tevkifat = ui.select(
                        options={'0': 'Yok', '2/10': '2/10', '5/10': '5/10', '7/10': '7/10', '9/10': '9/10'},
                        label='Tevkifat', value='0'
                    ).props('outlined dense label-color=cyan-8').classes('col')

                # Firma secimi + Yeni firma ekleme butonu
                with ui.row().classes('w-full items-center gap-1'):
                    inp_firma = ui.select(
                        options=firma_options, label='Firma', with_input=True
                    ).props('outlined dense label-color=cyan-8').classes('col')
                    ui.button(icon='add', on_click=lambda: open_mini_firma_dialog(inp_firma)).props(
                        'round dense flat color=primary').tooltip('Yeni Firma Ekle')

                # Risk limiti uyari alani
                risk_container = ui.element('div').classes('w-full')
                risk_container.set_visibility(False)

                def check_risk():
                    firma_kod = inp_firma.value
                    tur = inp_tur.value
                    risk_container.clear()
                    if not firma_kod or tur != 'SATIS':
                        risk_container.set_visibility(False)
                        return
                    try:
                        durum = get_firma_risk_durumu(firma_kod)
                    except Exception:
                        risk_container.set_visibility(False)
                        return
                    if durum['risk_limiti'] == 0:
                        risk_container.set_visibility(False)
                        return
                    if durum['limit_asimi']:
                        with risk_container:
                            bakiye_str = f"{durum['bakiye']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            limit_str = f"{durum['risk_limiti']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            ui.chip(
                                f"Risk Limiti Aşıldı! Bakiye: {bakiye_str} TL / Limit: {limit_str} TL",
                                icon='warning', color='red'
                            ).props('text-color=white dense')
                        risk_container.set_visibility(True)
                    elif durum['risk_yuzdesi'] >= 80:
                        with risk_container:
                            ui.chip(
                                f"Risk Limiti Uyarısı! %{durum['risk_yuzdesi']} kullanım",
                                icon='info', color='orange'
                            ).props('text-color=white dense')
                        risk_container.set_visibility(True)
                    else:
                        risk_container.set_visibility(False)

                inp_firma.on_value_change(lambda _: check_risk())
                inp_tur.on_value_change(lambda _: check_risk())

                # Ürün secimi + Yeni ürün ekleme butonu
                with ui.row().classes('w-full items-center gap-1'):
                    inp_urun = ui.select(
                        options=urun_options, label='Ürün', with_input=True
                    ).props('outlined dense label-color=cyan-8').classes('col')
                    ui.button(icon='add', on_click=lambda: open_mini_urun_dialog(inp_urun)).props(
                        'round dense flat color=primary').tooltip('Yeni Ürün Ekle')

                with ui.row().classes('w-full gap-md'):
                    inp_miktar = ui.number(label='Miktar', value=0, format='%.2f').props('outlined dense label-color=cyan-8 type=text').classes('col')
                    inp_birim_fiyat = ui.number(label='Birim Fiyat', value=0, format='%.2f').props('outlined dense label-color=cyan-8 type=text').classes('col')

                inp_aciklama = ui.input('Açıklama').props('outlined dense label-color=cyan-8').classes('w-full')

                # Hesaplama alani
                ui.separator()
                with ui.row().classes('w-full gap-md items-center'):
                    lbl_toplam = ui.label('Matrah: 0,00 TL').classes('text-subtitle2 col')
                    lbl_kdv_tutar = ui.label('KDV: 0,00 TL').classes('text-subtitle2 col')
                    lbl_tevkifat = ui.label('Tevkifat: 0,00 TL').classes('text-subtitle2 col text-orange-8')
                    lbl_kdvli = ui.label('Fatura Toplam: 0,00 TL').classes('text-subtitle2 text-weight-bold col text-primary')

                def fmt_tr(val):
                    s = f"{abs(val):,.2f}"
                    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                    return s

                def recalc():
                    matrah, kdv, tevk_tutar, odenecek_kdv, kdvli_toplam = hesapla(
                        inp_miktar.value, inp_birim_fiyat.value, inp_kdv.value, inp_tevkifat.value
                    )
                    lbl_toplam.set_text(f'Matrah: {fmt_tr(matrah)} TL')
                    lbl_kdv_tutar.set_text(f'KDV: {fmt_tr(kdv)} TL')
                    lbl_tevkifat.set_text(f'Tevkifat: {fmt_tr(tevk_tutar)} TL')
                    lbl_kdvli.set_text(f'Fatura Toplam: {fmt_tr(kdvli_toplam)} TL')

                inp_miktar.on_value_change(lambda _: recalc())
                inp_birim_fiyat.on_value_change(lambda _: recalc())
                inp_kdv.on_value_change(lambda _: recalc())
                inp_tevkifat.on_value_change(lambda _: recalc())

                ui.separator()

            # Duzenleme modunda mevcut degerleri doldur
            if is_edit:
                inp_tarih.value = edit_row.get('tarih', '')
                inp_tur.value = edit_row.get('tur', 'ALIS')
                inp_firma.value = edit_row.get('firma_kod', '')
                inp_urun.value = edit_row.get('urun_kod', '')
                inp_miktar.value = edit_row.get('miktar', 0)
                inp_birim_fiyat.value = edit_row.get('birim_fiyat', 0)
                inp_kdv.value = int(edit_row.get('kdv_orani', 20))
                inp_tevkifat.value = edit_row.get('tevkifat_orani', '0') or '0'
                inp_aciklama.value = edit_row.get('aciklama', '')
                inp_belge.value = edit_row.get('belge_no', '')
                recalc()
                check_risk()

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    if not inp_firma.value:
                        notify_err('Firma seçmelisiniz')
                        return
                    if not inp_urun.value:
                        notify_err('Ürün seçmelisiniz')
                        return
                    m = float(inp_miktar.value or 0)
                    bf = float(inp_birim_fiyat.value or 0)
                    if m <= 0:
                        notify_err('Miktar 0\'dan büyük olmalı')
                        return
                    if bf <= 0:
                        notify_err('Birim fiyat 0\'dan büyük olmalı')
                        return

                    firma_kod = inp_firma.value
                    firma_ad = firma_options.get(firma_kod, '')
                    # Firma listesi guncellenmis olabilir
                    if not firma_ad:
                        fresh_firmalar = get_firma_list()
                        for f in fresh_firmalar:
                            if f['kod'] == firma_kod:
                                firma_ad = f['ad']
                                break

                    urun_kod = inp_urun.value
                    urun_ad = urun_options.get(urun_kod, '')
                    if not urun_ad:
                        fresh_urunler = get_urun_list()
                        for u in fresh_urunler:
                            if u['kod'] == urun_kod:
                                urun_ad = u['ad']
                                break

                    matrah, kdv, tevk_tutar, odenecek_kdv, kdvli_toplam = hesapla(
                        m, bf, inp_kdv.value, inp_tevkifat.value
                    )

                    data = {
                        'tarih': inp_tarih.value,
                        'firma_kod': firma_kod,
                        'firma_ad': firma_ad,
                        'tur': inp_tur.value,
                        'urun_kod': urun_kod,
                        'urun_ad': urun_ad,
                        'miktar': m,
                        'birim_fiyat': bf,
                        'toplam': matrah,
                        'kdv_orani': float(inp_kdv.value or 0),
                        'kdv_tutar': kdv,
                        'kdvli_toplam': kdvli_toplam,
                        'tevkifat_orani': inp_tevkifat.value or '0',
                        'tevkifat_tutar': tevk_tutar,
                        'tevkifatsiz_kdv': odenecek_kdv,
                        'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        'belge_no': inp_belge.value.strip() if inp_belge.value else '',
                    }

                    try:
                        if is_edit:
                            update_hareket(edit_row['id'], data)
                            notify_ok('Hareket güncellendi')
                        else:
                            add_hareket(data)
                            notify_ok('Hareket eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def do_edit(row):
        open_hareket_dialog(edit_row=row)

    def do_delete(row_id):
        def confirmed():
            try:
                delete_hareket(row_id)
                notify_ok('Hareket silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu hareketi silmek istediğinize emin misiniz?', confirmed)

    # --- Slot template'leri ---
    # Satir arka plan rengi: tur'e gore cok hafif tint
    _rcls = "props.row.tur==='ALIS'?'hrk-alis':props.row.tur==='SATIS'?'hrk-satis':props.row.tur==='TAHSILAT'?'hrk-tahsilat':props.row.tur==='ODEME'?'hrk-odeme':''"

    _tarih_slot = r'''
        <q-td :props="props" :class="%s">
            {{ props.value ? props.value.split('-').reverse().join('.') : '' }}
        </q-td>
    ''' % _rcls

    tur_slot = r'''
        <q-td :props="props" :class="%s">
            <span style="font-weight:600;"
                :style="props.value === 'ALIS' ? 'color:#1d4ed8;' :
                        props.value === 'SATIS' ? 'color:#15803d;' :
                        props.value === 'TAHSILAT' ? 'color:#b45309;' :
                        props.value === 'ODEME' ? 'color:#b91c1c;' : 'color:#64748b;'">
                {{ props.value === 'ALIS' ? 'Alış' :
                   props.value === 'SATIS' ? 'Satış' :
                   props.value === 'TAHSILAT' ? 'Tahsilat' :
                   props.value === 'ODEME' ? 'Ödeme' : props.value }}
            </span>
        </q-td>
    ''' % _rcls

    _para_slot = r'''
        <q-td :props="props" :class="%s">
            {{ props.value != null && props.value !== 0
                ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                : '' }}
        </q-td>
    ''' % _rcls

    miktar_slot = r'''
        <q-td :props="props" :class="%s">
            {{ props.value != null && props.value !== 0 ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}
        </q-td>
    ''' % _rcls

    _default_slot = r'''
        <q-td :props="props" :class="%s">
            {{ props.value }}
        </q-td>
    ''' % _rcls

    actions_slot = r'''
        <q-td :props="props" :class="%s">
            <template v-if="props.row.source === 'STOK' || !props.row.source">
                <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                    @click="$parent.$emit('edit', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete_outline" color="negative" size="sm"
                    @click="$parent.$emit('delete', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
            </template>
            <template v-else>
                <q-chip dense color="grey-4" text-color="grey-9" size="sm">Kasa</q-chip>
            </template>
        </q-td>
    ''' % _rcls

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_hareketler(yil=None, ay=None)

        def on_tur_change(new_tur):
            tur_filter['value'] = new_tur
            apply_filters()

        def on_search_change(e):
            search_text['value'] = e.value or ''
            apply_filters()

        with ui.row().classes('w-full items-center gap-2 q-mb-xs'):
            search_input = ui.input(
                placeholder='Ara (firma, ürün, tür)...',
                on_change=on_search_change,
            ).props('outlined dense clearable').classes('w-64')
            ui.element('div').style('width:8px')

            segment_group(
                buttons=[
                    ('ALIS', 'Alış', '#1d4ed8'),
                    ('SATIS', 'Satış', '#15803d'),
                    ('TAHSILAT', 'Tahsilat', '#b45309'),
                    ('ODEME', 'Ödeme', '#b91c1c'),
                ],
                on_change=on_tur_change,
                active=None,
            )

            ui.space()
            ui.button('Yeni İşlem', icon='add', color='primary',
                      on_click=lambda: open_hareket_dialog())

        # Tablo
        table_ref = ui.table(
            columns=columns, rows=all_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full hrk-table').style('--table-extra-rows: 2;')
        table_ref.props('flat bordered dense')

        # Slot'lar
        table_ref.add_slot('body-cell-tarih', _tarih_slot)
        table_ref.add_slot('body-cell-tur', tur_slot)
        table_ref.add_slot('body-cell-miktar', miktar_slot)
        table_ref.add_slot('body-cell-birim_fiyat', _para_slot)
        table_ref.add_slot('body-cell-toplam', _para_slot)
        table_ref.add_slot('body-cell-kdvli_toplam', _para_slot)
        table_ref.add_slot('body-cell-belge_no', _default_slot)
        table_ref.add_slot('body-cell-urun_ad', _default_slot)
        table_ref.add_slot('body-cell-firma_ad', _default_slot)
        table_ref.add_slot('body-cell-aciklama', _default_slot)
        table_ref.add_slot('body-cell-birim', _default_slot)
        table_ref.add_slot('body-cell-kdv_orani', _default_slot)
        table_ref.add_slot('body-cell-tevkifat_orani', r'''
            <q-td :props="props" :class="''' + _rcls + r'''">
                <q-badge v-if="props.value && props.value !== '0'" color="orange-8" text-color="white" dense>
                    {{ props.value }}
                </q-badge>
                <span v-else class="text-grey-5">-</span>
            </q-td>
        ''')
        table_ref.add_slot('body-cell-actions', actions_slot)

        table_ref.on('edit', lambda e: do_edit(e.args))
        table_ref.on('delete', lambda e: do_delete(e.args['id']))



