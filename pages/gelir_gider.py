"""ALSE Plastik Hammadde - Gelir/Gider Sayfasi"""
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, fmt_para, ozet_pill,
    notify_ok, notify_err, confirm_dialog, normalize_search, donem_secici, donem_popover_btn,
)
from services.gelir_gider_service import (
    get_gelir_gider_list, get_gelir_gider_ozet,
    delete_gelir_gider, delete_gelir_gider_grup,
    save_gelir_gider_grup, get_gelir_gider_grup, gelir_gider_grupla,
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
    .im-enter-hint { font-size:10.5px; color:#94a3b8; white-space:nowrap; }
    /* Buton altinda F-tusu etiketi (akisa girmez -> tabloyu itmez) */
    .gg-fhint { position:absolute; top:100%; left:50%; transform:translateX(-50%);
        font-size:8.5px; color:#94a3b8; font-weight:700; letter-spacing:.5px;
        line-height:1; margin-top:2px; pointer-events:none; }

    /* --- Kalem tablosu (Yeni Islem ile ayni yapi): basliklar + 1-3 satir, sonra kaydirma --- */
    .im-ktable { border:1px solid #e2e8f0; border-radius:9px; overflow:hidden; flex:0 0 auto; }
    .gg-kgrid { grid-template-columns:1fr 112px 58px 92px 104px 26px; }
    .im-kthead { display:grid; background:#f1f5f9; font-size:10px; font-weight:700; letter-spacing:.03em;
        text-transform:uppercase; color:#64748b; padding-right:8px; }
    .im-kthead > * { padding:5px 8px; }
    .im-kthead > *:nth-child(2), .im-kthead > *:nth-child(4), .im-kthead > *:nth-child(5) { text-align:right; }
    .im-kthead > *:nth-child(3) { text-align:center; }
    .im-kbody { min-height:33px; max-height:99px; overflow-y:auto; scrollbar-gutter:stable;
        scrollbar-width:thin; scrollbar-color:#dbe1e8 transparent; }
    .im-kbody::-webkit-scrollbar { width:8px; }
    .im-kbody::-webkit-scrollbar-thumb { background:#dbe1e8; border-radius:4px; }
    .im-kbody::-webkit-scrollbar-track { background:transparent; }
    .im-krow { display:grid; gap:0; align-items:center; border-top:1px solid #eef2f6; padding:1px 0; }
    .im-krow:first-child { border-top:none; }
    .im-krow .q-field { width:100%; }
    .im-modal .im-krow .q-field--dense .q-field__control,
    .im-modal .im-krow .q-field--dense .q-field__append { height:30px !important; min-height:30px !important; }
    .im-modal .im-krow .q-field__control { padding-left:8px !important; padding-right:8px !important; }
    .im-modal .im-krow .q-field__native, .im-modal .im-krow .q-field__input { text-align:right; padding:0 !important; }
    .im-modal .im-krow .q-select .q-field__native,
    .im-modal .im-krow .q-select input { text-align:left !important; }
    .im-modal .im-krow .q-field--focused .q-field__control { background:#f0fdf9 !important; }
    .im-modal .im-krow .im-kkdv .q-field__native { text-align:center !important; justify-content:center; }
    .im-ktutar { text-align:right; font-weight:700; color:#0f766e; font-size:12.5px;
        font-variant-numeric:tabular-nums; padding-right:8px; }
    .im-modal .im-kgt { color:#047857 !important; font-weight:800; }
    /* "Yeni kalem eklensin mi?" onayi: SECILI buton belirgin (JS 'imsel' sinifi) */
    .im-confirm-card button.imsel { outline:3px solid #059669 !important; outline-offset:2px;
        box-shadow:0 0 0 4px rgba(5,150,105,.20) !important; }
    /* Liste: coklu kalem akordeonu (Islemler sayfasiyla ayni renkler) */
    .gg-table tbody tr.gg-grup-acik td { background:#e0f2fe !important; }
    .gg-table tbody tr.gg-kalem-tr td { background:#f0f9ff !important; }
    .gg-table tbody tr.gg-grup-acik td:first-child,
    .gg-table tbody tr.gg-kalem-tr td:first-child { box-shadow:inset 3px 0 0 #0284c7; }
    ''')

    table_ref = None
    all_rows = []        # ham satirlar (her kalem ayri) — kategori ozeti/PDF bunu kullanir
    grouped_rows = []    # liste gorunumu: ayni grup_id'li kalemler tek satirda (akordeon)
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
                q in normalize_search(r.get('kategori_tum') or r.get('kategori', '')) or
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
            table_ref.rows = _filter_rows(grouped_rows)
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
        nonlocal all_rows, grouped_rows
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        grouped_rows = gelir_gider_grupla(all_rows)
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
                'width: 92vw; max-width: 700px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('payments' if not is_edit else 'drive_file_rename_outline').classes('im-ic')
                ui.label(title).classes('im-title')

            # Icerik kendi icinde kayar; buton satiri altta sabit
            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Tarih + Tur + Cari (etiket kutu USTUNDE — Yeni Islem D4 yapisi)
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 150px'):
                        ui.label('TARİH').classes('im-flabel')
                        inp_tarih = ui.input(value=date.today().isoformat()).props(
                            'outlined dense type=date').classes('w-full')
                    with ui.element('div').classes('im-field').style('flex:0 0 118px'):
                        ui.label('TÜR').classes('im-flabel')
                        inp_tur = ui.select(
                            options={'GELIR': 'Gelir', 'GIDER': 'Gider'}, value='GIDER'
                        ).props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('CARİ (OPSİYONEL)').classes('im-flabel')
                        # transition-duration=0: Enter ile kapanan cari listesinin 300ms kapanis
                        # zamanlayicisi, hemen ardindan acilan kategori listesini kapatiyordu.
                        inp_firma = ui.select(
                            options=firma_options, with_input=True, clearable=True,
                        ).props('outlined dense transition-duration=0').classes('w-full gg-cari')
                        with inp_firma.add_slot('append'):
                            ui.icon('add', size='20px').classes('cursor-pointer').style('color:#059669').on(
                                'click', lambda: open_quick_firma_dialog(_on_firma_added))

                def _on_firma_added(kod, ad):
                    firmalar2 = get_firma_list()
                    new_opts = {f['kod']: f['ad'] for f in firmalar2}
                    inp_firma.options = new_opts
                    inp_firma.value = kod
                    inp_firma.update()

                # --- Kalemler (kategori bazli): her kalem ayri gelir_gider satiri olur, grup_id ile baglanir ---
                kalemler_state = []   # {'row','kat','matrah','kdv','lbl_kdv','lbl_top','gg_id','nav','kdv_nav'}
                silinen_idler = []    # duzenlemede cikarilan kalemlerin gelir_gider id'leri

                ui.label('KALEMLER').classes('im-flabel').style('margin-top:2px')
                with ui.element('div').classes('im-ktable w-full'):
                    with ui.element('div').classes('im-kthead gg-kgrid'):
                        for _h in ('Kategori', 'Matrah (Net)', 'KDV %', 'KDV', 'Toplam', ''):
                            ui.label(_h)
                    kalemler_box = ui.element('div').classes('im-kbody')
                with ui.row().classes('w-full items-center no-wrap').style('gap:8px;margin-top:-2px'):
                    ui.button('Kalem Ekle', icon='add', on_click=lambda: add_kalem_row()).props(
                        'dense flat no-caps color=green-7 size=sm').style('font-size:11px;padding:2px 6px')
                    # One cikan uyari (Nakliye/Ardiye icin)
                    lbl_one_cikan = ui.label('').classes('text-caption text-orange-9')

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

                # Aciklama (tum kalemler icin ortak)
                with ui.element('div').classes('im-field w-full'):
                    ui.label('AÇIKLAMA').classes('im-flabel')
                    inp_aciklama = ui.input().props('outlined dense').classes('w-full gg-aciklama')

                # Toplam cubugu (Yeni Islem'deki gibi) — tum kalemlerin toplami
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

                def _kalem_hesap(entry):
                    """(matrah, oran, kdv, toplam)"""
                    t = float(entry['matrah'].value or 0)
                    ko = float(entry['kdv'].value or 0)
                    kdv = t * ko / 100
                    return t, ko, kdv, t + kdv

                def _guncel_toplam():
                    return sum(_kalem_hesap(e)[3] for e in kalemler_state)

                def recalc():
                    t_net = t_kdv = t_top = 0.0
                    for e in kalemler_state:
                        t, ko, kdv, top = _kalem_hesap(e)
                        e['lbl_kdv'].set_text(fmt_tr(kdv))
                        e['lbl_top'].set_text(fmt_tr(top))
                        t_net += t
                        t_kdv += kdv
                        t_top += top
                    lbl_tutar.set_text(fmt_tr(t_net))
                    lbl_kdv.set_text(fmt_tr(t_kdv))
                    lbl_toplam.set_text(fmt_tr(t_top) + ' ₺')

                    # Odenen varsayilan: toplam (sadece ODENMEDI degilse ve kullanici ellemediyse guncellenir)
                    if (inp_durum.value or 'NAKIT') != 'ODENMEDI':
                        inp_odenen.value = t_top
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
                inp_odenen.on_value_change(lambda _: _recalc_kalan())

                # --- Kategori yardimcilari ---
                _kat_busy = {'v': False}   # programatik kategori degisimi (tur degisince) odak akisini tetiklemesin

                def _kategori_uyari():
                    one = [e['kat'].value for e in kalemler_state
                           if (e['kat'].value or '') in ONE_CIKAN_GIDER_KATEGORILER]
                    lbl_one_cikan.set_text(f'⭐ {one[0]}: Cari seçerek borç takibi yapabilirsiniz' if one else '')

                def _kategori_eklendi(sel, ad):
                    """Yeni olusturulan kategoriyi ilgili kalemin listesine en uste ekle (iconlu) ve sec."""
                    opts = dict(sel.options)
                    if ad not in opts:
                        ikon = kategori_ikon(ad)
                        opts = {ad: (f'{ikon} {ad}' if ikon else ad), **opts}
                        sel.options = opts
                    sel.value = ad
                    sel.update()

                def on_tur_change(e):
                    opts = _build_kategori_options(e.value)
                    first_key = next(iter(opts))
                    _kat_busy['v'] = True
                    try:
                        for en in kalemler_state:
                            en['kat'].options = opts
                            en['kat'].value = first_key
                            en['kat'].update()
                    finally:
                        _kat_busy['v'] = False
                    _kategori_uyari()
                inp_tur.on_value_change(on_tur_change)

                def _matraha(entry):
                    entry['matrah'].run_method('focus')
                    entry['matrah'].run_method('select')

                def _ac_kat(entry, gecikme_ms=0):
                    """Klavye akisi: kalemin kategori listesini ac (secince/kapaninca Matrah'a gecer).
                    showPopup yerine kontrol tiklamasi: onceki bir liste (orn. Cari) kapanirken
                    showPopup Quasar tarafindan yutuluyor; tiklama mouse akisiyla birebir ayni."""
                    entry['nav'] = True
                    sel_cls = f'gg-kkat-{entry["kat"].id}'
                    # Acik bir liste/onay penceresi kapanis animasyonunu (~300ms, DOM'da kalir) bitirmeden
                    # tiklanirsa Quasar yeni listeyi de kapatiyor -> DOM'da portal kalmayana kadar (max 1.5 sn) bekle.
                    ui.run_javascript(
                        "(()=>{const t0=Date.now();"
                        "const tick=()=>{const acik=document.querySelector('.q-menu,.im-confirm-card')!==null;"
                        "if(acik&&Date.now()-t0<1500){setTimeout(tick,40);return;}"
                        f"const c=document.querySelector('.{sel_cls} .q-field__control');if(c)c.click();}};"
                        f"setTimeout(tick,{int(gecikme_ms)});}})()")

                def _kalem_soru():
                    """KDV secildikten sonra Enter: yeni kalem eklensin mi? Enter=Hayır(ödeme durumuna), → ile Evet."""
                    with ui.dialog() as kdlg, ui.card().classes('q-pa-md im-confirm-card').style('min-width:360px;border-radius:12px'):
                        ui.label('Yeni kalem eklensin mi?').classes('text-subtitle2 text-weight-bold').style('color:#0f766e')
                        ui.label('Enter = Hayır (ödeme durumuna geçer)   ·   → ile Evet').classes('text-caption text-grey-6 q-mb-sm')

                        def _evet():
                            kdlg.close()
                            _ac_kat(add_kalem_row())

                        def _hayir():
                            kdlg.close()
                            _js_focus('.im-modal .im-vpwrap')

                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Hayır', on_click=_hayir).props('flat color=grey')
                            ui.button('Evet', on_click=_evet).props('unelevated color=positive')
                    kdlg.open()
                    ui.timer(0.12, lambda: ui.run_javascript('''
                        const card = [...document.querySelectorAll('.im-confirm-card')].pop();
                        if(!card) return;
                        const btns = card.querySelectorAll('button');
                        if(btns.length < 2) return;
                        const noBtn = btns[0], yesBtn = btns[1];
                        const mark = (b) => { noBtn.classList.remove('imsel'); yesBtn.classList.remove('imsel');
                                              b.classList.add('imsel'); b.focus(); };
                        mark(noBtn);
                        card.addEventListener('keydown', (e) => {
                            if(e.key === 'ArrowLeft'){ mark(noBtn); e.preventDefault(); }
                            else if(e.key === 'ArrowRight'){ mark(yesBtn); e.preventDefault(); }
                        });
                    '''), once=True)

                def remove_kalem(entry):
                    if len(kalemler_state) <= 1:
                        notify_err('En az bir kalem olmalı')
                        return
                    if entry.get('gg_id'):
                        silinen_idler.append(entry['gg_id'])
                    kalemler_state.remove(entry)
                    entry['row'].delete()
                    recalc()
                    _kategori_uyari()

                def add_kalem_row(kayit=None, ilk=False):
                    kayit = kayit or {}
                    entry = {'gg_id': kayit.get('id'), 'nav': False, 'kdv_nav': False}
                    _kdv0 = kayit.get('kdv_orani')
                    _kdv0 = int(float(_kdv0)) if _kdv0 not in (None, '') else 20
                    if _kdv0 not in (0, 1, 10, 20):
                        _kdv0 = 20
                    opts = _build_kategori_options(inp_tur.value or 'GIDER')
                    kat0 = kayit.get('kategori') or None
                    if kat0 and kat0 not in opts:
                        opts = {kat0: f'{kategori_ikon(kat0)} {kat0}', **opts}
                    if not kat0:
                        kat0 = next(iter(opts))
                    _t0 = kayit.get('tutar')
                    with kalemler_box:
                        with ui.element('div').classes('im-krow gg-kgrid') as krow:
                            k_kat = ui.select(options=opts, value=kat0).props('borderless dense').classes('gg-kkat')
                            k_kat.classes(f'gg-kkat-{k_kat.id}')   # klavye akisi hedefi (satira ozel)
                            with k_kat.add_slot('append'):
                                ui.icon('add', size='16px').classes('cursor-pointer').style('color:#059669').on(
                                    'click', lambda _, sel=k_kat: open_quick_kategori_dialog(
                                        lambda ad, sel=sel: _kategori_eklendi(sel, ad)))
                            k_matrah = ui.number(
                                value=(float(_t0) if _t0 not in (None, '') else None), format='%.2f'
                            ).props('borderless dense placeholder="0.00" input-class=text-right').classes('gg-kmatrah')
                            k_kdv = ui.select(
                                options={0: '0', 1: '1', 10: '10', 20: '20'}, value=_kdv0
                            ).props('borderless dense').classes('im-kkdv gg-kkdv')
                            k_lbl_kdv = ui.label('0,00').classes('im-ktutar')            # kdv tutari
                            k_lbl_top = ui.label('0,00').classes('im-ktutar im-kgt')     # kalem toplami
                            ui.button(icon='close', on_click=lambda: remove_kalem(entry)).props(
                                'round dense flat color=grey size=sm').tooltip('Kalemi çıkar')
                    entry.update({'row': krow, 'kat': k_kat, 'matrah': k_matrah, 'kdv': k_kdv,
                                  'lbl_kdv': k_lbl_kdv, 'lbl_top': k_lbl_top})
                    k_matrah.on_value_change(lambda _: recalc())
                    k_kdv.on_value_change(lambda _: recalc())

                    # Kategori: klavyeyle acildiysa liste kapaninca, mouse ile secildiyse hemen -> Matrah
                    def _kat_hide():
                        if entry['nav']:
                            entry['nav'] = False
                            _matraha(entry)
                    k_kat.on('popup-hide', _kat_hide)

                    def _kat_changed():
                        if _kat_busy['v']:
                            return
                        _kategori_uyari()
                        if not entry['nav']:
                            _matraha(entry)
                    k_kat.on_value_change(lambda _: _kat_changed())

                    # Matrah Enter -> KDV listesi acilir; secince "yeni kalem eklensin mi?" (mouse akisi etkilenmez)
                    def _matrah_enter():
                        entry['kdv_nav'] = True
                        k_kdv.run_method('focus')
                        k_kdv.run_method('showPopup')
                    k_matrah.on('keydown.enter.prevent', _matrah_enter)

                    def _kdv_hide():
                        if entry['kdv_nav']:
                            entry['kdv_nav'] = False
                            _kalem_soru()
                    k_kdv.on('popup-hide', _kdv_hide)

                    kalemler_state.append(entry)
                    if not ilk:
                        recalc()
                    return entry

            # Duzenleme modunda doldur
            mevcut_grup_id = ''
            grup_created_at = ''
            if is_edit:
                inp_tarih.value = edit_row.get('tarih', '')
                inp_tur.value = edit_row.get('tur', 'GIDER')
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
                # Grup uyesi ise tum kalemleri yukle, degilse tek kalem
                mevcut_grup_id = edit_row.get('grup_id') or ''
                grup_rows = get_gelir_gider_grup(mevcut_grup_id) if mevcut_grup_id else []
                if grup_rows:
                    grup_created_at = grup_rows[0].get('created_at', '') or ''
                    for r in grup_rows:
                        add_kalem_row(r, ilk=True)
                else:
                    grup_created_at = edit_row.get('created_at', '') or ''
                    add_kalem_row(edit_row, ilk=True)
                recalc()
            else:
                # Yeni kayit: tek bos kalem + initial state
                add_kalem_row(ilk=True)
                on_durum_change(None)
                recalc()

            # Initial kategori uyari cek
            _kategori_uyari()

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    kalem_vals = []
                    for i, e in enumerate(kalemler_state, 1):
                        t, ko, kdv, top = _kalem_hesap(e)
                        kat = e['kat'].value or ''
                        if not kat:
                            notify_err(f'{i}. kalem: kategori seçmelisiniz')
                            return
                        if t <= 0:
                            notify_err(f'{i}. kalem: matrah 0\'dan büyük olmalı')
                            return
                        kalem_vals.append((e, kat, t, ko, kdv, top))
                    toplam = sum(v[5] for v in kalem_vals)

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

                    # Ortak (baslik) alanlar: tum kalemlerde ayni
                    ortak = {
                        'tarih': inp_tarih.value,
                        'tur': inp_tur.value,
                        'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        'odeme_sekli': odeme_sekli,
                        'firma_kod': firma_kod,
                        'firma_ad': firma_ad,
                        'odeme_durumu': odeme_durumu,
                        'vade_tarih': inp_vade.value if durum == 'ODENMEDI' else '',
                        'banka_hesap_id': banka_hesap_id,
                        'grup_id': mevcut_grup_id,
                    }
                    kalemler_data = []
                    for e, kat, t, ko, kdv, top in kalem_vals:
                        data = dict(ortak)
                        data.update({
                            'kategori': kat,
                            'tutar': t,
                            'kdv_orani': ko,
                            'kdv_tutar': kdv,
                            'toplam': top,
                        })
                        if e.get('gg_id'):
                            data['id'] = e['gg_id']
                        elif grup_created_at:
                            # Duzenlemede eklenen yeni kalem, grubun zaman damgasini alir
                            data['created_at'] = grup_created_at
                        kalemler_data.append(data)

                    try:
                        if is_edit:
                            save_gelir_gider_grup(kalemler_data, silinen_idler)
                            notify_ok('Kayıt güncellendi')
                        else:
                            _gid, gg_id = save_gelir_gider_grup(kalemler_data)

                            # Sadece KISMI odemede kasa kaydini burada olustur.
                            # ODENDI (tam) durumunda servis zaten grubun tek kasa kaydini
                            # olusturuyor -> mukerrer kayit olmasin diye buraya girme.
                            if odeme_durumu == 'KISMI':
                                kasa_tur = 'GELIR' if inp_tur.value == 'GELIR' else 'GIDER'
                                kat = kalemler_data[0]['kategori']
                                if len(kalemler_data) > 1:
                                    kat += f' +{len(kalemler_data) - 1}'
                                kasa_aciklama = f'{kat}'
                                if ortak['aciklama']:
                                    kasa_aciklama += f': {ortak["aciklama"]}'
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
                # Tarih -> Tur(liste) -> Cari -> [Kalem: Kategori(liste) -> Matrah -> KDV(liste) -> "yeni kalem?"]
                # -> Odeme Durumu kutusu -> (Vade | Banka -> Odenen | Odenen) -> Aciklama -> Kaydet
                def _js_focus(sel_css, select_all=False):
                    ui.run_javascript(
                        f"const el=[...document.querySelectorAll('{sel_css}')].pop();"
                        "if(el){el.focus();" + ("if(el.select)el.select();" if select_all else "") + "}")

                _nav = {'tur': False, 'cari': False, 'banka': False}

                def _ac(sel, flag):
                    _nav[flag] = True
                    sel.run_method('focus')
                    sel.run_method('showPopup')

                inp_tarih.on('keydown.enter.prevent', lambda: _ac(inp_tur, 'tur'))

                def _tur_hide():
                    if _nav['tur']:
                        _nav['tur'] = False
                        inp_firma.run_method('focus')
                inp_tur.on('popup-hide', _tur_hide)

                # Cari Enter -> ilk kalemin kategori listesi. Quasar ayni Enter'la cari listesini
                # ACAR (kapaliysa) / secimi bitirip KAPATIR; kapanis tamamlanmadan acilan liste
                # Quasar tarafindan kapatiliyor -> kategori listesi 'popup-hide' olayinda acilir.
                def _cari_enter():
                    _nav['cari'] = True
                    inp_firma.run_method('hidePopup')
                inp_firma.on('keydown.enter', _cari_enter)

                def _cari_hide():
                    if _nav['cari']:
                        _nav['cari'] = False
                        if kalemler_state:
                            _ac_kat(kalemler_state[0])
                inp_firma.on('popup-hide', _cari_hide)

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
        # Odenen/Vade/Aciklama Enter atlamalari, Kaydet<->Iptal ok gecisi
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

    def do_delete(row):
        if not isinstance(row, dict):
            row = {'id': row}
        grup_id = row.get('grup_id') or ''
        grup_rows = get_gelir_gider_grup(grup_id) if grup_id else []
        if len(grup_rows) > 1:
            n = len(grup_rows)

            def grup_confirmed():
                try:
                    delete_gelir_gider_grup(grup_id)
                    notify_ok(f'Kayıt silindi ({n} kalem)')
                    load_data()
                except Exception as e:
                    notify_err(f'Hata: {e}')
            confirm_dialog(
                f'Bu kayıt {n} kalemli bir işlem. Tamamı ({n} kalem) ve bağlı kasa kaydı silinecek. Emin misiniz?',
                grup_confirmed)
            return

        def confirmed():
            try:
                delete_gelir_gider(row['id'])
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
                
                kalemler = row.get('kalemler') or []
                if len(kalemler) > 1:
                    # Coklu kalemli islem: her kalem ayri satir (kategori — matrah + KDV = toplam)
                    for i, k in enumerate(kalemler, 1):
                        info_row(f'{i}. Kalem',
                                 f"{k.get('kategori', '')} — {fmt_para(k.get('tutar') or 0)}"
                                 f" + KDV %{int(k.get('kdv_orani') or 0)} = {fmt_para(k.get('toplam') or 0)} TL",
                                 is_mono=True)
                else:
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
                              on_click=lambda: (dlg.close(), do_delete(row))) \
                        .props('unelevated no-caps color=negative dense')
                        
        dlg.open()

    def on_donem_change(yil, ay):
        state['yil'] = yil
        state['ay'] = ay
        load_data()

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        all_rows = get_gelir_gider_list(yil=state['yil'], ay=state['ay'])
        grouped_rows = gelir_gider_grupla(all_rows)
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
                with ui.element('div').style('position:relative'):
                    ui.button('YENİ', icon='swap_vert', color='primary', on_click=lambda: open_dialog()).props('dense no-caps')
                    ui.label('F2').classes('gg-fhint')

        # F2 kisayolu: modal kapaliysa Yeni Gelir/Gider acar; acik modalda Kaydet'e tiklar
        def _gg_fkey(e):
            if (e.args or {}).get('key') == 'F2':
                open_dialog()
        ui.on('gg_fkey', _gg_fkey)
        ui.run_javascript('''
            if(!window.__ggFkeys){
                window.__ggFkeys = true;
                document.addEventListener('keydown', (e) => {
                    if(e.key !== 'F2') return;
                    const b = [...document.querySelectorAll('.q-dialog .im-btn-kaydet')].pop();
                    if(b){ e.preventDefault(); b.click(); return; }
                    if(document.querySelector('.q-dialog')) return;
                    e.preventDefault();
                    emitEvent('gg_fkey', {key: 'F2'});
                }, true);
            }
        ''')

        with ui.row().classes('w-full items-center gap-2 q-mb-xs').style('min-height: 32px'):
            back_button = ui.button(
                'Kategori Özetine Dön', icon='arrow_back', on_click=_back_to_kategori,
            ).props('dense flat no-caps color=primary')
            back_button.set_visibility(False)
            table_title = ui.label('Gelir / Gider Kayıtları').classes('text-subtitle2 text-weight-bold text-grey-8')

        # Table
        table_ref = ui.table(
            columns=normal_columns, rows=grouped_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
        ).classes('w-full gg-table').style('--table-extra-rows: 2;')
        table_ref.props('flat bordered dense')

        # Tek 'body' slot: hucre icerikleri + coklu kalemli kayitlar icin akordeon satiri.
        # Coklu kalemli satira tiklayinca kalemler acilir; digerlerinde detay modali (veya kategori detayi).
        import json as _json
        _kat_ikon_js = _json.dumps(KATEGORI_IKON, ensure_ascii=False)
        _fmt_js = "toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2})"
        body_slot = (r'''
    <q-tr :props="props"
          :class="props.expand && props.row.kalemler && props.row.kalemler.length > 1 ? 'gg-grup-acik' : ''"
          @click="props.row.kalemler && props.row.kalemler.length > 1 ? props.expand = !props.expand : $parent.$emit('rowdetail', props.row)">
        <q-td v-for="col in props.cols" :key="col.name" :props="props"
              :class="col.name === 'tarih' && !props.row.tarih ? 'tarihsiz-cell' : ''">
            <template v-if="col.name === 'tarih'">
                <span v-if="props.row.tarih" style="font-weight:700;font-size:11px;color:#334155;">{{ props.row.tarih.split('-').reverse().join('.') }}</span>
                <span v-else style="color:#b91c1c;font-weight:600;">⚠ TARİH YOK</span>
            </template>
            <template v-else-if="col.name === 'tur'">
                <q-chip dense :color="props.row.tur === 'GELIR' ? 'positive' : 'negative'" text-color="white" size="sm">
                    {{ props.row.tur === 'GELIR' ? 'Gelir' : 'Gider' }}
                </q-chip>
            </template>
            <template v-else-if="col.name === 'kategori'">
                <div style="display:flex;align-items:center;">
                    <q-icon v-if="props.row.kalemler && props.row.kalemler.length > 1"
                            :name="props.expand ? 'expand_less' : 'expand_more'"
                            size="16px" class="q-mr-xs text-primary" />
                    <span v-if="props.row.kalemler && props.row.kalemler.length > 1" class="text-weight-medium">
                        {{ props.row.kalemler.length }} kalem: {{ props.row.kategori }}
                    </span>
                    <span v-else>{{ props.row.kategori ? (((__IKONMAP__)[props.row.kategori] || '🏷️') + ' ' + props.row.kategori) : '' }}</span>
                </div>
            </template>
            <template v-else-if="col.name === 'firma_ad'">
                <span v-if="props.row.firma_ad" class="text-weight-medium text-indigo-8">{{ props.row.firma_ad }}</span>
                <span v-else class="text-grey-5">-</span>
            </template>
            <template v-else-if="col.name === 'toplam' || col.name === 'matrah'">
                {{ props.row[col.name] != null && props.row[col.name] !== 0
                    ? (props.row[col.name] < 0 ? '-' : '') + Math.abs(props.row[col.name]).__FMT__ + ' TL'
                    : '' }}
            </template>
            <template v-else-if="col.name === 'kdv'">
                {{ (Number(props.row.kdv) || 0).__FMT__ + ' TL' }}
            </template>
            <template v-else-if="col.name === 'yuzde'">
                <span class="text-weight-bold text-grey-8">%{{ Math.round(Number(props.row.yuzde) || 0) }}</span>
            </template>
            <template v-else-if="col.name === 'odeme_durumu'">
                <q-chip v-if="props.row.odeme_durumu === 'ODENMEDI'" dense color="red-7" text-color="white" size="sm" icon="schedule">
                    Ödenmedi
                </q-chip>
                <q-chip v-else-if="props.row.odeme_durumu === 'KISMI'" dense color="orange-8" text-color="white" size="sm" icon="hourglass_bottom">
                    Kısmi
                </q-chip>
                <q-chip v-else dense color="green-7" text-color="white" size="sm" icon="check">
                    Ödendi
                </q-chip>
            </template>
            <template v-else-if="col.name === 'actions'">
                <q-btn flat round dense icon="edit" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
            </template>
            <template v-else>{{ col.value }}</template>
        </q-td>
    </q-tr>
    <template v-if="props.row.kalemler && props.row.kalemler.length > 1 && props.expand">
        <q-tr v-for="(k, ki) in props.row.kalemler" :key="'kalem' + ki" :props="props" class="gg-kalem-tr">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'kategori'">
                    <span style="display:inline-flex;align-items:center;color:#334155;font-weight:600;font-size:12px;">
                        <q-icon name="subdirectory_arrow_right" size="14px" class="q-mr-xs text-grey-6" />
                        {{ ((__IKONMAP__)[k.kategori] || '🏷️') + ' ' + k.kategori }}
                    </span>
                </template>
                <template v-else-if="col.name === 'aciklama'">
                    <span style="font-size:11.5px;color:#64748b;">
                        Matrah {{ Number(k.tutar || 0).__FMT__ }} · KDV %{{ Math.round(Number(k.kdv_orani) || 0) }} = {{ Number(k.kdv_tutar || 0).__FMT__ }}
                    </span>
                </template>
                <template v-else-if="col.name === 'toplam'">
                    <span class="num-mono" style="font-size:12px;color:#0f766e;font-weight:700;">{{ Number(k.toplam || 0).__FMT__ + ' TL' }}</span>
                </template>
            </q-td>
        </q-tr>
    </template>
        ''').replace('__IKONMAP__', _kat_ikon_js).replace('__FMT__', _fmt_js)
        table_ref.add_slot('body', body_slot)

        table_ref.on('edit', lambda e: open_dialog(edit_row=e.args))
        table_ref.on('delete', lambda e: do_delete(e.args))
        table_ref.on('rowdetail', lambda e: _handle_table_row_click(e.args))

        # Islemler detay modalindan 'Kaynak -> kayda git' ile gelinince ilgili kaydi ac
        if focus:
            _rec = next((r for r in all_rows if str(r.get('id')) == str(focus)), None)
            if _rec:
                open_dialog(edit_row=_rec)
