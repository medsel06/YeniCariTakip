"""ALSE Plastik Hammadde - Alis/Satis Hareketleri Sayfasi"""
import re as _re
from datetime import date, datetime
from nicegui import ui
from layout import (
    create_layout, PARA_SLOT, MIKTAR_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog, donem_secici, donem_popover_btn, segment_group,
    fmt_para, fmt_miktar
)
from services.kasa_service import (
    get_hareketler_sayfa, delete_hareket,
    get_hareket_grup, save_hareket_grup, delete_hareket_grup,
    get_kasa_by_id, add_kasa, update_kasa, delete_kasa, get_kasa_silme_etkisi,
    get_kasa_kategoriler,
)

# Tur-bazli onerilen kategoriler (ön muhasebe)
GELIR_KATEGORILER = ['Satış Tahsilatı', 'Cari Tahsilat', 'Çek/Senet Tahsilatı', 'Avans Alınan',
                     'Kira Geliri', 'Faiz Geliri', 'İade/Geri Ödeme', 'Diğer Gelir']
GIDER_KATEGORILER = ['Tedarikçi Ödemesi', 'Cari Ödeme', 'Personel/Maaş', 'Kira', 'Elektrik', 'Su',
                     'Doğalgaz', 'Telefon/İnternet', 'Nakliye', 'Yakıt', 'Vergi/SGK',
                     'Kredi/Kredi Kartı', 'Ofis/Kırtasiye', 'Bakım/Onarım', 'Sigorta',
                     'Komisyon/Banka Masrafı', 'Diğer Gider']
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
    /* Sutun (dikey) cizgileri kaldirildi */
    .hrk-table td { border-right: none; }
    .hrk-table th { border-right: none; text-align: center !important; }
    /* Rakam sutunlari: orijinal font + tabular figures (hizali) + biraz kucuk */
    .hrk-table .num-mono { font-variant-numeric: tabular-nums; font-size: 12px; }
    /* Satırların tıklanabilir olduğunu belirten pointer */
    .hrk-table tbody tr { cursor: pointer; }
    /* Coklu kalem akordeonu: acik grup vurgusu — ana satir + kalemler tek blok gibi */
    .hrk-table tbody tr.hrk-grup-acik td { background: #e0f2fe !important; }
    .hrk-table tbody tr.hrk-kalem-tr td { background: #f0f9ff !important; }
    .hrk-table tbody tr.hrk-grup-acik td:first-child,
    .hrk-table tbody tr.hrk-kalem-tr td:first-child { box-shadow: inset 3px 0 0 #0284c7; }
    /* Detay modal bilgi satirlari: cerceveli, zebra desen */
    .modal-info { border: 1px solid #e8edf2; border-radius: 10px; overflow: hidden; }
    .modal-info .info-row { border-bottom: 1px solid #eef2f7; }
    .modal-info .info-row:last-child { border-bottom: none; }
    .modal-info .info-row:nth-child(odd) { background: #ffffff; }
    .modal-info .info-row:nth-child(even) { background: #f8fafc; }
    .modal-info .info-row:hover { background: #eef4fb; }

    /* ================= Yeni Islem modali — Compact (D4) =================
       Dogru teknik (arastirma): kalem hucreleri 'borderless' PROP ile cercevesiz
       (:before hack YOK); kompakt yukseklik NiceGUI #4393 recetesi ile. */
    .im-modal { font-size:12.5px; border-radius:14px; }
    /* Baslik: acik yesil bar, SABIT (alse-dialog "cocuklar kaysin" kuralini ez) */
    .im-modal .im-head { background:#f0fdf9; border-bottom:1px solid #d5efe6;
        padding:11px 18px; display:flex; align-items:center; gap:9px;
        width:100%; align-self:stretch; box-sizing:border-box;
        flex:0 0 auto !important; overflow:hidden !important; }
    .im-modal .im-head .im-ic { color:#059669; font-size:20px; }
    .im-modal .im-head .im-title { font-size:15px; font-weight:700; color:#0f172a; }
    .im-modal .im-head .im-sub { font-size:11px; font-weight:500; color:#7c9a92; }
    /* Govde: beyaz, dar dis bosluk, sikici satir araligi */
    .im-modal .im-body { background:#ffffff !important; padding:10px 16px !important; gap:6px !important; }
    .im-modal .im-body > .row, .im-modal .im-body > .nicegui-row { gap:8px !important; }
    /* Alan sarmalayici: etiket kutunun USTUNDE (D4 yapisi) */
    .im-modal .im-field { display:flex; flex-direction:column; gap:2px; min-width:0;
        background:transparent !important; padding:0 !important; }
    .im-modal .im-flabel { font-size:10px; font-weight:700; text-transform:uppercase;
        color:#64748b; letter-spacing:.03em; line-height:1.2; padding-left:1px; }
    /* Kutu cizgileri bir tik daha ince/acik (D4) */
    .im-modal .q-field--outlined .q-field__control:before { border-color:#dbe3ea !important; }

    /* --- KOMPAKT yukseklik recetesi (NiceGUI #4393): tum alanlar 34px --- */
    .im-modal .q-field--dense .q-field__control,
    .im-modal .q-field--dense .q-field__append,
    .im-modal .q-field--dense .q-field__control--addon { height:34px !important; min-height:34px !important; }
    .im-modal .q-field--dense .q-field__control-container { display:flex; align-items:center; }
    .im-modal .q-field--dense .q-field__native, .im-modal .q-field--dense .q-field__input {
        font-size:12.5px; min-height:32px; }
    /* Etiketler: gri, kucuk, UPPERCASE (cyan yerine); odakta yesil */
    .im-modal .q-field__label { color:#64748b !important; text-transform:uppercase;
        font-size:10px; letter-spacing:.03em; }
    .im-modal .q-field--focused .q-field__label { color:#059669 !important; }
    .im-modal .q-field--focused .q-field__control:after { border-color:#059669 !important; }

    /* --- Kalem tablosu: hizali sutunlar + basliklar + sabit 3-satir --- */
    .im-ktable { border:1px solid #e2e8f0; border-radius:9px; overflow:hidden; flex:0 0 auto; }
    .im-kthead { display:grid; grid-template-columns:1fr 66px 80px 48px 82px 82px 92px 26px;
        background:#f1f5f9; font-size:10px; font-weight:700; letter-spacing:.03em;
        text-transform:uppercase; color:#64748b; }
    .im-kthead > * { padding:5px 8px; }
    .im-kthead > *:nth-child(2), .im-kthead > *:nth-child(3),
    .im-kthead > *:nth-child(5), .im-kthead > *:nth-child(6),
    .im-kthead > *:nth-child(7) { text-align:right; }
    .im-kthead > *:nth-child(4) { text-align:center; }
    /* scrollbar-gutter:stable -> cubuk yeri HEP ayrilir, icerigi itmez; baslikta ayni bosluk */
    .im-kthead { padding-right:8px; }
    .im-kbody { min-height:99px; max-height:99px; overflow-y:auto; scrollbar-gutter:stable;
        scrollbar-width:thin; scrollbar-color:#dbe1e8 transparent; }
    .im-kbody::-webkit-scrollbar { width:8px; }
    .im-kbody::-webkit-scrollbar-thumb { background:#dbe1e8; border-radius:4px; }
    .im-kbody::-webkit-scrollbar-track { background:transparent; }
    /* Satir grid'i basligin grid'iyle ayni hizada baslasin: yatay padding 0 */
    .im-krow { display:grid; grid-template-columns:1fr 66px 80px 48px 82px 82px 92px 26px; gap:0;
        align-items:center; border-top:1px solid #eef2f6; padding:1px 0; }
    .im-krow:first-child { border-top:none; }
    .im-krow .q-field { width:100%; }
    /* Kalem alanlari: ULTRA-kompakt 30px (borderless prop cerceveyi zaten kaldirir) */
    .im-modal .im-krow .q-field--dense .q-field__control,
    .im-modal .im-krow .q-field--dense .q-field__append { height:30px !important; min-height:30px !important; }
    /* Hucre ic boslugu = baslik hucresiyle AYNI (8px) -> sutunlar hizali */
    .im-modal .im-krow .q-field__control { padding-left:8px !important; padding-right:8px !important; }
    .im-modal .im-krow .q-field__native, .im-modal .im-krow .q-field__input { text-align:right; padding:0 !important; }
    .im-modal .im-krow .q-select .q-field__native,
    .im-modal .im-krow .q-select input { text-align:left !important; }
    .im-modal .im-krow .q-field--focused .q-field__control { background:#f0fdf9 !important; }
    /* KDV hucresi: deger ortalanir (ok kaldirildi, basligin altinda durur) */
    .im-modal .im-krow .im-kkdv .q-field__native { text-align:center !important; justify-content:center; }
    /* Genel toplam vurgusu */
    .im-modal .im-kgt { color:#047857 !important; font-weight:800; }
    /* TUM select oklarini kaldir (zaten tiklayinca aciliyor) */
    .im-modal .q-select__dropdown-icon { display:none !important; }
    /* Hizli ekleme onay popup: SECILI buton cok belirgin (JS 'imsel' sinifi) */
    .im-confirm-card button.imsel { outline:3px solid #059669 !important; outline-offset:2px;
        box-shadow:0 0 0 4px rgba(5,150,105,.20) !important; }
    /* Alt bilgi: Enter/F2 ipucu */
    .im-enter-hint { font-size:10.5px; color:#94a3b8; white-space:nowrap; }
    /* Toolbar butonu altinda F-tusu etiketi (akisa girmez -> tabloyu itmez) */
    .hrk-fhint { position:absolute; top:100%; left:50%; transform:translateX(-50%);
        font-size:8.5px; color:#94a3b8; font-weight:700; letter-spacing:.5px;
        line-height:1; margin-top:2px; pointer-events:none; }
    .im-ktutar { text-align:right; font-weight:700; color:#0f766e; font-size:12.5px;
        font-variant-numeric:tabular-nums; padding-right:8px; }

    /* --- Toplam cubugu (acik) --- */
    .im-totbar { display:grid; grid-template-columns:repeat(4,1fr);
        background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; overflow:hidden; flex:0 0 auto; }
    .im-tot { padding:7px 12px; border-right:1px solid #e8edf3; }
    .im-tot:last-child { border-right:none; background:#ecfdf5; }
    .im-tot .tk { font-size:9.5px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:#8a97a6; }
    .im-tot:last-child .tk { color:#059669; }
    .im-tot .tv { font-size:14.5px; font-weight:800; color:#0f172a; font-variant-numeric:tabular-nums; }
    .im-tot:last-child .tv { color:#047857; }

    /* --- Odeme: toggle + alanlar YAN YANA (dikey uzama yok) --- */
    .im-odeme { display:flex; align-items:flex-end; gap:12px; flex-wrap:nowrap; }
    .im-odeme .im-octx { display:flex; gap:8px; flex:1; min-width:0; align-items:flex-end; }
    .im-vqbtns { display:flex; gap:5px; align-items:center; padding-bottom:3px; }

    /* Enter-akisi: Vadeli/Pesin sarici klavyeyle gelince belirgin kutu */
    .im-vpwrap { border:1px solid transparent; border-radius:10px; padding:1px 6px; outline:none; }
    .im-vpwrap:focus { border-color:#c7dbe8; background:#f6fafd; }
    /* Kaydet/Iptal klavye odagi belirgin olsun */
    .im-modal .im-btn-kaydet:focus, .im-modal .im-btn-iptal:focus {
        outline:2px solid #0891b2; outline-offset:2px; }

    /* Vadeli/Pesin: yesil KUTU toggle (D4 pill) */
    .im-modal .q-radio--checked .q-radio__inner { color:#059669 !important; }
    .im-modal .im-odeme .q-option-group { display:flex; gap:8px; }
    .im-modal .im-odeme .q-radio { border:1px solid #dbe1e8; border-radius:8px; padding:2px 10px; margin:0; }
    .im-modal .im-odeme .q-radio--checked { background:#e7f6ef; border-color:#059669; }
    .im-modal .im-odeme .q-radio__label { font-weight:600; font-size:12px; }
    .im-modal .im-odeme .q-radio__inner { font-size:22px; }  /* radio dairesini kucult */

    /* Firma + : yesil kare badge */
    .im-modal .im-addbadge { background:#e6f5f2 !important; color:#0f766e !important;
        width:34px; min-width:34px; height:34px; border-radius:8px; }
    .im-modal .im-addbadge:hover { background:#0f766e !important; color:#fff !important; }
    ''')

    table_ref = None
    # Sunucu tarafli sayfalama durumu (Quasar pagination nesnesiyle ayni anahtarlar)
    pag_state = {'page': 1, 'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
    # Varsayilan: bu yil (Kasa sayfasiyla ayni). Eskiden tum zamanlar cekilip
    # ~2000 satir her acilista tarayiciya gidiyordu; kullanici 'Tumu'ye gecebilir.
    state = {'yil': datetime.now().year, 'ay': None}

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

    def _sayfa_getir():
        """Mevcut donem/arama/tur/siralama/sayfa icin SADECE o sayfayi DB'den cek.
        (Eskiden tum liste cekilip Python'da filtreleniyor ve hepsi tarayiciya gidiyordu.)"""
        sort_by = pag_state.get('sortBy') or 'tarih'
        descending = bool(pag_state.get('descending')) if pag_state.get('sortBy') else True
        kw = dict(yil=state['yil'], ay=state['ay'], q=search_text['value'], tur=tur_filter['value'],
                  sort_by=sort_by, descending=descending, per_page=pag_state['rowsPerPage'])
        r = get_hareketler_sayfa(page=pag_state['page'], **kw)
        if not r['rows'] and r['total'] > 0 and pag_state['page'] > 1:
            # Sayfa bosaldi (orn. son kayit silindi) -> son dolu sayfaya cek
            per = pag_state['rowsPerPage'] if pag_state['rowsPerPage'] > 0 else r['total']
            pag_state['page'] = max(1, -(-r['total'] // max(1, per)))
            r = get_hareketler_sayfa(page=pag_state['page'], **kw)
        return r

    def apply_filters(reset_page=False):
        if reset_page:
            pag_state['page'] = 1
        r = _sayfa_getir()
        if table_ref:
            table_ref.rows = r['rows']
            table_ref.pagination = {**pag_state, 'rowsNumber': r['total']}
            table_ref.update()

    def load_data():
        apply_filters()

    def _on_table_request(e):
        """Quasar 'request' olayi: sayfa / sayfa boyutu / siralama degisti."""
        a = e.args
        if isinstance(a, list) and a:
            a = a[0]
        pag = a.get('pagination', a) if isinstance(a, dict) else {}
        for k in ('page', 'rowsPerPage', 'sortBy', 'descending'):
            if k in pag:
                pag_state[k] = pag[k]
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

        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 720px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('receipt_long' if not is_edit else 'drive_file_rename_outline').classes('im-ic')
                ui.label(title).classes('im-title')

            # Icerik alani kendi icinde kayar; buton satiri her zaman altta sabit kalir
            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # D4 gibi: Tarih + Fatura No + Tur + Tevkifat DORDU tek satirda (etiket kutu USTUNDE); altinda Firma
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TARİH').classes('im-flabel')
                        # native type=date: TR tarayicida gg.aa.yyyy + native takvim; deger yine YYYY-MM-DD
                        inp_tarih = ui.input(value=date.today().isoformat()).props('outlined dense type=date').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('İRSALİYE / FATURA NO').classes('im-flabel')
                        inp_belge = ui.input().props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('TÜR').classes('im-flabel')
                        inp_tur = ui.select(
                            options={'ALIS': 'Alış', 'SATIS': 'Satış'}, value='ALIS'
                        ).props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('TEVKİFAT').classes('im-flabel')
                        inp_tevkifat = ui.select(
                            options={'0': 'Yok', '2/10': '2/10', '5/10': '5/10', '7/10': '7/10', '9/10': '9/10'},
                            value='0'
                        ).props('outlined dense').classes('w-full')

                # Firma (etiket kutu USTUNDE, + kutu ICINDE) — ust satirla ayni sag kenar
                with ui.element('div').classes('im-field w-full'):
                    ui.label('FİRMA').classes('im-flabel')
                    inp_firma = ui.select(
                        options=firma_options, with_input=True, new_value_mode='add-unique'
                    ).props('outlined dense').classes('w-full')
                    with inp_firma.add_slot('append'):
                        ui.icon('add', size='20px').classes('cursor-pointer').style('color:#059669').on(
                            'click', lambda: open_mini_firma_dialog(inp_firma))

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

                # --- Urun kalemleri (coklu): her kalem ayri hareket satiri olur, grup_id ile baglanir ---
                kalemler_state = []   # {'row','urun','miktar','bf','lbl','hareket_id','created_at'}
                silinen_idler = []    # duzenlemede cikarilan kalemlerin hareket id'leri

                # --- TR sayi bicimleme: miktar duz (binlik nokta, gereksizse ondalik yok);
                #     birim fiyat / tutar 12.000,35 (binlik nokta + virgul ondalik) ---
                def _num_parse(s):
                    if s is None:
                        return 0.0
                    s = str(s).strip().replace(' ', '').replace('₺', '').replace('TL', '')
                    if not s:
                        return 0.0
                    if ',' in s:  # TR giris: nokta binlik, virgul ondalik
                        s = s.replace('.', '').replace(',', '.')
                    elif _re.fullmatch(r'-?\d{1,3}(\.\d{3})+', s):
                        # Virgul yok ama binlik desenli nokta(lar) var: "1.000" -> 1000
                        # (blur'daki _fmt_miktar binlik noktali yazar; float("1.000")=1.0 hatasini onler)
                        s = s.replace('.', '')
                    try:
                        return float(s)
                    except ValueError:
                        return 0.0

                def _tr_num(v, dec):
                    s = f"{abs(float(v or 0)):,.{dec}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    return ('-' if float(v or 0) < 0 else '') + s

                def _fmt_miktar(v):
                    v = float(v or 0)
                    return _tr_num(v, 0) if v == int(v) else _tr_num(v, 2)

                def _fmt_para(v):
                    return _tr_num(v, 2)

                # --- Klavye hizli akis: Enter=Tab; liste disi firma/urun icin Evet/Hayir onay ---
                def _quick_add_confirm(yer, value, on_yes, on_no):
                    with ui.dialog() as cdlg, ui.card().classes('q-pa-md im-confirm-card').style('min-width:360px;border-radius:12px'):
                        ui.label(f'"{value}"').classes('text-subtitle2 text-weight-bold').style('color:#0f766e')
                        ui.label(f'{yer} listesinde yok — eklensin mi?').classes('text-body2')
                        ui.label('Enter = Evet   ·   ← ile Hayır').classes('text-caption text-grey-6 q-mb-sm')
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Hayır', on_click=lambda: (cdlg.close(), on_no())).props('flat color=grey')
                            ui.button('Evet', on_click=lambda: (cdlg.close(), on_yes())).props('unelevated color=positive')
                    cdlg.open()
                    # JS: native Evet butonuna odaklan (run_method('focus') q-btn'de calismaz) + ok tuslari.
                    # 120ms gecikme -> popup'i acan Enter, Evet'i otomatik tetiklemez.
                    ui.timer(0.12, lambda: ui.run_javascript('''
                        const card = [...document.querySelectorAll('.im-confirm-card')].pop();
                        if(!card) return;
                        const btns = card.querySelectorAll('button');
                        if(btns.length < 2) return;
                        const noBtn = btns[0], yesBtn = btns[1];
                        const mark = (b) => { noBtn.classList.remove('imsel'); yesBtn.classList.remove('imsel');
                                              b.classList.add('imsel'); b.focus(); };
                        mark(yesBtn);
                        card.addEventListener('keydown', (e) => {
                            if(e.key === 'ArrowLeft'){ mark(noBtn); e.preventDefault(); }
                            else if(e.key === 'ArrowRight'){ mark(yesBtn); e.preventDefault(); }
                        });
                    '''), once=True)

                def _kalem_soru():
                    """KDV secildikten sonra Enter: yeni kalem eklensin mi? Enter=Evet, ←=Hayır(açıklamaya)."""
                    with ui.dialog() as kdlg, ui.card().classes('q-pa-md im-confirm-card').style('min-width:360px;border-radius:12px'):
                        ui.label('Yeni kalem eklensin mi?').classes('text-subtitle2 text-weight-bold').style('color:#0f766e')
                        ui.label('Enter = Hayır (açıklamaya geçer)   ·   → ile Evet').classes('text-caption text-grey-6 q-mb-sm')

                        def _evet():
                            kdlg.close()
                            add_kalem_row()
                            kalemler_state[-1]['urun'].run_method('focus')

                        def _hayir():
                            kdlg.close()
                            inp_aciklama.run_method('focus')

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

                def _focus_ilk_urun():
                    if kalemler_state:
                        kalemler_state[0]['urun'].run_method('focus')

                firma_kods0 = set(firma_options)   # gercek firma kodlari (yeni yazilanlar haric)
                urun_kods0 = set(urun_options)     # gercek urun kodlari
                _firma_busy = {'v': False}
                def _on_firma_change():
                    if _firma_busy['v']:
                        return
                    v = inp_firma.value
                    if not v:
                        return
                    if v in firma_kods0:           # gercek firma secildi -> urune gec
                        _focus_ilk_urun()
                        return
                    # liste disi yeni isim (new_value_mode ekledi) -> Evet/Hayir onay
                    yeni_ad = firma_options.get(v, v)
                    def _yes():
                        _firma_busy['v'] = True
                        kod = generate_firma_kod()
                        add_firma({'kod': kod, 'ad': yeni_ad})
                        firma_options.pop(v, None)
                        firma_options[kod] = yeni_ad
                        firma_kods0.add(kod)
                        inp_firma.set_options(firma_options, value=kod)
                        _firma_busy['v'] = False
                        notify_ok('Firma eklendi')
                        _focus_ilk_urun()
                    def _no():
                        _firma_busy['v'] = True
                        firma_options.pop(v, None)
                        inp_firma.set_options(firma_options, value=None)
                        _firma_busy['v'] = False
                    _quick_add_confirm('Firmalar', yeni_ad, _yes, _no)
                inp_firma.on_value_change(lambda: _on_firma_change())

                # Enter=Tab hizli akis: select odaga gelince liste ACILIR (ust secenek zaten secili).
                # Enter ustu secip kapatir -> bir sonraki select acilir. Enter-Enter ile hizli gecis.
                _sel_nav = {'active': False}
                def _ac_select(sel):
                    _sel_nav['active'] = True
                    sel.run_method('focus')
                    sel.run_method('showPopup')
                inp_tarih.on('keydown.enter.prevent', lambda: inp_belge.run_method('focus'))
                inp_belge.on('keydown.enter.prevent', lambda: _ac_select(inp_tur))
                def _tur_hide():
                    if _sel_nav['active']:
                        _sel_nav['active'] = False
                        _ac_select(inp_tevkifat)
                inp_tur.on('popup-hide', _tur_hide)
                def _tevk_hide():
                    if _sel_nav['active']:
                        _sel_nav['active'] = False
                        inp_firma.run_method('focus')
                inp_tevkifat.on('popup-hide', _tevk_hide)

                ui.label('Ürün Kalemleri').classes('text-caption text-weight-bold').style(
                    'color:#0e7490;letter-spacing:0.3px;')
                # Basliklı tablo + sabit 3-satir kaydirma alani (im-kbody). KDV her kalemde ayri sutun.
                with ui.element('div').classes('im-ktable w-full'):
                    with ui.element('div').classes('im-kthead'):
                        # Turkce buyuk harf elle yazilir (CSS uppercase 'i'->'I' bozuyor)
                        for _h in ('ÜRÜN', 'MİKTAR', 'B.FİYAT', 'KDV', 'MATRAH', 'KDV TUT.', 'GENEL TOPLAM', ''):
                            ui.label(_h)
                    kalemler_box = ui.element('div').classes('im-kbody')

                def remove_kalem(entry):
                    if len(kalemler_state) <= 1:
                        notify_err('En az bir kalem olmalı')
                        return
                    if entry.get('hareket_id'):
                        silinen_idler.append(entry['hareket_id'])
                    kalemler_state.remove(entry)
                    entry['row'].delete()
                    recalc()

                def add_kalem_row(kayit=None, ilk=False):
                    kayit = kayit or {}
                    entry = {'hareket_id': kayit.get('id'), 'created_at': kayit.get('created_at', '')}
                    _kdv0 = kayit.get('kdv_orani')
                    _kdv0 = int(_kdv0) if _kdv0 is not None else 20
                    if _kdv0 not in (0, 1, 10, 20):
                        _kdv0 = 20
                    with kalemler_box:
                        with ui.element('div').classes('im-krow') as krow:
                            k_urun = ui.select(
                                options=urun_options, with_input=True, new_value_mode='add-unique',
                                value=kayit.get('urun_kod') or None
                            ).props('borderless dense')
                            with k_urun.add_slot('append'):
                                ui.icon('add', size='16px').classes('cursor-pointer').style('color:#059669').on(
                                    'click', lambda _, s=k_urun: open_mini_urun_dialog(s))
                            # ui.input + TR bicim: miktar duz sayi, birim fiyat 12.000,35 (blur'da bicimlenir)
                            k_miktar = ui.input(
                                value=(_fmt_miktar(kayit['miktar']) if kayit.get('miktar') else None)
                            ).props('borderless dense placeholder="0" input-class=text-right')
                            k_bf = ui.input(
                                value=(_fmt_para(kayit['birim_fiyat']) if kayit.get('birim_fiyat') else None)
                            ).props('borderless dense placeholder="0,00" input-class=text-right')
                            k_kdv = ui.select(
                                options={0: '0', 1: '1', 10: '10', 20: '20'}, value=_kdv0
                            ).props('borderless dense').classes('im-kkdv')
                            k_lbl = ui.label('0,00').classes('im-ktutar')          # matrah
                            k_lbl_kdv = ui.label('0,00').classes('im-ktutar')      # kdv tutari
                            k_lbl_gt = ui.label('0,00').classes('im-ktutar im-kgt')  # genel toplam
                            ui.button(icon='close', on_click=lambda: remove_kalem(entry)).props(
                                'round dense flat color=grey size=sm').tooltip('Kalemi çıkar')
                    entry.update({'row': krow, 'urun': k_urun, 'miktar': k_miktar,
                                  'bf': k_bf, 'kdv': k_kdv, 'lbl': k_lbl,
                                  'lbl_kdv': k_lbl_kdv, 'lbl_gt': k_lbl_gt})
                    k_miktar.on_value_change(lambda _: recalc())
                    k_bf.on_value_change(lambda _: recalc())
                    k_kdv.on_value_change(lambda _: recalc())
                    k_miktar.on('blur', lambda _, el=k_miktar:
                                el.set_value(_fmt_miktar(_num_parse(el.value))) if el.value not in (None, '') else None)
                    k_bf.on('blur', lambda _, el=k_bf:
                            el.set_value(_fmt_para(_num_parse(el.value))) if el.value not in (None, '') else None)

                    # Enter = Tab (kalem ici): urun(secince)->miktar->b.fiyat->kdv; liste disi urun icin onay
                    _urun_busy = {'v': False}
                    def _on_urun_change():
                        if _urun_busy['v']:
                            return
                        v = k_urun.value
                        if not v:
                            return
                        if v in urun_kods0:        # gercek urun secildi -> miktara gec
                            k_miktar.run_method('focus')
                            return
                        yeni_ad = urun_options.get(v, v)
                        def _yes():
                            _urun_busy['v'] = True
                            kod = generate_urun_kod()
                            add_urun({'kod': kod, 'ad': yeni_ad, 'kategori': '', 'birim': 'KG'})
                            urun_options.pop(v, None)
                            urun_options[kod] = yeni_ad
                            urun_kods0.add(kod)
                            k_urun.set_options(urun_options, value=kod)
                            _urun_busy['v'] = False
                            notify_ok('Ürün eklendi')
                            k_miktar.run_method('focus')
                        def _no():
                            _urun_busy['v'] = True
                            urun_options.pop(v, None)
                            k_urun.set_options(urun_options, value=None)
                            _urun_busy['v'] = False
                        _quick_add_confirm('Stok', yeni_ad, _yes, _no)
                    k_urun.on_value_change(lambda: _on_urun_change())
                    k_miktar.on('keydown.enter.prevent', lambda: k_bf.run_method('focus'))

                    # B.fiyat Enter -> KDV listesi acilir (secili oran ustte); Enter secince
                    # "yeni kalem eklensin mi?" sorusu gelir. Mouse akisi etkilenmez (bayrak).
                    _kdv_nav = {'v': False}
                    def _bf_enter():
                        _kdv_nav['v'] = True
                        k_kdv.run_method('focus')
                        k_kdv.run_method('showPopup')
                    k_bf.on('keydown.enter.prevent', _bf_enter)
                    def _kdv_hide():
                        if _kdv_nav['v']:
                            _kdv_nav['v'] = False
                            _kalem_soru()
                    k_kdv.on('popup-hide', _kdv_hide)
                    kalemler_state.append(entry)
                    if not ilk:
                        recalc()

                ui.button('Kalem Ekle', icon='add', on_click=lambda: add_kalem_row()).props(
                    'dense flat no-caps color=green-7 size=sm').style('font-size:11px;padding:2px 6px')

                inp_aciklama = ui.input('Açıklama').props('outlined dense label-color=cyan-8').classes('w-full')

                # --- Ödeme türü: Vadeli (cariye borc/alacak) veya Peşin (ayni anda kasa/banka hareketi) ---
                # Kasa/Banka secenekleri (peSin icin): '' = nakit kasa, digerleri banka hesabi id
                pesin_hesap_opts = {'': 'Kasa (Nakit)'}
                pesin_banka_ad_by_id = {}
                for _b in list_banka_hesaplari(sadece_aktif=True):
                    _ad = (_b.get('ad') or '').strip()
                    if _ad:
                        pesin_hesap_opts[str(_b['id'])] = _ad
                        pesin_banka_ad_by_id[str(_b['id'])] = _ad

                # Odeme: toggle + baglamsal alanlar YAN YANA (dikey uzama/scroll yok)
                with ui.element('div').classes('im-odeme w-full q-mt-xs'):
                    # tabindex=-1: Enter-akisinda JS ile odaklanir; ok tuslari Vadeli/Pesin secer
                    with ui.element('div').classes('im-vpwrap').props('tabindex=-1') as vp_wrap:
                        inp_odeme_mod = ui.radio(
                            {'vadeli': 'Vadeli', 'pesin': 'Peşin'}, value='vadeli'
                        ).props('inline dense color=cyan-8')

                    # Vadeli: vade tarihi (native takvim, etiket ustte) + hizli vade
                    with ui.element('div').classes('im-octx') as vadeli_box:
                        with ui.element('div').classes('im-field').style('flex:0 0 160px'):
                            ui.label('VADE TARİHİ').classes('im-flabel')
                            inp_vade = ui.input().props('outlined dense type=date clearable').classes('w-full im-vade')

                        def _set_vade_gun(gun):
                            from datetime import datetime as _dt, timedelta as _td
                            base = inp_tarih.value or date.today().isoformat()
                            try:
                                b = _dt.strptime(str(base)[:10], '%Y-%m-%d').date()
                            except ValueError:
                                b = date.today()
                            inp_vade.set_value((b + _td(days=gun)).isoformat())

                        with ui.element('div').classes('im-vqbtns'):
                            ui.button('+7g', on_click=lambda: _set_vade_gun(7)).props('dense flat no-caps size=sm')
                            ui.button('+15g', on_click=lambda: _set_vade_gun(15)).props('dense flat no-caps size=sm')
                            ui.button('+30g', on_click=lambda: _set_vade_gun(30)).props('dense flat no-caps size=sm')

                    # Pesin: kasa/banka + odeme sekli + tutar (etiket USTTE, tutar TR bicim)
                    with ui.element('div').classes('im-octx') as pesin_box:
                        with ui.element('div').classes('im-field').style('flex:1;min-width:0'):
                            ui.label('KASA / BANKA').classes('im-flabel')
                            inp_pesin_hesap = ui.select(
                                options=pesin_hesap_opts, value=''
                            ).props('outlined dense').classes('w-full')
                        with ui.element('div').classes('im-field').style('flex:1;min-width:0'):
                            ui.label('ÖDEME ŞEKLİ').classes('im-flabel')
                            inp_pesin_odeme = ui.select(
                                options=['NAKIT', 'HAVALE', 'EFT', 'KK', 'CEK', 'DIGER'], value='NAKIT'
                            ).props('outlined dense').classes('w-full')
                        with ui.element('div').classes('im-field').style('flex:1;min-width:0'):
                            ui.label('TUTAR').classes('im-flabel')
                            inp_pesin_tutar = ui.input(value='').props(
                                'outlined dense input-class=text-right placeholder="0,00"').classes('w-full im-ptutar')
                            inp_pesin_tutar.on('blur', lambda _:
                                inp_pesin_tutar.set_value(_fmt_para(_num_parse(inp_pesin_tutar.value)))
                                if inp_pesin_tutar.value not in (None, '') else None)

                # Banka secilince odeme seklini otomatik HAVALE yap (nakit kalmasin)
                inp_pesin_hesap.on_value_change(
                    lambda e: (inp_pesin_odeme.set_value('HAVALE')
                               if (e.value and inp_pesin_odeme.value == 'NAKIT') else None))

                # Pesin tutar: kullanici elle degistirene kadar Fatura Toplam ile senkron
                _pesin_state = {'manuel': False, 'sync': False}

                def _on_pesin_tutar(_):
                    if not _pesin_state['sync']:
                        _pesin_state['manuel'] = True
                inp_pesin_tutar.on_value_change(_on_pesin_tutar)

                def _sync_pesin_tutar(kdvli_toplam):
                    if _pesin_state['manuel']:
                        return
                    _pesin_state['sync'] = True
                    inp_pesin_tutar.value = _fmt_para(kdvli_toplam)
                    _pesin_state['sync'] = False

                def _update_odeme_mod():
                    is_pesin = inp_odeme_mod.value == 'pesin'
                    vadeli_box.set_visibility(not is_pesin)
                    pesin_box.set_visibility(is_pesin)
                    if is_pesin:
                        _pesin_state['manuel'] = False
                        recalc()
                inp_odeme_mod.on_value_change(lambda _: _update_odeme_mod())
                pesin_box.set_visibility(False)

                # Hesaplama alani — acik toplam cubugu
                def fmt_tr(val):
                    s = f"{abs(val):,.2f}"
                    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                    return s

                def _tot_cell(baslik):
                    with ui.element('div').classes('im-tot'):
                        ui.label(baslik).classes('tk')
                        return ui.label('0,00').classes('tv')

                with ui.element('div').classes('im-totbar w-full'):
                    lbl_toplam = _tot_cell('MATRAH')
                    lbl_kdv_tutar = _tot_cell('KDV')
                    lbl_tevkifat = _tot_cell('TEVKİFAT')
                    lbl_kdvli = _tot_cell('FATURA TOPLAM')

                def recalc():
                    t_matrah = t_kdv = t_tevk = t_kdvli = 0.0
                    for k in kalemler_state:
                        # Her kalem kendi KDV oraniyla (miktar/bf TR string -> float)
                        matrah, kdv, tevk_tutar, odenecek_kdv, kdvli_toplam = hesapla(
                            _num_parse(k['miktar'].value), _num_parse(k['bf'].value), k['kdv'].value, inp_tevkifat.value
                        )
                        k['lbl'].set_text(fmt_tr(matrah))
                        k['lbl_kdv'].set_text(fmt_tr(kdv))
                        k['lbl_gt'].set_text(fmt_tr(kdvli_toplam))
                        t_matrah += matrah
                        t_kdv += kdv
                        t_tevk += tevk_tutar
                        t_kdvli += kdvli_toplam
                    lbl_toplam.set_text(fmt_tr(t_matrah))
                    lbl_kdv_tutar.set_text(fmt_tr(t_kdv))
                    lbl_tevkifat.set_text(fmt_tr(t_tevk) if t_tevk else '')  # tevkifat yoksa bos
                    lbl_kdvli.set_text(fmt_tr(t_kdvli) + ' ₺')
                    _sync_pesin_tutar(t_kdvli)

                inp_tevkifat.on_value_change(lambda _: recalc())

            # Duzenleme modunda mevcut degerleri doldur
            mevcut_grup_id = ''
            grup_created_at = ''
            if is_edit:
                inp_tarih.value = edit_row.get('tarih', '')
                inp_tur.value = edit_row.get('tur', 'ALIS')
                inp_firma.value = edit_row.get('firma_kod', '')
                inp_tevkifat.value = edit_row.get('tevkifat_orani', '0') or '0'
                inp_aciklama.value = edit_row.get('aciklama', '')
                inp_belge.value = edit_row.get('belge_no', '')
                inp_vade.value = edit_row.get('vade_tarih', '') or ''
                # Duzenlemede pesin odeme akisi yok — sadece vade alani gorunur
                inp_odeme_mod.set_visibility(False)
                pesin_box.set_visibility(False)
                vadeli_box.set_visibility(True)
                # Grup uyesi ise tum kalemleri yukle, degilse tek kalem
                mevcut_grup_id = edit_row.get('grup_id') or ''
                grup_rows = get_hareket_grup(mevcut_grup_id) if mevcut_grup_id else []
                if grup_rows:
                    grup_created_at = grup_rows[0].get('created_at', '') or ''
                    for r in grup_rows:
                        add_kalem_row(r, ilk=True)
                else:
                    add_kalem_row(edit_row, ilk=True)
                recalc()
                check_risk()
            else:
                add_kalem_row(ilk=True)
                recalc()

            # NOT: layout.py .alse-dialog kurali tum div cocuklara flex:1+overflow:auto verir;
            # buton satirinin kendi kaydirma cubugu olmamasi icin inline ile eziyoruz.
            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;'
                    'border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def save():
                    if not inp_tarih.value:
                        notify_err('Tarih seçmelisiniz')
                        return
                    if not inp_firma.value:
                        notify_err('Firma seçmelisiniz')
                        return
                    for i, k in enumerate(kalemler_state, 1):
                        if not k['urun'].value:
                            notify_err(f'{i}. kalemde ürün seçmelisiniz')
                            return
                        if _num_parse(k['miktar'].value) <= 0:
                            notify_err(f'{i}. kalemde miktar 0\'dan büyük olmalı')
                            return
                        if _num_parse(k['bf'].value) <= 0:
                            notify_err(f'{i}. kalemde birim fiyat 0\'dan büyük olmalı')
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

                    # Urun adlari (mini dialogla yeni eklenenler icin taze liste)
                    urun_ad_by_kod = dict(urun_options)
                    if any(k['urun'].value not in urun_ad_by_kod for k in kalemler_state):
                        for u in get_urun_list():
                            urun_ad_by_kod.setdefault(u['kod'], u['ad'])

                    # Pesin modu yalnizca yeni kayitta gecerli
                    is_pesin = (not is_edit) and inp_odeme_mod.value == 'pesin'
                    pesin_tutar = 0.0
                    if is_pesin:
                        pesin_tutar = _num_parse(inp_pesin_tutar.value)
                        if pesin_tutar <= 0:
                            notify_err('Peşin tutar 0\'dan büyük olmalı')
                            return

                    ortak = {
                        'tarih': inp_tarih.value,
                        'firma_kod': firma_kod,
                        'firma_ad': firma_ad,
                        'tur': inp_tur.value,
                        # kdv_orani artik kalem bazinda (asagida her kaleme yazilir)
                        'tevkifat_orani': inp_tevkifat.value or '0',
                        'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        'belge_no': inp_belge.value.strip() if inp_belge.value else '',
                        # Pesin secildiyse vade yok (ayni anda odendi/tahsil edildi)
                        'vade_tarih': '' if is_pesin else (inp_vade.value or '').strip(),
                    }

                    kalemler_data = []
                    for k in kalemler_state:
                        m = _num_parse(k['miktar'].value)
                        bf = _num_parse(k['bf'].value)
                        kdv_orani = float(k['kdv'].value or 0)
                        matrah, kdv, tevk_tutar, odenecek_kdv, kdvli_toplam = hesapla(
                            m, bf, kdv_orani, inp_tevkifat.value
                        )
                        data = dict(ortak)
                        data.update({
                            'urun_kod': k['urun'].value,
                            'urun_ad': urun_ad_by_kod.get(k['urun'].value, ''),
                            'miktar': m,
                            'birim_fiyat': bf,
                            'toplam': matrah,
                            'kdv_orani': kdv_orani,
                            'kdv_tutar': kdv,
                            'kdvli_toplam': kdvli_toplam,
                            'tevkifat_tutar': tevk_tutar,
                            'tevkifatsiz_kdv': odenecek_kdv,
                            'grup_id': mevcut_grup_id,
                        })
                        if k.get('hareket_id'):
                            data['id'] = k['hareket_id']
                        elif grup_created_at:
                            # Grup duzenlemede eklenen yeni kalem, grubun zaman damgasini alir
                            data['created_at'] = grup_created_at
                        kalemler_data.append(data)

                    try:
                        if is_edit:
                            save_hareket_grup(kalemler_data, silinen_idler)
                            notify_ok('İşlem güncellendi')
                        else:
                            save_hareket_grup(kalemler_data)
                            if is_pesin:
                                # Ayni anda kasa/banka hareketi: ALIS->Odeme(GIDER), SATIS->Tahsilat(GELIR)
                                _is_alis = (inp_tur.value == 'ALIS')
                                _hesap_id = inp_pesin_hesap.value or ''
                                if len(kalemler_data) == 1:
                                    _desc = kalemler_data[0]['urun_ad']
                                else:
                                    _desc = f"{len(kalemler_data)} kalem"
                                kasa_data = {
                                    'tarih': inp_tarih.value,
                                    'firma_kod': firma_kod,
                                    'firma_ad': firma_ad,
                                    'tur': 'GIDER' if _is_alis else 'GELIR',
                                    'tutar': pesin_tutar,
                                    'odeme_sekli': inp_pesin_odeme.value or 'NAKIT',
                                    'banka_hesap_id': int(_hesap_id) if _hesap_id else None,
                                    'banka': pesin_banka_ad_by_id.get(_hesap_id, ''),
                                    'kategori': 'Tedarikçi Ödemesi' if _is_alis else 'Satış Tahsilatı',
                                    'aciklama': (f"{'Alış peşin ödeme' if _is_alis else 'Satış peşin tahsilat'}"
                                                 f" — {_desc}".strip(' —')),
                                }
                                add_kasa(kasa_data)
                                notify_ok('İşlem eklendi + ' +
                                          ('ödeme yapıldı' if _is_alis else 'tahsilat yapıldı'))
                            else:
                                notify_ok('İşlem eklendi')
                        dlg.close()
                        load_data()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

                # --- Enter-akisi kablolari (sunucu tarafi): aciklama -> Vadeli/Peşin -> pesin zinciri ---
                # Ok tuslari + Enter->Kaydet odaklari gecikmesiz olsun diye CLIENT-SIDE JS'te
                # (dlg.open() sonrasi kurulur); burada sadece popup/logic gerektirenler var.
                def _js_focus(sel_css, select_all=False):
                    ui.run_javascript(
                        f"const el=[...document.querySelectorAll('{sel_css}')].pop();"
                        "if(el){el.focus();" + ("if(el.select)el.select();" if select_all else "") + "}")

                def _aciklama_enter():
                    if is_edit:
                        inp_vade.run_method('focus')   # duzenlemede pesin akisi yok
                    else:
                        _js_focus('.im-vpwrap')
                inp_aciklama.on('keydown.enter.prevent', _aciklama_enter)

                _pesin_nav = {'hesap': False, 'odeme': False}

                def _vp_enter():
                    if inp_odeme_mod.value == 'pesin':
                        _pesin_nav['hesap'] = True
                        inp_pesin_hesap.run_method('focus')
                        inp_pesin_hesap.run_method('showPopup')
                    else:
                        inp_vade.run_method('focus')
                vp_wrap.on('keydown.enter.prevent', _vp_enter)

                # Pesin zinciri: kasa/banka secilince odeme sekli acilir, o secilince tutara gecilir
                def _hesap_hide():
                    if _pesin_nav['hesap']:
                        _pesin_nav['hesap'] = False
                        _pesin_nav['odeme'] = True
                        inp_pesin_odeme.run_method('focus')
                        inp_pesin_odeme.run_method('showPopup')
                inp_pesin_hesap.on('popup-hide', _hesap_hide)

                def _odeme_hide():
                    if _pesin_nav['odeme']:
                        _pesin_nav['odeme'] = False
                        # Tutar dolu gelir; tumu secili odaklanir (yazinca ustune yazar, Enter ile gecer)
                        _js_focus('.im-modal .im-ptutar input', select_all=True)
                inp_pesin_odeme.on('popup-hide', _odeme_hide)
        dlg.open()
        # Modal acilinca odak dogrudan Tarih'e
        ui.timer(0.2, lambda: inp_tarih.run_method('focus'), once=True)
        # Klavye akisi (CLIENT-SIDE, sunucu gecikmesi yok):
        # - Vadeli/Pesin kutusunda ← → radio degistirir (click ile sunucuya da senkron olur)
        # - Vade/Tutar'da Enter aninda Kaydet'e odaklanir (tek Enter ile kaydeder)
        # - Kaydet ← Iptal, Iptal → Kaydet
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__enterFlow) return;
            modal.__enterFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const vp = modal.querySelector('.im-vpwrap');
            if(vp) vp.addEventListener('keydown', (e) => {
                const r = vp.querySelectorAll('.q-radio');
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(r[0]) r[0].click(); vp.focus(); }
                else if(e.key === 'ArrowRight'){ e.preventDefault(); if(r[1]) r[1].click(); vp.focus(); }
            });
            const vadeInp = modal.querySelector('.im-vade input');
            if(vadeInp) vadeInp.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
            const tutarInp = modal.querySelector('.im-ptutar input');
            if(tutarInp) tutarInp.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

    def do_edit(row):
        open_hareket_dialog(edit_row=row)

    def do_delete(row):
        grup_id = row.get('grup_id') or ''
        grup_rows = get_hareket_grup(grup_id) if grup_id else []
        if len(grup_rows) > 1:
            def grup_confirmed():
                try:
                    delete_hareket_grup(grup_id)
                    notify_ok(f'İşlem silindi ({len(grup_rows)} kalem)')
                    load_data()
                except Exception as e:
                    notify_err(f'Hata: {e}')
            confirm_dialog(
                f'Bu satır {len(grup_rows)} kalemli bir işlemin parçası. '
                f'İşlemin tamamı ({len(grup_rows)} kalem) silinecek. Emin misiniz?',
                grup_confirmed)
            return

        def confirmed():
            try:
                delete_hareket(row['id'])
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

        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 600px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('payments' if tur_default == 'GELIR' else 'shopping_cart_checkout').classes('im-ic')
                ui.label(baslik).classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Tarih + Tur
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TARİH').classes('im-flabel')
                        inp_tarih = ui.input(value=tarih_default).props(
                            'outlined dense type=date').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('TÜR').classes('im-flabel')
                        inp_tur = ui.select(
                            options={'GELIR': 'Tahsilat', 'GIDER': 'Ödeme'}, value=tur_default
                        ).props('outlined dense').classes('w-full')

                # Firma
                with ui.element('div').classes('im-field w-full'):
                    ui.label('FİRMA').classes('im-flabel')
                    inp_firma = ui.select(
                        options=firma_opts, value=firma_kod_default if firma_kod_default in firma_opts else '',
                        with_input=True,
                    ).props('outlined dense').classes('w-full kd-firma')

                # Satir: Tutar + Odeme Sekli + Banka
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 140px'):
                        ui.label('TUTAR (TL)').classes('im-flabel')
                        inp_tutar = ui.number(value=tutar_default, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full kd-tutar')
                    with ui.element('div').classes('im-field col'):
                        ui.label('ÖDEME ŞEKLİ').classes('im-flabel')
                        inp_odeme = ui.select(
                            options=['NAKIT', 'HAVALE', 'EFT', 'KK', 'CEK', 'DIGER'],
                            value=odeme_default if odeme_default in ['NAKIT', 'HAVALE', 'EFT', 'KK', 'CEK', 'DIGER'] else 'NAKIT',
                        ).props('outlined dense').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('BANKA').classes('im-flabel')
                        inp_banka = ui.select(
                            options=banka_opts,
                            value=banka_sel_default,
                            on_change=lambda e: (inp_odeme.set_value('HAVALE')
                                                 if (e.value and inp_odeme.value == 'NAKIT') else None),
                        ).props('outlined dense').classes('w-full')

                # Kategori
                _db_kats = get_kasa_kategoriler()

                def _kat_opts(tur):
                    base = GELIR_KATEGORILER if tur == 'GELIR' else GIDER_KATEGORILER
                    out = []
                    for k in base + _db_kats:
                        if k and k not in out:
                            out.append(k)
                    if kategori_default and kategori_default not in out:
                        out.append(kategori_default)
                    return out

                with ui.element('div').classes('im-field w-full'):
                    ui.label('KATEGORİ').classes('im-flabel')
                    inp_kategori = ui.select(
                        options=_kat_opts(tur_default), value=kategori_default or None,
                        with_input=True,
                    ).props('outlined dense new-value-mode=add-unique clearable').classes('w-full kd-kategori')

                def _sync_kat_opts(_=None):
                    opts = _kat_opts(inp_tur.value)
                    cur = inp_kategori.value
                    if cur and cur not in opts:
                        opts = opts + [cur]
                    inp_kategori.set_options(opts)
                inp_tur.on_value_change(_sync_kat_opts)

                # Aciklama
                with ui.element('div').classes('im-field w-full'):
                    ui.label('AÇIKLAMA').classes('im-flabel')
                    inp_aciklama = ui.input(value=aciklama_default).props(
                        'outlined dense').classes('w-full kd-aciklama')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

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

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

                # Enter akisi (sunucu: popup zinciri): Tarih -> Tur -> Firma -> Tutar
                # -> Odeme Sekli -> (HAVALE/EFT: Banka) -> Kategori -> Aciklama -> Kaydet
                _knav = {'tur': False, 'odeme': False, 'banka': False}

                def _kac(sel, flag):
                    _knav[flag] = True
                    sel.run_method('focus')
                    sel.run_method('showPopup')

                inp_tarih.on('keydown.enter.prevent', lambda: _kac(inp_tur, 'tur'))

                def _ktur_hide():
                    if _knav['tur']:
                        _knav['tur'] = False
                        inp_firma.run_method('focus')
                inp_tur.on('popup-hide', _ktur_hide)

                inp_tutar.on('keydown.enter.prevent', lambda: _kac(inp_odeme, 'odeme'))

                def _kodeme_hide():
                    if _knav['odeme']:
                        _knav['odeme'] = False
                        if inp_odeme.value in ('HAVALE', 'EFT'):
                            _kac(inp_banka, 'banka')
                        else:
                            inp_kategori.run_method('focus')
                inp_odeme.on('popup-hide', _kodeme_hide)

                def _kbanka_hide():
                    if _knav['banka']:
                        _knav['banka'] = False
                        inp_kategori.run_method('focus')
                inp_banka.on('popup-hide', _kbanka_hide)
        dlg.open()
        # Acilinca odak Tarih'e
        ui.timer(0.2, lambda: inp_tarih.run_method('focus'), once=True)
        # Klavye akisi (CLIENT-SIDE): firma->tutar, kategori->aciklama, aciklama->Kaydet
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__kdFlow) return;
            modal.__kdFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const go = (sel, selAll) => { const el = modal.querySelector(sel);
                if(el){ el.focus(); if(selAll && el.select) el.select(); } };
            const firma = modal.querySelector('.kd-firma input');
            if(firma) firma.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ setTimeout(() => go('.kd-tutar input', true), 80); }
            });
            const kat = modal.querySelector('.kd-kategori input');
            if(kat) kat.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ setTimeout(() => go('.kd-aciklama input'), 80); }
            });
            const acik = modal.querySelector('.kd-aciklama input');
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
                def info_row(label, value, is_mono=False, extra_style='', on_click=None):
                    if value is None or value == '':
                        value = '-'
                    bg = '#f1f5f9' if _ridx['i'] % 2 else '#ffffff'
                    _ridx['i'] += 1
                    cls = 'w-full justify-between items-center no-wrap info-row'
                    if on_click:
                        cls += ' cursor-pointer'
                    rw = ui.row().classes(cls).style(f'background:{bg};padding:9px 14px;')
                    if on_click:
                        rw.on('click', on_click)
                    with rw:
                        ui.label(label).classes('uppercase').style('font-size:11px;font-weight:700;color:#64748b;letter-spacing:0.5px;')
                        if on_click:
                            with ui.row().classes('items-center gap-1 no-wrap'):
                                ui.label(str(value)).classes('text-right').style('font-size:13.5px;font-weight:700;color:#2563eb;' + extra_style)
                                ui.icon('open_in_new').style('font-size:15px;color:#2563eb;')
                        else:
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
                    kalemler = row.get('kalemler') or []
                    if len(kalemler) > 1:
                        # Coklu kalemli islem: her kalem ayri satir
                        for i, k in enumerate(kalemler, 1):
                            info_row(f'{i}. Kalem',
                                     f"{k.get('urun_ad', '')} — {fmt_miktar(k.get('miktar') or 0)}"
                                     f" x {fmt_para(k.get('birim_fiyat') or 0)}"
                                     f" = {fmt_para(k.get('kdvli_toplam') or 0)} TL",
                                     is_mono=True)
                    else:
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
                        
                    # Kasa Kaynak Bilgisi (ilgili kayda gidilebilir)
                    kaynak = row.get('kasa_kaynak', '')
                    if kaynak:
                        if kaynak == 'gelir_gider':
                            gg_id = row.get('gelir_gider_id')
                            if gg_id:
                                info_row('Kaynak', 'Gelir/Gider kaydına git',
                                         on_click=lambda g=gg_id: (dlg.close(), ui.navigate.to(f'/gelir-gider?focus={g}')))
                            else:
                                info_row('Kaynak', 'Gelir/Gider Modülü')
                        elif kaynak == 'cek':
                            c_id = row.get('cek_id')
                            if c_id:
                                info_row('Kaynak', 'Çek/Senet kaydına git',
                                         on_click=lambda c=c_id: (dlg.close(), ui.navigate.to(f'/cekler?focus={c}')))
                            else:
                                info_row('Kaynak', 'Çek/Senet Modülü')
                        else:
                            info_row('Kaynak', 'Serbest Kasa Kaydı')
                        
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
                                  on_click=lambda: (dlg.close(), do_delete(row))) \
                            .props('unelevated no-caps color=negative dense')
                    else: # KASA
                        ui.button('Düzenle', icon='edit', 
                                  on_click=lambda: (dlg.close(), do_edit_kasa(row))) \
                            .props('unelevated no-caps color=primary dense')
                        ui.button('Sil', icon='delete', 
                                  on_click=lambda: (dlg.close(), do_delete_kasa(row))) \
                            .props('unelevated no-caps color=negative dense')
                            
        dlg.open()

    # --- Body slot ---
    # Satir arka plan rengi: tarih bos ise kirmizi (tarihsiz uyarisi),
    # aksi halde tur'e gore cok hafif tint
    _rcls = "(!props.row.tarih)?'hrk-tarihsiz':props.row.tur==='ALIS'?'hrk-alis':props.row.tur==='SATIS'?'hrk-satis':props.row.tur==='TAHSILAT'?'hrk-tahsilat':props.row.tur==='ODEME'?'hrk-odeme':''"

    # Tek 'body' slot: hucre icerikleri + coklu kalemli islemler icin akordeon satiri.
    # Coklu kalemli satira tiklayinca kalemler acilir; digerlerinde detay modali acilir.
    body_slot = (r'''
    <q-tr :props="props"
          :class="props.expand && props.row.kalemler && props.row.kalemler.length > 1 ? 'hrk-grup-acik' : ''"
          @click="props.row.kalemler && props.row.kalemler.length > 1 ? props.expand = !props.expand : $parent.$emit('rowdetail', props.row)">
        <q-td v-for="col in props.cols" :key="col.name" :props="props" :class="''' + _rcls + r'''">
            <template v-if="col.name === 'tarih'">
                <span v-if="props.row.tarih" style="font-weight:700;font-size:11px;color:#334155;">{{ props.row.tarih.split('-').reverse().join('.') }}</span>
                <span v-else style="color:#7f1d1d;font-weight:700;">⚠ TARİH YOK</span>
            </template>
            <template v-else-if="col.name === 'tur'">
                <span style="display:inline-block;padding:2px 10px;border-radius:999px;font-weight:700;font-size:11px;letter-spacing:0.2px;"
                    :style="props.row.tur === 'ALIS' ? 'background:#e0e7ff;color:#4338ca;' :
                            props.row.tur === 'SATIS' ? 'background:#dcfce7;color:#15803d;' :
                            props.row.tur === 'TAHSILAT' ? 'background:#cffafe;color:#0e7490;' :
                            props.row.tur === 'ODEME' ? 'background:#ffe4e6;color:#be123c;' : 'background:#f1f5f9;color:#475569;'">
                    {{ props.row.tur === 'ALIS' ? 'Alış' :
                       props.row.tur === 'SATIS' ? 'Satış' :
                       props.row.tur === 'TAHSILAT' ? 'Tahsilat' :
                       props.row.tur === 'ODEME' ? 'Ödeme' : props.row.tur }}
                </span>
            </template>
            <template v-else-if="col.name === 'urun_ad'">
                <div style="display:flex;align-items:center;">
                    <q-icon v-if="props.row.kalemler && props.row.kalemler.length > 1"
                            :name="props.expand ? 'expand_less' : 'expand_more'"
                            size="16px" class="q-mr-xs text-primary" />
                    <div style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        {{ props.row.urun_ad }}
                        <q-tooltip v-if="props.row.urun_ad && String(props.row.urun_ad).length > 18"
                            anchor="top middle" self="bottom middle"
                            style="font-size:12.5px;max-width:360px;white-space:normal;background:#1e293b;">
                            {{ props.row.urun_ad }}
                        </q-tooltip>
                    </div>
                </div>
            </template>
            <template v-else-if="col.name === 'firma_ad' || col.name === 'aciklama'">
                <div :style="'max-width:' + (col.name === 'firma_ad' ? 170 : 200) + 'px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'">
                    {{ props.row[col.name] }}
                    <q-tooltip v-if="props.row[col.name] && String(props.row[col.name]).length > (col.name === 'firma_ad' ? 22 : 26)"
                        anchor="top middle" self="bottom middle"
                        style="font-size:12.5px;max-width:360px;white-space:normal;background:#1e293b;">
                        {{ props.row[col.name] }}
                    </q-tooltip>
                </div>
            </template>
            <template v-else-if="col.name === 'miktar'">
                <span class="num-mono">{{ props.row.miktar != null && props.row.miktar !== 0 ? Number(props.row.miktar).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}</span>
            </template>
            <template v-else-if="col.name === 'birim_fiyat' || col.name === 'toplam' || col.name === 'kdvli_toplam'">
                <span class="num-mono">{{ props.row[col.name] != null && props.row[col.name] !== 0
                    ? (props.row[col.name] < 0 ? '-' : '') + Math.abs(props.row[col.name]).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                    : '' }}</span>
            </template>
            <template v-else-if="col.name === 'tevkifat_orani'">
                <q-badge v-if="props.row.tevkifat_orani && props.row.tevkifat_orani !== '0'" color="orange-8" text-color="white" dense>
                    {{ props.row.tevkifat_orani }}
                </q-badge>
                <span v-else class="text-grey-5">-</span>
            </template>
            <template v-else-if="col.name === 'actions'">
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
            </template>
            <template v-else>{{ col.value }}</template>
        </q-td>
    </q-tr>
    <template v-if="props.row.kalemler && props.row.kalemler.length > 1 && props.expand">
        <q-tr v-for="(k, ki) in props.row.kalemler" :key="'kalem' + ki" :props="props" class="hrk-kalem-tr">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'urun_ad'">
                    <span style="display:inline-flex;align-items:center;color:#334155;font-weight:600;font-size:12px;">
                        <q-icon name="subdirectory_arrow_right" size="14px" class="q-mr-xs text-grey-6" />
                        {{ k.urun_ad }}
                    </span>
                </template>
                <template v-else-if="col.name === 'miktar'">
                    <span class="num-mono" style="font-size:12px;color:#475569;">{{ k.miktar != null ? Number(k.miktar).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}</span>
                </template>
                <template v-else-if="col.name === 'birim_fiyat'">
                    <span class="num-mono" style="font-size:12px;color:#475569;">{{ k.birim_fiyat != null ? Number(k.birim_fiyat).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}</span>
                </template>
                <template v-else-if="col.name === 'toplam'">
                    <span class="num-mono" style="font-size:12px;color:#475569;">{{ k.miktar != null && k.birim_fiyat != null ? (Number(k.miktar) * Number(k.birim_fiyat)).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}</span>
                </template>
                <template v-else-if="col.name === 'kdvli_toplam'">
                    <span class="num-mono" style="font-size:12px;color:#0f766e;font-weight:700;">{{ k.kdvli_toplam != null ? Number(k.kdvli_toplam).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}</span>
                </template>
            </q-td>
        </q-tr>
    </template>
    ''')

    # --- PAGE CONTENT ---
    with ui.column().classes('w-full q-pa-sm'):
        ilk_sayfa = _sayfa_getir()

        def on_tur_change(new_tur):
            tur_filter['value'] = new_tur
            apply_filters(reset_page=True)

        def on_search_change(e):
            search_text['value'] = e.value or ''
            apply_filters(reset_page=True)

        with ui.row().classes('w-full items-center gap-2 q-mb-xs'):
            search_input = ui.input(
                placeholder='Ara (firma, ürün, tür)...',
                on_change=on_search_change,
            ).props('outlined dense clearable debounce=250').classes('w-64')

            def _donem_changed(yil, ay):
                state['yil'] = yil
                state['ay'] = ay
                load_data()

            donem_popover_btn(_donem_changed, default_mode='YIL')
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
            with ui.element('div').style('position:relative'):
                ui.button('TAHSİLAT', icon='account_balance_wallet', color='positive',
                          on_click=lambda: open_kasa_dialog(default_tur='GELIR')).props('unelevated dense no-caps')
                ui.label('F6').classes('hrk-fhint')
            with ui.element('div').style('position:relative'):
                ui.button('ÖDEME', icon='credit_card', color='warning',
                          on_click=lambda: open_kasa_dialog(default_tur='GIDER')).props('unelevated dense no-caps')
                ui.label('F7').classes('hrk-fhint')
            with ui.element('div').style('position:relative'):
                ui.button('İŞLEM', icon='receipt_long', color='primary',
                          on_click=lambda: open_hareket_dialog()).props('unelevated dense no-caps')
                ui.label('F5').classes('hrk-fhint')

        # F-tusu kisayollari: F5=Yeni Islem, F6=Yeni Tahsilat, F7=Yeni Odeme,
        # F2=acik modalda Kaydet (client-side tiklanir, cift kayit olmaz)
        def _fkey(e):
            k = (e.args or {}).get('key')
            if k == 'F5':
                open_hareket_dialog()
            elif k == 'F6':
                open_kasa_dialog(default_tur='GELIR')
            elif k == 'F7':
                open_kasa_dialog(default_tur='GIDER')
        ui.on('hrk_fkey', _fkey)
        ui.run_javascript('''
            if(!window.__hrkFkeys){
                window.__hrkFkeys = true;
                document.addEventListener('keydown', (e) => {
                    if(e.key === 'F2'){
                        const b = [...document.querySelectorAll('.q-dialog .im-btn-kaydet')].pop();
                        if(b){ e.preventDefault(); b.click(); }
                        return;
                    }
                    if(['F5','F6','F7'].includes(e.key)){
                        e.preventDefault();
                        if(document.querySelector('.q-dialog')) return;
                        emitEvent('hrk_fkey', {key: e.key});
                    }
                }, true);
            }
        ''')

        # Tablo
        # rowsNumber verildiginde Quasar sunucu tarafli moda gecer: sayfa/siralama
        # degisince 'request' olayi yayar, satirlari biz doldururuz.
        table_ref = ui.table(
            columns=columns, rows=ilk_sayfa['rows'], row_key='id',
            pagination={**pag_state, 'rowsNumber': ilk_sayfa['total']}
        ).classes('w-full hrk-table').style('--table-extra-rows: 3;')
        table_ref.props('flat bordered dense')
        table_ref.on('request', _on_table_request)

        # Slot: tek body (hucreler + akordeon kalem satiri)
        table_ref.add_slot('body', body_slot)

        table_ref.on('edit', lambda e: do_edit(e.args))
        table_ref.on('delete', lambda e: do_delete(e.args))
        table_ref.on('edit_kasa', lambda e: do_edit_kasa(e.args))
        table_ref.on('delete_kasa', lambda e: do_delete_kasa(e.args))
        table_ref.on('rowdetail', lambda e: _show_row_detail(e.args))



