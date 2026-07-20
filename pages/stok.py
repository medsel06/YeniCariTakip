"""Cari Takip - Stok Sayfasi"""
from nicegui import ui
from layout import create_layout, fmt_miktar, MIKTAR_SLOT, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, confirm_dialog, normalize_search, IM_MODAL_CSS, f2_kisayolu
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
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'left', 'sortable': False},
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

        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 520px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('inventory_2').classes('im-ic')
                ui.label('Yeni Ürün Ekle').classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Kod (readonly) + Urun Adi
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 110px'):
                        ui.label('ÜRÜN KODU').classes('im-flabel')
                        inp_kod = ui.input(value=auto_kod).props('outlined dense readonly').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('ÜRÜN ADI').classes('im-flabel')
                        inp_ad = ui.input().props('outlined dense').classes('w-full st-ad')
                # Satir 2: Kategori + Birim
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('KATEGORİ').classes('im-flabel')
                        inp_kat = ui.select(
                            options=kategoriler, with_input=True, new_value_mode='add-unique'
                        ).props('outlined dense clearable').classes('w-full st-kat')
                    with ui.element('div').classes('im-field').style('flex:0 0 130px'):
                        ui.label('BİRİM').classes('im-flabel')
                        inp_birim = ui.select(
                            options=['KG', 'ADET', 'METRE', 'LITRE', 'PAKET', 'M3'], value='KG'
                        ).props('outlined dense').classes('w-full')
                # Quasar bug fix: kullanici yeni kategori yazip Enter basmadan Kaydet'e
                # tiklarsa input-value commit edilmiyor. input-value event'i ile son
                # yazilan text'i yakaliyoruz, save'de fallback olarak kullaniyoruz.
                _kat_pending = {'text': ''}
                inp_kat.on('input-value', lambda e: _kat_pending.update({'text': str(e.args or '').strip()}))

                # DESİ alani (sadece uretim takibi aciksa)
                _ayar = get_company_settings()
                inp_desi = None
                if _ayar.get('uretim_takibi'):
                    with ui.element('div').classes('im-field w-full'):
                        ui.label('DESİ DEĞERİ (BİRİM BAŞINA HAMMADDE)').classes('im-flabel')
                        inp_desi = ui.number(value=0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full st-desi')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

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
                        # Yazildi ama Enter basilmadi -> pending text'i kullan
                        if not kat_val and _kat_pending.get('text'):
                            kat_val = _kat_pending['text']
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

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

                # Enter akisi (sunucu): kategori secilince Birim listesi acilir
                _nav = {'birim': False}

                def _kat_enter():
                    _nav['birim'] = True
                    inp_birim.run_method('focus')
                    inp_birim.run_method('showPopup')
                inp_kat.on('keydown.enter', _kat_enter)  # prevent YOK: yeni kategori commit'i bozulmasin

                def _birim_hide():
                    if _nav['birim']:
                        _nav['birim'] = False
                        if inp_desi is not None:
                            ui.run_javascript(
                                "const el=[...document.querySelectorAll('.im-modal .st-desi input')].pop();"
                                "if(el){el.focus();el.select();}")
                        else:
                            ui.run_javascript(
                                "const b=[...document.querySelectorAll('.im-modal .im-btn-kaydet')].pop();"
                                "if(b)b.focus();")
                inp_birim.on('popup-hide', _birim_hide)
        dlg.open()
        # Acilinca odak Urun Adi'na
        ui.timer(0.2, lambda: inp_ad.run_method('focus'), once=True)
        # Klavye akisi (CLIENT-SIDE): ad -> kategori; desi -> Kaydet; ok tuslari Kaydet<->Iptal
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__stFlow) return;
            modal.__stFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const ad = modal.querySelector('.st-ad input');
            if(ad) ad.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault();
                    const k = modal.querySelector('.st-kat input'); if(k) k.focus(); }
            });
            const desi = modal.querySelector('.st-desi input');
            if(desi) desi.addEventListener('keydown', (e) => {
                if(e.key === 'Enter'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

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
        # disinda veya bos string olunca render sirasinda dialog acilmiyor
        # (ABS GRANÜL(K) bug: kategori='' ve options'da '' yok -> dialog patliyor).
        _kat_raw = (row.get('kategori') or '').strip()
        _kat_val = _kat_raw if _kat_raw else None  # bos -> None (Quasar None'i temiz handle eder)
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
            _kat_pending = {'text': ''}
            inp_kat.on('input-value', lambda e: _kat_pending.update({'text': str(e.args or '').strip()}))
            inp_birim = ui.select(
                options=_birim_options,
                value=_birim_val, label='Birim',
                with_input=True, new_value_mode='add-unique',
            ).classes('w-full').props('outlined dense')
            _birim_pending = {'text': ''}
            inp_birim.on('input-value', lambda e: _birim_pending.update({'text': str(e.args or '').strip()}))

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
                        if not kat_val and _kat_pending.get('text'):
                            kat_val = _kat_pending['text']
                        birim_val = (inp_birim.value or '').strip() if isinstance(inp_birim.value, str) else ''
                        if not birim_val and _birim_pending.get('text'):
                            birim_val = _birim_pending['text']
                        if not birim_val:
                            birim_val = 'KG'
                        update_urun(row['kod'], {
                            'ad': inp_ad.value.strip(),
                            'kategori': kat_val,
                            'birim': birim_val,
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
            with ui.element('div').style('position:relative'):
                ui.button('EKLE', icon='inventory_2', color='primary', on_click=open_add_dialog).props('dense no-caps')
                ui.label('F2').classes('fkey-hint')
        ui.add_css(IM_MODAL_CSS)
        f2_kisayolu(open_add_dialog)

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
                <div class="row no-wrap items-center" style="gap:2px;">
                    <span style="display:inline-flex;width:30px;justify-content:center;">
                        <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                            @click.stop="$parent.$emit('edit', props.row)">
                            <q-tooltip>Düzenle</q-tooltip>
                        </q-btn>
                    </span>
                    <span style="display:inline-flex;width:30px;justify-content:center;">
                        <q-btn v-if="(!props.row.alis || props.row.alis === 0) && (!props.row.satis || props.row.satis === 0) && (!props.row.uretim_girdi || props.row.uretim_girdi === 0) && (!props.row.uretim_cikti || props.row.uretim_cikti === 0)"
                            flat round dense icon="delete_outline" color="negative" size="sm"
                            @click.stop="$parent.$emit('remove', props.row)">
                            <q-tooltip>Sil (boş stok)</q-tooltip>
                        </q-btn>
                    </span>
                </div>
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





