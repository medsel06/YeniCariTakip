"""ALSE Plastik Hammadde - Gelir/Gider Sayfasi"""
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, fmt_para, ozet_pill, PARA_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog, normalize_search, donem_secici, donem_popover_btn,
)
from services.gelir_gider_service import (
    get_gelir_gider_list, get_gelir_gider_ozet,
    add_gelir_gider, update_gelir_gider, delete_gelir_gider,
    get_gelir_gider_rapor, kategori_ozet,
    kategori_normalize, kategori_ikon, get_kategori_kullanim, KATEGORI_IKON,
    GELIR_KATEGORILER, GIDER_KATEGORILER, ONE_CIKAN_GIDER_KATEGORILER,
)
from services.banka_service import list_banka_hesaplari
from services.kasa_service import add_kasa
from services.cari_service import get_firma_list, add_firma, generate_firma_kod
from services.pdf_service import (
    save_pdf_preview, generate_gelir_gider_kategori_pdf, generate_gelir_gider_liste_pdf,
)


@ui.page('/gelir-gider')
def gelir_gider_page(focus: int = None):
    if not create_layout(active_path='/gelir-gider', page_title='Gelir / Gider'):
        return
    ui.add_css('''
    .gg-table tbody tr { cursor: pointer; }

    /* ===== Yeni Gelir/Gider modali — Yeni Islem (D4) kompakt yapisiyla ayni ===== */
    .im-modal { font-size:12.5px; border-radius:14px; }
    .im-modal .im-head { background:#f0fdf9; border-bottom:1px solid #d5efe6;
        padding:11px 18px; display:flex; align-items:center; gap:9px;
        width:100%; align-self:stretch; box-sizing:border-box;
        flex:0 0 auto !important; overflow:hidden !important; }
    .im-modal .im-head .im-ic { color:#059669; font-size:20px; }
    .im-modal .im-head .im-title { font-size:15px; font-weight:700; color:#0f172a; }
    .im-modal .im-body { background:#ffffff !important; padding:10px 16px !important; gap:6px !important; }
    .im-modal .im-body > .row, .im-modal .im-body > .nicegui-row { gap:8px !important; }
    .im-modal .im-field { display:flex; flex-direction:column; gap:2px; min-width:0;
        background:transparent !important; padding:0 !important; }
    .im-modal .im-flabel { font-size:10px; font-weight:700; text-transform:uppercase;
        color:#64748b; letter-spacing:.03em; line-height:1.2; padding-left:1px; }
    .im-modal .q-field--outlined .q-field__control:before { border-color:#dbe3ea !important; }
    .im-modal .q-field--dense .q-field__control,
    .im-modal .q-field--dense .q-field__append,
    .im-modal .q-field--dense .q-field__control--addon { height:34px !important; min-height:34px !important; }
    .im-modal .q-field--dense .q-field__control-container { display:flex; align-items:center; }
    .im-modal .q-field--dense .q-field__native, .im-modal .q-field--dense .q-field__input {
        font-size:12.5px; min-height:32px; }
    .im-modal .q-field__label { color:#64748b !important; text-transform:uppercase;
        font-size:10px; letter-spacing:.03em; }
    .im-modal .q-field--focused .q-field__label { color:#059669 !important; }
    .im-modal .q-field--focused .q-field__control:after { border-color:#059669 !important; }
    .im-modal .q-select__dropdown-icon { display:none !important; }
    /* Toplam cubugu (3 hucre) */
    .im-totbar { display:grid; background:#f8fafc; border:1px solid #e2e8f0;
        border-radius:9px; overflow:hidden; flex:0 0 auto; }
    .gg-tot3 { grid-template-columns:repeat(3,1fr); }
    .im-tot { padding:7px 12px; border-right:1px solid #e8edf3; }
    .im-tot:last-child { border-right:none; background:#ecfdf5; }
    .im-tot .tk { font-size:9.5px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:#8a97a6; }
    .im-tot:last-child .tk { color:#059669; }
    .im-tot .tv { font-size:14.5px; font-weight:800; color:#0f172a; font-variant-numeric:tabular-nums; }
    .im-tot:last-child .tv { color:#047857; }
    /* Odeme durumu: pill radio + klavye odak kutusu */
    .im-odeme { display:flex; align-items:flex-end; gap:12px; flex-wrap:nowrap; }
    .im-modal .q-radio--checked .q-radio__inner { color:#059669 !important; }
    .im-modal .im-odeme .q-option-group { display:flex; gap:8px; flex-wrap:wrap; }
    .im-modal .im-odeme .q-radio { border:1px solid #dbe1e8; border-radius:8px; padding:2px 10px; margin:0; }
    .im-modal .im-odeme .q-radio--checked { background:#e7f6ef; border-color:#059669; }
    .im-modal .im-odeme .q-radio__label { font-weight:600; font-size:12px; }
    .im-modal .im-odeme .q-radio__inner { font-size:22px; }
    .im-vpwrap { border:1px solid transparent; border-radius:10px; padding:1px 6px; outline:none; }
    .im-vpwrap:focus { border-color:#c7dbe8; background:#f6fafd; }
    .im-modal .im-btn-kaydet:focus, .im-modal .im-btn-iptal:focus {
        outline:2px solid #0891b2; outline-offset:2px; }
    ''')

    table_ref = None
    all_rows = []
    ozet_box = None
    view_button = None
    back_button = None
    table_title = None
    now = datetime.now()
    # Default: yil=mevcut, ay=None (Tumu) — UI donem_secici default_ay=0 ile sync
    state = {
        'yil': now.year,
        'ay': None,
        'view': 'normal',
        'selected_tur': None,
        'selected_kategori': None,
    }
    search_val = {'text': ''}

    normal_columns = [
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

    kategori_columns = [
        {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
        {'name': 'kategori', 'label': 'Kategori', 'field': 'kategori', 'align': 'left', 'sortable': True},
        {'name': 'adet', 'label': 'Adet', 'field': 'adet', 'align': 'right', 'sortable': True},
        {'name': 'matrah', 'label': 'Matrah', 'field': 'matrah', 'align': 'right', 'sortable': True},
        {'name': 'kdv', 'label': 'KDV', 'field': 'kdv', 'align': 'right', 'sortable': True},
        {'name': 'toplam', 'label': 'Toplam', 'field': 'toplam', 'align': 'right', 'sortable': True},
        {'name': 'yuzde', 'label': '%', 'field': 'yuzde', 'align': 'right', 'sortable': True},
    ]

    def _filter_rows(rows):
        q = normalize_search(search_val['text'])
        if not q:
            return rows
        return [r for r in rows if
                q in normalize_search(r.get('kategori', '')) or
                q in normalize_search(r.get('aciklama', '')) or
                q in normalize_search(r.get('firma_ad', '')) or
                q in normalize_search(r.get('tur', ''))]

    def _kategori_rows(rows):
        """PDF raporundaki gruplamayi ekrana uygun, hafif satirlara donusturur."""
        grouped = kategori_ozet(rows)
        result = []
        for tur in ('GIDER', 'GELIR'):
            tur_rows = grouped.get(tur, [])
            tur_toplam = sum(float(item.get('toplam', 0) or 0) for item in tur_rows)
            for index, item in enumerate(tur_rows):
                toplam = float(item.get('toplam', 0) or 0)
                result.append({
                    'id': f'kategori:{tur}:{index}',
                    'tur': tur,
                    'kategori': item.get('kategori', ''),
                    'adet': item.get('adet', 0),
                    'matrah': item.get('matrah', 0),
                    'kdv': item.get('kdv', 0),
                    'toplam': toplam,
                    'yuzde': (toplam / tur_toplam * 100) if tur_toplam else 0,
                })
        return result

    def _update_view_header():
        if table_title is None:
            return

        view = state['view']
        if view == 'kategori':
            table_title.set_text('Kategori Özeti')
        elif view == 'kategori_detay':
            tur_label = 'Gelir' if state['selected_tur'] == 'GELIR' else 'Gider'
            table_title.set_text(f"{tur_label} Kategori Detayı: {state['selected_kategori']}")
        else:
            table_title.set_text('Gelir / Gider Kayıtları')

        if back_button is not None:
            back_button.set_visibility(view == 'kategori_detay')
        if view_button is not None:
            if view == 'normal':
                view_button.set_text('Kategori')
                view_button.props('icon=donut_small')
            else:
                view_button.set_text('Normal Kayıtlar')
                view_button.props('icon=view_list')

    def apply_filters():
        if not table_ref:
            return

        rows = _filter_rows(all_rows)
        if state['view'] == 'kategori':
            table_ref.columns = kategori_columns
            table_ref.rows = _kategori_rows(rows)
            table_ref.pagination = {'rowsPerPage': 50}
        elif state['view'] == 'kategori_detay':
            table_ref.columns = normal_columns
            table_ref.rows = [
                row for row in rows
                if row.get('tur') == state['selected_tur']
                and ((row.get('kategori') or '').strip() or '(Kategorisiz)') == state['selected_kategori']
            ]
            table_ref.pagination = {'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        else:
            table_ref.columns = normal_columns
            table_ref.rows = rows
            table_ref.pagination = {'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}

        _update_view_header()
        table_ref.update()

    def _toggle_kategori_view():
        if state['view'] == 'normal':
            state['view'] = 'kategori'
        else:
            state['view'] = 'normal'
            state['selected_tur'] = None
            state['selected_kategori'] = None
        apply_filters()

    def _show_kategori_detail(row):
        state['view'] = 'kategori_detay'
        state['selected_tur'] = row.get('tur')
        state['selected_kategori'] = row.get('kategori')
        apply_filters()

    def _back_to_kategori():
        state['view'] = 'kategori'
        state['selected_tur'] = None
        state['selected_kategori'] = None
        apply_filters()

    def _handle_table_row_click(row):
        if state['view'] == 'kategori':
            _show_kategori_detail(row)
        else:
            _show_row_detail(row)

    def load_data():
        nonlocal all_rows
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        apply_filters()
        ozet = get_gelir_gider_ozet(yil=state['yil'], ay=state['ay'])
        if ozet_box is not None:
            net_fg = '#15803d' if (ozet['net'] or 0) >= 0 else '#b91c1c'
            ozet_box.clear()
            with ozet_box:
                ozet_pill([
                    ('Gelir', ozet['gelir'], '#15803d'),
                    ('Gider', ozet['gider'], '#b91c1c'),
                    ('Net', ozet['net'], net_fg),
                ])

    def _build_kategori_options(tur):
        """Kategori secenekleri: en cok kullanilan ustte, hepsi iconlu.
        Kullanicinin olusturdugu (veride var olan) kategoriler de dahil."""
        known = list(GELIR_KATEGORILER if tur == 'GELIR' else GIDER_KATEGORILER)
        # Kullanim sayisina gore sirali kategoriler (cok -> az)
        try:
            kullanim = get_kategori_kullanim(tur)
        except Exception:
            kullanim = []
        # Sira: once kullanilanlar (cok->az), sonra hic kullanilmayan hazir kategoriler
        ordered, seen = [], set()
        for k, _adet in kullanim:
            if k and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in known:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        # Label'lari icon ile kur
        opts = {}
        for k in ordered:
            ikon = kategori_ikon(k)
            opts[k] = f'{ikon} {k}' if ikon else k
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

    def open_quick_kategori_dialog(on_added):
        """Hizli yeni kategori ekleme dialogu."""
        with ui.dialog() as kdlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 380px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('sell')
                ui.label('Yeni Kategori Ekle').classes('dialog-title')
            inp_kat_ad = ui.input('Kategori Adı').props('outlined dense autofocus').classes('w-full q-mt-sm')
            ui.label('İlk harfler otomatik büyük yazılır (örn: nakliye → Nakliye).').classes(
                'text-caption text-grey-6 q-pl-sm')

            def _save():
                ad = kategori_normalize((inp_kat_ad.value or '').strip())
                if not ad:
                    ui.notify('Kategori adı boş olamaz', type='warning')
                    return
                kdlg.close()
                on_added(ad)

            inp_kat_ad.on('keydown.enter', lambda _: _save())
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=kdlg.close).props('flat color=grey')
                ui.button('Ekle', color='primary', on_click=_save).props('unelevated')
        kdlg.open()

    def open_dialog(edit_row=None):
        is_edit = edit_row is not None
        title = 'Kayıt Düzenle' if is_edit else 'Yeni Gelir/Gider'

        firmalar = get_firma_list()
        firma_options = {f['kod']: f['ad'] for f in firmalar}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 660px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('payments' if not is_edit else 'drive_file_rename_outline').classes('im-ic')
                ui.label(title).classes('im-title')

            # Icerik kendi icinde kayar; buton satiri altta sabit
            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Tarih + Tur + Kategori (etiket kutu USTUNDE — Yeni Islem D4 yapisi)
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TARİH').classes('im-flabel')
                        inp_tarih = ui.input(value=date.today().isoformat()).props(
                            'outlined dense type=date').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('TÜR').classes('im-flabel')
                        inp_tur = ui.select(
                            options={'GELIR': 'Gelir', 'GIDER': 'Gider'}, value='GIDER'
                        ).props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('KATEGORİ').classes('im-flabel')
                        inp_kategori = ui.select(
                            options=_build_kategori_options('GIDER'), value='Nakliye'
                        ).props('outlined dense').classes('w-full')
                        with inp_kategori.add_slot('append'):
                            ui.icon('add', size='20px').classes('cursor-pointer').style('color:#059669').on(
                                'click', lambda: open_quick_kategori_dialog(_on_kategori_added))

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

                # Cari (opsiyonel; + kutu ICINDE — Yeni Islem firma alani gibi)
                with ui.element('div').classes('im-field w-full'):
                    ui.label('CARİ (OPSİYONEL)').classes('im-flabel')
                    inp_firma = ui.select(
                        options=firma_options, with_input=True, clearable=True,
                    ).props('outlined dense').classes('w-full gg-cari')
                    with inp_firma.add_slot('append'):
                        ui.icon('add', size='20px').classes('cursor-pointer').style('color:#059669').on(
                            'click', lambda: open_quick_firma_dialog(_on_firma_added))

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

                def _on_kategori_added(ad):
                    """Yeni olusturulan kategoriyi en uste ekle (iconlu) ve sec."""
                    opts = dict(inp_kategori.options)
                    if ad not in opts:
                        ikon = kategori_ikon(ad)
                        yeni = {ad: (f'{ikon} {ad}' if ikon else ad)}
                        yeni.update(opts)
                        inp_kategori.options = yeni
                    inp_kategori.value = ad
                    inp_kategori.update()
                    on_kategori_change(None)

                # Satir 3: Tutar + KDV
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TUTAR (NET)').classes('im-flabel')
                        inp_tutar = ui.number(value=0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full gg-tutar')
                    with ui.element('div').classes('im-field col'):
                        ui.label('KDV ORANI').classes('im-flabel')
                        inp_kdv = ui.select(
                            options={0: '%0', 1: '%1', 10: '%10', 20: '%20'}, value=20
                        ).props('outlined dense').classes('w-full')

                # Odeme durumu: pill radio; klavyeyle gelince belirgin kutu (ok tuslariyla secim)
                with ui.element('div').classes('im-field w-full'):
                    ui.label('ÖDEME DURUMU').classes('im-flabel')
                    with ui.element('div').classes('im-odeme'):
                        with ui.element('div').classes('im-vpwrap').props('tabindex=-1') as durum_wrap:
                            inp_durum = ui.radio(
                                options={
                                    'NAKIT': 'Nakit (Kasa)',
                                    'BANKA': 'Banka',
                                    'CEK': 'Çek',
                                    'SENET': 'Senet',
                                    'ODENMEDI': 'Ödenmedi (Cari borç)',
                                },
                                value='NAKIT',
                            ).props('inline dense')

                # Baglamsal alanlar: Odenen + Banka + Vade (duruma gore) tek satirda
                with ui.row().classes('w-full gap-sm no-wrap items-end'):
                    odeme_container = ui.row().classes('col gap-sm items-end no-wrap')
                    with odeme_container:
                        with ui.element('div').classes('im-field').style('flex:0 0 150px'):
                            ui.label('ÖDENEN TUTAR').classes('im-flabel')
                            inp_odenen = ui.number(value=0, format='%.2f').props(
                                'outlined dense input-class=text-right').classes('w-full gg-odenen')
                        banka_row = ui.element('div').classes('im-field').style('flex:1;min-width:0')
                        banka_row.set_visibility(False)
                        with banka_row:
                            ui.label('BANKA HESABI').classes('im-flabel')
                            _bopts = {str(h['id']): h['ad'] for h in list_banka_hesaplari(sadece_aktif=True)}
                            inp_banka = ui.select(_bopts).props('outlined dense').classes('w-full')
                        lbl_kalan_borc = ui.label('').classes('text-caption text-orange-9') \
                            .style('padding-bottom:8px;white-space:nowrap')
                    vade_container = ui.element('div').classes('im-field').style('flex:0 0 160px')
                    vade_container.set_visibility(False)
                    with vade_container:
                        ui.label('VADE TARİHİ').classes('im-flabel')
                        inp_vade = ui.input(value='').props(
                            'outlined dense type=date clearable').classes('w-full gg-vade')

                # Aciklama
                with ui.element('div').classes('im-field w-full'):
                    ui.label('AÇIKLAMA').classes('im-flabel')
                    inp_aciklama = ui.input().props('outlined dense').classes('w-full gg-aciklama')

                # Toplam cubugu (Yeni Islem'deki gibi)
                def _tot_cell(baslik):
                    with ui.element('div').classes('im-tot'):
                        ui.label(baslik).classes('tk')
                        return ui.label('0,00').classes('tv')

                with ui.element('div').classes('im-totbar gg-tot3 w-full'):
                    lbl_tutar = _tot_cell('TUTAR (NET)')
                    lbl_kdv = _tot_cell('KDV')
                    lbl_toplam = _tot_cell('TOPLAM')

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
                    lbl_tutar.set_text(fmt_tr(t))
                    lbl_kdv.set_text(fmt_tr(kdv))
                    lbl_toplam.set_text(fmt_tr(toplam) + ' ₺')

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
                    banka_row.set_visibility(val == 'BANKA')
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
                elif odm_sk in ('HAVALE', 'BANKA', 'EFT'):
                    inp_durum.value = 'BANKA'
                else:
                    inp_durum.value = 'NAKIT'
                vade_container.set_visibility(inp_durum.value == 'ODENMEDI')
                odeme_container.set_visibility(inp_durum.value != 'ODENMEDI')
                banka_row.set_visibility(inp_durum.value == 'BANKA')
                if edit_row.get('banka_hesap_id'):
                    inp_banka.value = str(edit_row.get('banka_hesap_id'))
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

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

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
                    banka_hesap_id = int(inp_banka.value) if (durum == 'BANKA' and inp_banka.value) else None
                    if durum == 'BANKA' and not banka_hesap_id:
                        notify_err('Banka hesabı seçmelisiniz')
                        return

                    if durum == 'BANKA':
                        odeme_sekli = 'BANKA'
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
                        'banka_hesap_id': banka_hesap_id,
                    }

                    try:
                        if is_edit:
                            update_gelir_gider(edit_row['id'], data)
                            notify_ok('Kayıt güncellendi')
                        else:
                            gg_id = add_gelir_gider(data)

                            # Sadece KISMI odemede kasa kaydini burada olustur.
                            # ODENDI (tam) durumunda add_gelir_gider() zaten otomatik
                            # kasa kaydi olusturuyor -> mukerrer kayit olmasin diye buraya girme.
                            if odeme_durumu == 'KISMI':
                                kasa_tur = 'GELIR' if inp_tur.value == 'GELIR' else 'GIDER'
                                kat = inp_kategori.value or ''
                                kasa_aciklama = f'{kat}'
                                if data['aciklama']:
                                    kasa_aciklama += f': {data["aciklama"]}'
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
                                    'banka_hesap_id': banka_hesap_id,
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

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

                # --- Enter akisi (sunucu tarafi: popup acma zinciri) ---
                # Tarih -> Tur(liste) -> Kategori(liste) -> Cari -> Tutar -> KDV(liste)
                # -> Odeme Durumu kutusu -> (Vade | Banka -> Odenen | Odenen) -> Aciklama -> Kaydet
                def _js_focus(sel_css, select_all=False):
                    ui.run_javascript(
                        f"const el=[...document.querySelectorAll('{sel_css}')].pop();"
                        "if(el){el.focus();" + ("if(el.select)el.select();" if select_all else "") + "}")

                _nav = {'tur': False, 'kat': False, 'kdv': False, 'banka': False}

                def _ac(sel, flag):
                    _nav[flag] = True
                    sel.run_method('focus')
                    sel.run_method('showPopup')

                inp_tarih.on('keydown.enter.prevent', lambda: _ac(inp_tur, 'tur'))

                def _tur_hide():
                    if _nav['tur']:
                        _nav['tur'] = False
                        _ac(inp_kategori, 'kat')
                inp_tur.on('popup-hide', _tur_hide)

                def _kat_hide():
                    if _nav['kat']:
                        _nav['kat'] = False
                        inp_firma.run_method('focus')
                inp_kategori.on('popup-hide', _kat_hide)

                inp_tutar.on('keydown.enter.prevent', lambda: _ac(inp_kdv, 'kdv'))

                def _kdv_hide():
                    if _nav['kdv']:
                        _nav['kdv'] = False
                        _js_focus('.im-modal .im-vpwrap')
                inp_kdv.on('popup-hide', _kdv_hide)

                def _durum_enter():
                    val = inp_durum.value or 'NAKIT'
                    if val == 'ODENMEDI':
                        inp_vade.run_method('focus')
                    elif val == 'BANKA':
                        _ac(inp_banka, 'banka')
                    else:
                        _js_focus('.im-modal .gg-odenen input', select_all=True)
                durum_wrap.on('keydown.enter.prevent', _durum_enter)

                def _banka_hide():
                    if _nav['banka']:
                        _nav['banka'] = False
                        _js_focus('.im-modal .gg-odenen input', select_all=True)
                inp_banka.on('popup-hide', _banka_hide)
        dlg.open()
        # Acilinca odak Tarih'e
        ui.timer(0.2, lambda: inp_tarih.run_method('focus'), once=True)
        # Klavye akisi (CLIENT-SIDE, gecikmesiz): durum kutusunda ok tuslari,
        # Cari/Odenen/Vade/Aciklama Enter atlamalari, Kaydet<->Iptal ok gecisi
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__ggFlow) return;
            modal.__ggFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const go = (sel, selAll) => { const el = modal.querySelector(sel);
                if(el){ el.focus(); if(selAll && el.select) el.select(); } };
            const dw = modal.querySelector('.im-vpwrap');
            if(dw) dw.addEventListener('keydown', (e) => {
                const r = [...dw.querySelectorAll('.q-radio')];
                const i = r.findIndex(x => x.getAttribute('aria-checked') === 'true');
                if(e.key === 'ArrowRight'){ e.preventDefault();
                    const n = r[Math.min(i + 1, r.length - 1)]; if(n) n.click(); dw.focus(); }
                else if(e.key === 'ArrowLeft'){ e.preventDefault();
                    const p = r[Math.max(i - 1, 0)]; if(p) p.click(); dw.focus(); }
            });
            const cari = modal.querySelector('.gg-cari input');
            if(cari) cari.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ setTimeout(() => go('.gg-tutar input', true), 80); }
            });
            const odenen = modal.querySelector('.gg-odenen input');
            if(odenen) odenen.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); go('.gg-aciklama input'); }
            });
            const vade = modal.querySelector('.gg-vade input');
            if(vade) vade.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); go('.gg-aciklama input'); }
            });
            const acik = modal.querySelector('.gg-aciklama input');
            if(acik) acik.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

    def do_delete(rec_id):
        def confirmed():
            try:
                delete_gelir_gider(rec_id)
                notify_ok('Kayıt silindi')
                load_data()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu kaydı silmek istediğinize emin misiniz?', confirmed)

    def _show_row_detail(row):
        """Gelir/Gider satır detaylarını gösteren modern bir kart/modal açar."""
        tur = row.get('tur', '')
        
        # Tür-bazlı renk ve başlık atamaları (Açık Tema)
        if tur == 'GELIR':
            bg_color = 'bg-emerald-50'
            text_color = 'text-emerald-800'
            border_color = 'border-emerald-100'
            tur_label = 'Gelir Kaydı'
            icon = 'arrow_downward'
        else: # GIDER
            bg_color = 'bg-rose-50'
            text_color = 'text-rose-800'
            border_color = 'border-rose-100'
            tur_label = 'Gider Kaydı'
            icon = 'arrow_upward'
            
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('width: 90vw; max-width: 500px; border-radius: 12px;'):
            # Header
            with ui.row().classes(f'w-full items-center justify-between q-pa-sm rounded-lg border {bg_color} {border_color} q-mb-md'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon(icon).classes(f'text-xl {text_color}')
                    ui.label(tur_label).classes(f'text-base font-bold {text_color}')
                ui.badge(f"ID: {row.get('id', '')}", color='grey-2').props('text-color=grey-7')

            # Body
            with ui.column().classes('w-full gap-1 q-mb-md'):
                def info_row(label, value, is_mono=False, extra_style=''):
                    if value is None or value == '':
                        value = '-'
                    with ui.row().classes('w-full py-2 px-3 justify-between items-center rounded transition-all hover:bg-slate-50 border-b border-slate-100'):
                        ui.label(label).classes('text-xs font-semibold text-slate-500 uppercase tracking-wider')
                        ui.label(str(value)).classes(f'text-sm font-medium text-slate-800 {"num-mono" if is_mono else ""}').style(extra_style)

                # Bilgiler
                tarih_str = row.get('tarih', '')
                if tarih_str:
                    try:
                        dt = datetime.strptime(tarih_str, '%Y-%m-%d')
                        tarih_str = dt.strftime('%d.%m.%Y')
                    except Exception:
                        pass
                info_row('Tarih', tarih_str)
                info_row('Firma Adı', row.get('firma_ad'))
                
                # Tutar (vurgulu)
                toplam = row.get('toplam', 0)
                info_row('Tutar (Matrah)', f"{fmt_para(toplam)} TL", is_mono=True, extra_style='font-weight: 700; color: #1e293b; font-size: 15px;')
                
                info_row('Kategori', row.get('kategori'))
                
                # Ödeme Durumu
                durum = row.get('odeme_durumu', '')
                durum_label = 'Ödendi' if durum == 'ODENDI' else 'Kısmi' if durum == 'KISMI' else 'Ödenmedi'
                info_row('Ödeme Durumu', durum_label)
                
                info_row('Ödeme Şekli', row.get('odeme_sekli'))
                info_row('Açıklama', row.get('aciklama'))

            ui.separator().classes('q-my-xs')

            # Footer
            with ui.row().classes('w-full justify-between items-center q-mt-md'):
                ui.button('Kapat', on_click=dlg.close).props('flat color=grey')
                
                with ui.row().classes('gap-2'):
                    ui.button('Düzenle', icon='edit', 
                              on_click=lambda: (dlg.close(), open_dialog(edit_row=row))) \
                        .props('unelevated no-caps color=primary dense')
                    ui.button('Sil', icon='delete', 
                              on_click=lambda: (dlg.close(), do_delete(row.get('id')))) \
                        .props('unelevated no-caps color=negative dense')
                        
        dlg.open()

    def on_donem_change(yil, ay):
        state['yil'] = yil
        state['ay'] = ay
        load_data()

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        ozet = get_gelir_gider_ozet(yil=state['yil'], ay=state['ay'])

        with ui.element('div').classes('w-full q-mb-sm'):
            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                def _on_search_change(e):
                    search_val['text'] = e.value or ''
                    apply_filters()

                search_input = ui.input(
                    placeholder='Ara (kategori, açıklama)...',
                    on_change=_on_search_change,
                ).props('outlined dense clearable').classes('w-64')
                donem_popover_btn(on_donem_change, default_mode='YIL')
                ui.space()
                ozet_box = ui.row().classes('items-center no-wrap q-mr-sm')
                with ozet_box:
                    _ng = '#15803d' if (ozet['net'] or 0) >= 0 else '#b91c1c'
                    ozet_pill([
                        ('Gelir', ozet['gelir'], '#15803d'),
                        ('Gider', ozet['gider'], '#b91c1c'),
                        ('Net', ozet['net'], _ng),
                    ])

                def _open_pdf(pdf_bytes, filename):
                    preview_url = save_pdf_preview(pdf_bytes, filename)
                    ui.run_javascript(f"window.open('{preview_url}', '_blank')")

                def _open_pdf_dialog():
                    import calendar
                    _t = date.today()

                    def _ay_araligi(y, m):
                        return f'{y:04d}-{m:02d}-01', f'{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}'

                    # Varsayilan tarih araligi = sayfadaki mevcut donem
                    if state.get('ay'):
                        _db, _de = _ay_araligi(state['yil'], state['ay'])
                    elif state.get('yil'):
                        _db, _de = f"{state['yil']}-01-01", f"{state['yil']}-12-31"
                    else:
                        _db, _de = '', ''

                    with ui.dialog() as pdlg, ui.card().classes('alse-dialog').style('width:90vw;max-width:470px'):
                        with ui.element('div').classes('alse-dialog-header'):
                            ui.icon('picture_as_pdf')
                            ui.label('PDF Raporu').classes('dialog-title')
                        with ui.column().classes('w-full gap-3').style('padding:10px 4px'):
                            with ui.row().classes('w-full gap-2 items-end no-wrap'):
                                inp_bas = ui.input('Başlangıç', value=_db).props(
                                    'outlined dense type=date label-color=cyan-8').classes('col')
                                inp_bit = ui.input('Bitiş', value=_de).props(
                                    'outlined dense type=date label-color=cyan-8').classes('col')
                            with ui.row().classes('w-full gap-1 items-center'):
                                ui.label('Hızlı:').classes('text-caption text-grey-7')

                                def _pre(b, e):
                                    inp_bas.set_value(b)
                                    inp_bit.set_value(e)
                                ui.button('Bugün', on_click=lambda: _pre(_t.isoformat(), _t.isoformat())).props('dense flat no-caps size=sm')
                                ui.button('Bu Ay', on_click=lambda: _pre(*_ay_araligi(_t.year, _t.month))).props('dense flat no-caps size=sm')
                                _pm = (_t.year, _t.month - 1) if _t.month > 1 else (_t.year - 1, 12)
                                ui.button('Geçen Ay', on_click=lambda: _pre(*_ay_araligi(*_pm))).props('dense flat no-caps size=sm')
                                ui.button('Bu Yıl', on_click=lambda: _pre(f'{_t.year}-01-01', f'{_t.year}-12-31')).props('dense flat no-caps size=sm')
                                ui.button('Tümü', on_click=lambda: _pre('', '')).props('dense flat no-caps size=sm color=grey-7')

                            ui.separator()
                            with ui.row().classes('w-full items-center gap-2'):
                                ui.label('Tür:').classes('text-caption text-grey-7')
                                inp_tur = ui.radio({'HEPSI': 'Hepsi', 'GIDER': 'Gider', 'GELIR': 'Gelir'},
                                                   value='HEPSI').props('inline dense color=cyan-8')
                            with ui.column().classes('w-full gap-1'):
                                ui.label('Rapor Tipi').classes('text-caption text-grey-7')
                                inp_tip = ui.radio({'normal': 'Normal (düz liste)',
                                                    'kategori': 'Kategori bazlı (gruplu + toplam)'},
                                                   value='normal').props('dense color=cyan-8').classes('w-full')
                            chk_detay = ui.checkbox('Kategori raporunda detay satırları da olsun', value=False)
                            chk_detay.bind_visibility_from(inp_tip, 'value', backward=lambda v: v == 'kategori')

                        with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                            ui.button('İptal', on_click=pdlg.close).props('flat color=grey')

                            def _uret():
                                try:
                                    bas = (inp_bas.value or '').strip() or None
                                    bit = (inp_bit.value or '').strip() or None
                                    tur = None if inp_tur.value == 'HEPSI' else inp_tur.value
                                    rows = get_gelir_gider_rapor(bas, bit, tur)
                                    if not rows:
                                        notify_err('Seçilen kriterlerde kayıt bulunamadı')
                                        return
                                    if bas and bit:
                                        _dl = f"{bas[8:10]}.{bas[5:7]}.{bas[:4]} - {bit[8:10]}.{bit[5:7]}.{bit[:4]}"
                                    else:
                                        _dl = 'Tüm Zamanlar'
                                    if inp_tip.value == 'kategori':
                                        pdf = generate_gelir_gider_kategori_pdf(
                                            kategori_ozet(rows), f'Kategori Raporu — {_dl}',
                                            tur_filtre=inp_tur.value, detay=chk_detay.value)
                                        fname = 'gelir_gider_kategori.pdf'
                                    else:
                                        pdf = generate_gelir_gider_liste_pdf(rows, f'Gelir / Gider Raporu — {_dl}')
                                        fname = 'gelir_gider_raporu.pdf'
                                    pdlg.close()
                                    _open_pdf(pdf, fname)
                                except Exception as e:
                                    notify_err(f'PDF hatası: {e}')

                            ui.button('PDF Oluştur', color='primary', on_click=_uret).props('unelevated')
                    pdlg.open()

                view_button = ui.button(
                    'Kategori', icon='donut_small', color='primary', on_click=_toggle_kategori_view,
                ).props('dense outline no-caps')
                ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_open_pdf_dialog).props('dense')
                ui.button('YENİ', icon='swap_vert', color='primary', on_click=lambda: open_dialog()).props('dense no-caps')

        with ui.row().classes('w-full items-center gap-2 q-mb-xs').style('min-height: 32px'):
            back_button = ui.button(
                'Kategori Özetine Dön', icon='arrow_back', on_click=_back_to_kategori,
            ).props('dense flat no-caps color=primary')
            back_button.set_visibility(False)
            table_title = ui.label('Gelir / Gider Kayıtları').classes('text-subtitle2 text-weight-bold text-grey-8')

        # Table
        table_ref = ui.table(
            columns=normal_columns, rows=all_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full gg-table').style('--table-extra-rows: 2;')
        table_ref.props('flat bordered dense')

        table_ref.add_slot('body-cell-tarih', TARIH_SLOT)
        table_ref.add_slot('body-cell-toplam', PARA_SLOT)
        table_ref.add_slot('body-cell-matrah', PARA_SLOT)
        table_ref.add_slot('body-cell-kdv', r'''
            <q-td :props="props">
                {{ (Number(props.value) || 0).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' }}
            </q-td>
        ''')
        table_ref.add_slot('body-cell-yuzde', r'''
            <q-td :props="props">
                <span class="text-weight-bold text-grey-8">%{{ Math.round(Number(props.value) || 0) }}</span>
            </q-td>
        ''')

        table_ref.add_slot('body-cell-tur', r'''
            <q-td :props="props">
                <q-chip dense :color="props.value === 'GELIR' ? 'positive' : 'negative'" text-color="white" size="sm">
                    {{ props.value === 'GELIR' ? 'Gelir' : 'Gider' }}
                </q-chip>
            </q-td>
        ''')

        # Kategori - Nakliye/Ardiye one cikan
        # Kategori hucresi: dropdown ile ayni emoji-ikonlu gorunum (tum kategoriler ayni stil)
        import json as _json
        _kat_ikon_js = _json.dumps(KATEGORI_IKON, ensure_ascii=False)
        table_ref.add_slot('body-cell-kategori', (r'''
            <q-td :props="props">
                <span>{{ props.value ? (((__IKONMAP__)[props.value] || '🏷️') + ' ' + props.value) : '' }}</span>
            </q-td>
        ''').replace('__IKONMAP__', _kat_ikon_js))

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
        table_ref.on('row-click', lambda e: _handle_table_row_click(e.args[1]))

        # Islemler detay modalindan 'Kaynak -> kayda git' ile gelinince ilgili kaydi ac
        if focus:
            _rec = next((r for r in all_rows if str(r.get('id')) == str(focus)), None)
            if _rec:
                open_dialog(edit_row=_rec)
