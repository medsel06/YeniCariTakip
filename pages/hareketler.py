"""ALSE Plastik Hammadde - Alis/Satis Hareketleri Sayfasi"""
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, PARA_SLOT, MIKTAR_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog, normalize_search, donem_secici, segment_group,
    fmt_para, fmt_miktar
)
from services.kasa_service import (
    get_hareketler, add_hareket, update_hareket, delete_hareket,
    get_kasa_by_id, add_kasa, update_kasa, delete_kasa, get_kasa_silme_etkisi,
)
from services.cari_service import get_firma_list, add_firma, generate_firma_kod, get_firma_risk_durumu
from services.stok_service import get_urun_list, add_urun, generate_urun_kod
from services.banka_service import list_banka_hesaplari


@ui.page('/hareketler')
def hareketler_page():
    if not create_layout(active_path='/hareketler', page_title='Hareketler'):
        return

    ui.add_css('''
    /* Zebra: Odeme Takibi ile ayni (global .q-table zebra: odd #fff / even #f1f5f9). Tur-bazli renkler kaldirildi. */
    /* Tarihsiz kayit uyarisi zebra'yi ezer (rapora girmiyor) */
    .hrk-table tbody tr td.hrk-tarihsiz { background: #fee2e2 !important; color: #7f1d1d !important; }
    .hrk-table tbody tr:hover td.hrk-tarihsiz { background: #fecaca !important; }
    .hrk-table td { border-right: 1px solid #e8edf2; }
    .hrk-table td:last-child { border-right: none; }
    .hrk-table th { border-right: 1px solid rgba(255,255,255,0.15); text-align: center !important; }
    .hrk-table th:last-child { border-right: none; }
    /* Rakam sutunlari: orijinal font + tabular figures (hizali) + biraz kucuk */
    .hrk-table .num-mono { font-variant-numeric: tabular-nums; font-size: 12px; }
    /* Satırların tıklanabilir olduğunu belirten pointer */
    .hrk-table tbody tr { cursor: pointer; }
    /* Detay modal bilgi satirlari: cerceveli, zebra desen */
    .modal-info { border: 1px solid #e8edf2; border-radius: 10px; overflow: hidden; }
    .modal-info .info-row { border-bottom: 1px solid #eef2f7; }
    .modal-info .info-row:last-child { border-bottom: none; }
    .modal-info .info-row:nth-child(odd) { background: #ffffff; }
    .modal-info .info-row:nth-child(even) { background: #f8fafc; }
    .modal-info .info-row:hover { background: #eef4fb; }
    ''')

    table_ref = None
    all_rows = []
    state = {'yil': None, 'ay': None}

    columns = [
        {'name': 'tarih', 'label': 'TARİH', 'field': 'tarih', 'align': 'center', 'sortable': True},
        {'name': 'belge_no', 'label': 'BELGE NO', 'field': 'belge_no', 'align': 'left', 'sortable': True},
        {'name': 'firma_ad', 'label': 'FİRMA', 'field': 'firma_ad', 'align': 'left', 'sortable': True,
         'style': 'width:170px;max-width:170px', 'headerStyle': 'width:170px'},
        {'name': 'tur', 'label': 'TÜR', 'field': 'tur', 'align': 'center', 'sortable': True},
        {'name': 'urun_ad', 'label': 'ÜRÜN', 'field': 'urun_ad', 'align': 'left', 'sortable': True,
         'style': 'width:150px;max-width:150px', 'headerStyle': 'width:150px'},
        {'name': 'miktar', 'label': 'MİKTAR', 'field': 'miktar', 'align': 'right', 'sortable': True},
        {'name': 'birim_fiyat', 'label': 'BİRİM FİYAT', 'field': 'birim_fiyat', 'align': 'right', 'sortable': True},
        {'name': 'toplam', 'label': 'TOPLAM', 'field': 'toplam', 'align': 'right', 'sortable': True},
        {'name': 'kdvli_toplam', 'label': 'KDV\'Lİ TOPLAM', 'field': 'kdvli_toplam', 'align': 'right', 'sortable': True},
        {'name': 'tevkifat_orani', 'label': 'TEVKİFAT', 'field': 'tevkifat_orani', 'align': 'center', 'sortable': True},
        {'name': 'aciklama', 'label': 'AÇIKLAMA', 'field': 'aciklama', 'align': 'left', 'sortable': False,
         'style': 'width:200px;max-width:200px', 'headerStyle': 'width:200px'},
        {'name': 'actions', 'label': 'İŞLEMLER', 'field': 'actions', 'align': 'left', 'sortable': False},
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

                # --- Vade (opsiyonel): bos=pesin. Dolu ise Odeme Takibi'nde "vadesi yaklasan"
                # olarak gorunur. Cariye etkisi YOK (tutar tek kez yazilir). ---
                inp_vade = ui.input('Vade Tarihi (opsiyonel — boş = peşin)').props(
                    'outlined dense label-color=cyan-8 clearable').classes('w-full')
                with inp_vade.add_slot('append'):
                    icon_vd = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_vd:
                        ui.date(on_change=lambda e: (inp_vade.set_value(e.value), menu_vd.close()))
                    icon_vd.on('click', menu_vd.open)

                def _set_vade_gun(gun):
                    from datetime import datetime as _dt, timedelta as _td
                    base = inp_tarih.value or date.today().isoformat()
                    try:
                        b = _dt.strptime(str(base)[:10], '%Y-%m-%d').date()
                    except ValueError:
                        b = date.today()
                    inp_vade.set_value((b + _td(days=gun)).isoformat())

                with ui.row().classes('w-full gap-1 items-center q-mb-xs'):
                    ui.label('Hızlı vade:').classes('text-caption text-grey-7')
                    ui.button('Peşin', on_click=lambda: inp_vade.set_value('')).props('dense flat no-caps size=sm color=grey-7')
                    ui.button('+7 gün', on_click=lambda: _set_vade_gun(7)).props('dense flat no-caps size=sm')
                    ui.button('+15 gün', on_click=lambda: _set_vade_gun(15)).props('dense flat no-caps size=sm')
                    ui.button('+30 gün', on_click=lambda: _set_vade_gun(30)).props('dense flat no-caps size=sm')

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
                inp_vade.value = edit_row.get('vade_tarih', '') or ''
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
                        'vade_tarih': (inp_vade.value or '').strip(),
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

    # --- KASA edit/delete/yeni dialoglari ---
    def open_kasa_dialog(edit_row=None, default_tur=None):
        """Kasa kaydi (TAHSILAT/ODEME) ekle veya duzenle.
        edit_row: dict (row['kasa_id'] dolu olmali) — duzenleme modu
        default_tur: 'GELIR' (Tahsilat) veya 'GIDER' (Odeme) — yeni kayit modu
        """
        is_edit = edit_row is not None
        if is_edit:
            kasa_kaynak = edit_row.get('kasa_kaynak')
            # Bagli kayit ise — kaynaktan duzenleme uyarisi
            if kasa_kaynak == 'gelir_gider':
                notify_err('Bu kayit Gelir-Gider modulunden uretilmis. Lütfen Gelir/Gider sayfasından düzenleyin.')
                ui.navigate.to('/gelir-gider')
                return
            if kasa_kaynak == 'cek':
                notify_err('Bu kayit bir cek hareketinden gelmistir. Lütfen Çekler sayfasından düzenleyin.')
                ui.navigate.to('/cekler')
                return
            # Serbest kasa — DB'den tam kayit cek
            kasa_rec = get_kasa_by_id(edit_row.get('kasa_id'))
            if not kasa_rec:
                notify_err('Kayit bulunamadi')
                return
            tur_default = kasa_rec.get('tur', 'GELIR')
            tarih_default = kasa_rec.get('tarih') or date.today().strftime('%Y-%m-%d')
            firma_kod_default = kasa_rec.get('firma_kod', '')
            firma_ad_default = kasa_rec.get('firma_ad', '')
            tutar_default = float(kasa_rec.get('tutar') or 0)
            odeme_default = kasa_rec.get('odeme_sekli', 'NAKIT')
            banka_default = kasa_rec.get('banka', '')
            banka_hesap_id_default = kasa_rec.get('banka_hesap_id')
            kategori_default = kasa_rec.get('kategori', '')
            aciklama_default = kasa_rec.get('aciklama', '')
        else:
            tur_default = default_tur or 'GELIR'
            tarih_default = date.today().strftime('%Y-%m-%d')
            firma_kod_default = ''
            firma_ad_default = ''
            tutar_default = 0.0
            odeme_default = 'NAKIT'
            banka_default = ''
            banka_hesap_id_default = None
            kategori_default = ''
            aciklama_default = ''

        firmalar = get_firma_list()
        firma_opts = {f['kod']: f"{f['ad']}" for f in firmalar}
        firma_opts[''] = '(Firma yok — serbest kayit)'

        # Banka secenekleri (Bankalar sayfasinda tanimli aktif hesaplar) — id ile eslesir
        banka_opts = {'': '(Banka yok)'}
        banka_ad_by_id = {}
        for b in list_banka_hesaplari(sadece_aktif=True):
            ad = (b.get('ad') or '').strip()
            if ad:
                banka_opts[str(b['id'])] = ad
                banka_ad_by_id[str(b['id'])] = ad
        # Duzenleme: kayittaki banka_hesap_id'yi sec; yoksa eski metin banka adina gore esle
        banka_sel_default = ''
        if banka_hesap_id_default and str(banka_hesap_id_default) in banka_opts:
            banka_sel_default = str(banka_hesap_id_default)
        elif banka_default:
            for k, v in banka_ad_by_id.items():
                if v == banka_default:
                    banka_sel_default = k
                    break

        baslik = ('Tahsilat Düzenle' if tur_default == 'GELIR' else 'Ödeme Düzenle') if is_edit else \
                 ('Yeni Tahsilat' if tur_default == 'GELIR' else 'Yeni Ödeme')

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 560px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('payments' if tur_default == 'GELIR' else 'shopping_cart_checkout')
                ui.label(baslik).classes('dialog-title')

            with ui.row().classes('w-full q-mt-sm gap-2'):
                inp_tarih = ui.input('Tarih', value=tarih_default).props('outlined dense type=date').classes('col')
                inp_tur = ui.select(
                    options={'GELIR': 'Tahsilat', 'GIDER': 'Ödeme'},
                    value=tur_default, label='Tür'
                ).props('outlined dense').classes('col')

            inp_firma = ui.select(
                options=firma_opts, value=firma_kod_default if firma_kod_default in firma_opts else '',
                label='Firma', with_input=True,
            ).classes('w-full q-mt-sm').props('outlined dense')

            with ui.row().classes('w-full q-mt-sm gap-2'):
                inp_tutar = ui.number('Tutar (TL)', value=tutar_default, format='%.2f').props('outlined dense').classes('col')
                inp_odeme = ui.select(
                    options=['NAKIT', 'HAVALE', 'EFT', 'KK', 'CEK', 'DIGER'],
                    value=odeme_default if odeme_default in ['NAKIT', 'HAVALE', 'EFT', 'KK', 'CEK', 'DIGER'] else 'NAKIT',
                    label='Ödeme Şekli',
                ).props('outlined dense').classes('col')

            with ui.row().classes('w-full q-mt-sm gap-2'):
                inp_banka = ui.select(
                    options=banka_opts,
                    value=banka_sel_default,
                    label='Banka',
                ).props('outlined dense').classes('col')
                inp_kategori = ui.input('Kategori', value=kategori_default).props('outlined dense').classes('col')

            inp_aciklama = ui.input('Açıklama', value=aciklama_default).classes('w-full q-mt-sm').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih zorunlu')
                        return
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar > 0 olmalı')
                        return
                    firma_kod = inp_firma.value or ''
                    firma_ad = firma_opts.get(firma_kod, '') if firma_kod else ''
                    if firma_ad == '(Firma yok — serbest kayit)':
                        firma_ad = ''
                    data = {
                        'tarih': inp_tarih.value,
                        'firma_kod': firma_kod,
                        'firma_ad': firma_ad,
                        'tur': inp_tur.value,
                        'tutar': float(inp_tutar.value),
                        'odeme_sekli': inp_odeme.value or 'NAKIT',
                        'banka_hesap_id': int(inp_banka.value) if inp_banka.value else None,
                        'banka': banka_ad_by_id.get(inp_banka.value or '', ''),
                        'kategori': inp_kategori.value or '',
                        'aciklama': inp_aciklama.value or '',
                    }
                    try:
                        if is_edit:
                            update_kasa(edit_row.get('kasa_id'), data)
                            notify_ok('Kasa kaydı güncellendi')
                        else:
                            add_kasa(data)
                            notify_ok('Kasa kaydı eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def do_edit_kasa(row):
        open_kasa_dialog(edit_row=row)

    def do_delete_kasa(row):
        kasa_id = row.get('kasa_id')
        if not kasa_id:
            notify_err('Kasa ID bulunamadi')
            return
        impact = get_kasa_silme_etkisi(kasa_id)
        if not impact.get('ok'):
            notify_err('Kayit bulunamadi')
            return

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 520px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('warning', color='red-6')
                ui.label('Silme Onayı').classes('dialog-title')

            ui.label('Bu işlem aşağıdaki sonuçları doğuracaktır:').classes('text-body2 q-mt-sm')
            with ui.column().classes('w-full q-mt-sm gap-1'):
                for etki in impact['etkiler']:
                    ui.label(f"• {etki}").classes('text-caption')

            ui.separator().classes('q-my-sm')
            ui.label('Onaylıyor musunuz?').classes('text-weight-bold text-negative')

            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Vazgeç', on_click=dlg.close).props('flat color=grey')

                def confirm():
                    try:
                        delete_kasa(kasa_id)
                        notify_ok('Kayıt silindi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Evet, Sil', color='negative', on_click=confirm).props('unelevated')
        dlg.open()

    def _show_row_detail(row):
        """Satır detaylarını gösteren modern bir kart/modal açar."""
        tur = row.get('tur', '')
        source = row.get('source', 'STOK')
        
        # Tür-bazlı renk, başlık ve ikon atamaları (Açık Tema / Beyaz Zeminle Uyumlu)
        if tur == 'ALIS':
            bg_color = 'bg-blue-50'
            text_color = 'text-blue-800'
            border_color = 'border-blue-100'
            tur_label = 'Alış İşlemi'
            icon = 'shopping_cart'
        elif tur == 'SATIS':
            bg_color = 'bg-emerald-50'
            text_color = 'text-emerald-800'
            border_color = 'border-emerald-100'
            tur_label = 'Satış İşlemi'
            icon = 'trending_up'
        elif tur == 'TAHSILAT':
            bg_color = 'bg-amber-50'
            text_color = 'text-amber-800'
            border_color = 'border-amber-100'
            tur_label = 'Tahsilat'
            icon = 'account_balance_wallet'
        else: # ODEME
            bg_color = 'bg-rose-50'
            text_color = 'text-rose-800'
            border_color = 'border-rose-100'
            tur_label = 'Ödeme'
            icon = 'credit_card'
            
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('width: 90vw; max-width: 550px; border-radius: 12px;'):
            # 1. Üst Kısım / Header (İşlem Türüne Göre Renkli)
            with ui.row().classes(f'w-full items-center justify-between q-pa-sm rounded-lg border {bg_color} {border_color} q-mb-md'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon(icon).classes(f'text-xl {text_color}')
                    ui.label(tur_label).classes(f'text-base font-bold {text_color}')
                with ui.row().classes('items-center gap-1'):
                    belge = row.get('belge_no', '')
                    if belge:
                        ui.badge(f"Belge: {belge}", color='grey-3').props('text-color=grey-8')
                    ui.badge(f"ID: {row.get('id', '')}", color='grey-2').props('text-color=grey-7')

            # 2. Bilgi Satırları / Body
            with ui.column().classes('w-full gap-0 q-mb-md modal-info'):

                # Bilgi satırı yardımcı fonksiyonu — belirgin zebra (inline, garanti)
                _ridx = {'i': 0}
                def info_row(label, value, is_mono=False, extra_style=''):
                    if value is None or value == '':
                        value = '-'
                    bg = '#f1f5f9' if _ridx['i'] % 2 else '#ffffff'
                    _ridx['i'] += 1
                    with ui.row().classes('w-full justify-between items-center no-wrap info-row').style(f'background:{bg};padding:9px 14px;'):
                        ui.label(label).classes('uppercase').style('font-size:11px;font-weight:700;color:#64748b;letter-spacing:0.5px;')
                        ui.label(str(value)).classes(f'text-right {"num-mono" if is_mono else ""}').style('font-size:13.5px;font-weight:600;color:#1e293b;' + extra_style)

                # Cari Bilgileri
                info_row('Firma Adı', row.get('firma_ad'))
                
                # Tarih
                tarih_str = row.get('tarih', '')
                if tarih_str:
                    try:
                        dt = datetime.strptime(tarih_str, '%Y-%m-%d')
                        tarih_str = dt.strftime('%d.%m.%Y')
                    except Exception:
                        pass
                info_row('Tarih', tarih_str)
                
                # Stok İşlemleri Detayı
                if source == 'STOK':
                    info_row('Ürün Adı', row.get('urun_ad'))
                    
                    # Miktar + Birim
                    birim = row.get('birim') or 'KG'
                    miktar = row.get('miktar', 0)
                    info_row('Miktar', f"{fmt_miktar(miktar)} {birim}", is_mono=True)
                    
                    # Birim Fiyat
                    bf = row.get('birim_fiyat', 0)
                    info_row('Birim Fiyat', f"{fmt_para(bf)} TL", is_mono=True)
                    
                    # Toplam (Matrah)
                    toplam = row.get('toplam', 0)
                    info_row('Matrah (KDV Hariç)', f"{fmt_para(toplam)} TL", is_mono=True)
                    
                    # KDV
                    kdv_orani = row.get('kdv_orani', 0)
                    kdv_tutar = row.get('kdv_tutar', 0)
                    if kdv_orani > 0:
                        info_row('KDV Oranı', f"% {int(kdv_orani)}")
                        info_row('KDV Tutarı', f"{fmt_para(kdv_tutar)} TL", is_mono=True)
                    
                    # Tevkifat
                    tevkifat = row.get('tevkifat_orani', '0')
                    if tevkifat and tevkifat != '0':
                        tevkifat_tutar = row.get('tevkifat_tutar', 0)
                        info_row('Tevkifat Oranı', tevkifat)
                        info_row('Tevkifat Tutarı', f"{fmt_para(tevkifat_tutar)} TL", is_mono=True)
                    
                    # Net Toplam
                    kdvli = row.get('kdvli_toplam', 0)
                    info_row('KDV\'li Toplam', f"{fmt_para(kdvli)} TL", is_mono=True, extra_style='font-weight: 700; color: #1e293b; font-size: 15px;')
                
                # Kasa/Banka İşlemleri Detayı
                else: 
                    # Tutar
                    toplam = row.get('toplam', 0)
                    info_row('Tutar', f"{fmt_para(toplam)} TL", is_mono=True, extra_style='font-weight: 700; color: #1e293b; font-size: 15px;')
                    
                    # Ödeme Şekli & Banka Bilgisi
                    odeme = row.get('odeme_sekli', '')
                    banka = row.get('banka', '')
                    if odeme:
                        info_row('Ödeme Şekli', odeme)
                    if banka:
                        info_row('Banka / Kasa', banka)
                        
                    # Kasa Kaynak Bilgisi
                    kaynak = row.get('kasa_kaynak', '')
                    if kaynak:
                        kaynak_label = 'Serbest Kasa Kaydı'
                        if kaynak == 'gelir_gider':
                            kaynak_label = 'Gelir/Gider Modülü'
                        elif kaynak == 'cek':
                            kaynak_label = 'Çek/Senet Modülü'
                        info_row('Kaynak', kaynak_label)
                        
                # Açıklama
                info_row('Açıklama', row.get('aciklama'))

            ui.separator().classes('q-my-xs')

            # 3. Alt Kısım / Footer (İsimlendirilmiş Aksiyon Butonları)
            with ui.row().classes('w-full justify-between items-center q-mt-md'):
                ui.button('Kapat', on_click=dlg.close).props('flat color=grey')
                
                with ui.row().classes('gap-2'):
                    if source == 'STOK':
                        ui.button('Düzenle', icon='edit', 
                                  on_click=lambda: (dlg.close(), do_edit(row))) \
                            .props('unelevated no-caps color=primary dense')
                        ui.button('Sil', icon='delete', 
                                  on_click=lambda: (dlg.close(), do_delete(row.get('id')))) \
                            .props('unelevated no-caps color=negative dense')
                    else: # KASA
                        ui.button('Düzenle', icon='edit', 
                                  on_click=lambda: (dlg.close(), do_edit_kasa(row))) \
                            .props('unelevated no-caps color=primary dense')
                        ui.button('Sil', icon='delete', 
                                  on_click=lambda: (dlg.close(), do_delete_kasa(row))) \
                            .props('unelevated no-caps color=negative dense')
                            
        dlg.open()

    # --- Slot template'leri ---
    # Satir arka plan rengi: tarih bos ise kirmizi (tarihsiz uyarisi),
    # aksi halde tur'e gore cok hafif tint
    _rcls = "(!props.row.tarih)?'hrk-tarihsiz':props.row.tur==='ALIS'?'hrk-alis':props.row.tur==='SATIS'?'hrk-satis':props.row.tur==='TAHSILAT'?'hrk-tahsilat':props.row.tur==='ODEME'?'hrk-odeme':''"

    _tarih_slot = r'''
        <q-td :props="props" :class="%s">
            <span v-if="props.value" style="font-weight:700;font-size:11px;color:#334155;">{{ props.value.split('-').reverse().join('.') }}</span>
            <span v-else style="color:#7f1d1d;font-weight:700;">⚠ TARİH YOK</span>
        </q-td>
    ''' % _rcls

    tur_slot = r'''
        <q-td :props="props" :class="%s">
            <span style="display:inline-block;padding:2px 10px;border-radius:999px;font-weight:700;font-size:11px;letter-spacing:0.2px;"
                :style="props.value === 'ALIS' ? 'background:#e0e7ff;color:#4338ca;' :
                        props.value === 'SATIS' ? 'background:#dcfce7;color:#15803d;' :
                        props.value === 'TAHSILAT' ? 'background:#cffafe;color:#0e7490;' :
                        props.value === 'ODEME' ? 'background:#ffe4e6;color:#be123c;' : 'background:#f1f5f9;color:#475569;'">
                {{ props.value === 'ALIS' ? 'Alış' :
                   props.value === 'SATIS' ? 'Satış' :
                   props.value === 'TAHSILAT' ? 'Tahsilat' :
                   props.value === 'ODEME' ? 'Ödeme' : props.value }}
            </span>
        </q-td>
    ''' % _rcls

    _para_slot = r'''
        <q-td :props="props" :class="%s">
            <span class="num-mono">{{ props.value != null && props.value !== 0
                ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                : '' }}</span>
        </q-td>
    ''' % _rcls

    miktar_slot = r'''
        <q-td :props="props" :class="%s">
            <span class="num-mono">{{ props.value != null && props.value !== 0 ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}</span>
        </q-td>
    ''' % _rcls

    _default_slot = r'''
        <q-td :props="props" :class="%s">
            {{ props.value }}
        </q-td>
    ''' % _rcls

    # Daraltilmis sutun: ellipsis + sadece metin sigmazsa (esik karakter sayisi) tooltip
    def _ellipsis_slot(max_w, thr):
        return (r'''
        <q-td :props="props" :class="''' + _rcls + r'''">
            <div style="max-width:''' + str(max_w) + r'''px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {{ props.value }}
                <q-tooltip v-if="props.value && String(props.value).length > ''' + str(thr) + r'''"
                    anchor="top middle" self="bottom middle"
                    style="font-size:12.5px;max-width:360px;white-space:normal;background:#1e293b;">
                    {{ props.value }}
                </q-tooltip>
            </div>
        </q-td>''')

    _urun_slot = _ellipsis_slot(150, 18)
    _aciklama_slot = _ellipsis_slot(200, 26)
    _firma_slot = _ellipsis_slot(170, 22)

    actions_slot = r'''
        <q-td :props="props" :class="%s">
            <template v-if="props.row.source === 'STOK' || !props.row.source">
                <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete_outline" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
            </template>
            <template v-else>
                <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit_kasa', props.row)">
                    <q-tooltip>{{ props.row.kasa_kaynak === 'gelir_gider' ? 'Gelir-Gider sayfasından düzenle' :
                                  props.row.kasa_kaynak === 'cek' ? 'Çek sayfasından düzenle' :
                                  'Düzenle' }}</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete_outline" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete_kasa', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
                <q-chip dense
                    :color="props.row.kasa_kaynak === 'gelir_gider' ? 'orange-3' :
                            props.row.kasa_kaynak === 'cek' ? 'purple-3' : 'grey-3'"
                    text-color="grey-9" size="sm" class="q-ml-xs"
                    style="font-size:10px;height:18px;">
                    {{ props.row.kasa_kaynak === 'gelir_gider' ? 'GG' :
                       props.row.kasa_kaynak === 'cek' ? 'Çek' : 'Kasa' }}
                </q-chip>
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
            ui.button('TAHSİLAT', icon='account_balance_wallet', color='positive',
                      on_click=lambda: open_kasa_dialog(default_tur='GELIR')).props('unelevated dense no-caps')
            ui.button('ÖDEME', icon='credit_card', color='warning',
                      on_click=lambda: open_kasa_dialog(default_tur='GIDER')).props('unelevated dense no-caps')
            ui.button('İŞLEM', icon='receipt_long', color='primary',
                      on_click=lambda: open_hareket_dialog()).props('unelevated dense no-caps')

        # Tablo
        table_ref = ui.table(
            columns=columns, rows=all_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full hrk-table').style('--table-extra-rows: 3;')
        table_ref.props('flat bordered dense')

        # Slot'lar
        table_ref.add_slot('body-cell-tarih', _tarih_slot)
        table_ref.add_slot('body-cell-tur', tur_slot)
        table_ref.add_slot('body-cell-miktar', miktar_slot)
        table_ref.add_slot('body-cell-birim_fiyat', _para_slot)
        table_ref.add_slot('body-cell-toplam', _para_slot)
        table_ref.add_slot('body-cell-kdvli_toplam', _para_slot)
        table_ref.add_slot('body-cell-belge_no', _default_slot)
        table_ref.add_slot('body-cell-urun_ad', _urun_slot)
        table_ref.add_slot('body-cell-firma_ad', _firma_slot)
        table_ref.add_slot('body-cell-aciklama', _aciklama_slot)
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
        table_ref.on('edit_kasa', lambda e: do_edit_kasa(e.args))
        table_ref.on('delete_kasa', lambda e: do_delete_kasa(e.args))
        table_ref.on('row-click', lambda e: _show_row_detail(e.args[1]))



