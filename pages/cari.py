"""ALSE Plastik Hammadde - Cari Hesaplar Sayfasi"""
from datetime import datetime
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog, PARA_SLOT, normalize_search, donem_popover_btn, segment_group, IM_MODAL_CSS, f2_kisayolu
from services.cari_service import (
    get_cari_bakiye_list, get_firma_list, add_firma, update_firma, generate_firma_kod
)


@ui.page('/cari')
def cari_page():
    if not create_layout(active_path='/cari', page_title='Cari Hesaplar'):
        return

    # --- State ---
    now = datetime.now()
    search_value = {'text': ''}
    tur_filter = {'value': None}  # 'ALIS' | 'SATIS' | None
    # Default: yil=mevcut yil, ay=None (Tumu) — UI ile sync (donem_secici default_ay=0=Tumu)
    state = {'yil': now.year, 'ay': None}

    # --- Data Load ---
    def load_data():
        # Backend hareketsiz/sifir bakiyeli firmalari zaten filtreliyor.
        # UI'da geri ekleme bloğu kaldırıldı (Paket 1) — kapanmış firmalar artık görünmez.
        return get_cari_bakiye_list(yil=state['yil'], ay=state['ay'])

    all_data = load_data()

    def get_filtered():
        rows = all_data
        if tur_filter['value'] == 'ALIS':
            rows = [r for r in rows if (r.get('alis') or 0) > 0]
        elif tur_filter['value'] == 'SATIS':
            rows = [r for r in rows if (r.get('satis') or 0) > 0]
        q = normalize_search(search_value['text'])
        if q:
            rows = [r for r in rows if q in normalize_search(r['ad']) or q in normalize_search(r['kod'])]
        return rows

    # --- UI ---
    with ui.column().classes('w-full q-pa-sm'):
        # Donem degisince
        def _on_donem(yil, ay):
            nonlocal all_data
            state['yil'] = yil
            state['ay'] = ay
            all_data = load_data()
            table.rows = get_filtered()
            table.update()
            _render_ozet()

        def on_tur_change(new_tur):
            tur_filter['value'] = new_tur
            table.rows = get_filtered()
            table.update()
            _render_ozet()

        # Arama + Tur segment + Donem popover + Buton tek satir
        with ui.row().classes('w-full items-center gap-2 q-mb-xs'):
            search_input = ui.input(
                label='Ara (Firma adı veya kodu)',
            ).classes('w-64').props('outlined dense clearable')

            ui.element('div').style('width:8px')
            segment_group(
                buttons=[
                    ('ALIS', 'Alış', '#1d4ed8'),
                    ('SATIS', 'Satış', '#15803d'),
                ],
                on_change=on_tur_change,
                active=None,
            )

            donem_popover_btn(_on_donem, default_mode='YIL')
            ui.space()
            # Tek parca ozet panel (butonlarin saginda, ayni satirda)
            ozet_box = ui.row().classes('items-center no-wrap')
            with ui.element('div').style('position:relative'):
                ui.button('YENİ', icon='add_business', on_click=lambda: open_new_firma_dialog()) \
                    .props('color=primary dense no-caps')
                ui.label('F2').classes('fkey-hint')
        ui.add_css(IM_MODAL_CSS)
        f2_kisayolu(lambda: open_new_firma_dialog())

        def _render_ozet():
            ozet_box.clear()
            rows = get_filtered()
            t_alacak = sum(float(r.get('bakiye') or 0) for r in rows if float(r.get('bakiye') or 0) > 0)
            t_borc = sum(-float(r.get('bakiye') or 0) for r in rows if float(r.get('bakiye') or 0) < 0)
            net = t_alacak - t_borc
            net_fg = '#15803d' if net >= 0 else '#b91c1c'
            segs = [
                ('Alacak', t_alacak, '#15803d'),
                ('Borç', t_borc, '#b91c1c'),
                ('Net', net, net_fg),
            ]
            with ozet_box:
                with ui.row().classes('items-center no-wrap').style(
                    'border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;background:#fff;height:34px'
                ):
                    for i, (lbl, val, fg) in enumerate(segs):
                        sep = 'border-right:1px solid #eef2f6;' if i < len(segs) else ''
                        with ui.row().classes('items-center no-wrap').style(
                            f'padding:0 12px;gap:6px;height:100%;{sep}'
                        ):
                            ui.label(lbl).style('font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.4px')
                            ui.label(f"{fmt_para(val)} ₺").style(f'font-size:13px;font-weight:800;color:{fg}')

        # Tablo
        columns = [
            {'name': 'ad', 'label': 'Firma Ad\u0131', 'field': 'ad', 'align': 'left', 'sortable': True},
            {'name': 'devir', 'label': 'Devir', 'field': 'devir', 'align': 'right', 'sortable': True},
            {'name': 'alis', 'label': 'Al\u0131\u015f', 'field': 'alis', 'align': 'right', 'sortable': True},
            {'name': 'satis', 'label': 'Sat\u0131\u015f', 'field': 'satis', 'align': 'right', 'sortable': True},
            {'name': 'odeme', 'label': '\u00d6deme', 'field': 'odeme', 'align': 'right', 'sortable': True},
            {'name': 'tahsilat', 'label': 'Tahsilat', 'field': 'tahsilat', 'align': 'right', 'sortable': True},
            {'name': 'bakiye', 'label': 'Bakiye', 'field': 'bakiye', 'align': 'right', 'sortable': True},
            {'name': 'actions', 'label': '', 'field': 'actions', 'align': 'center'},
        ]

        table = ui.table(
            columns=columns,
            rows=get_filtered(),
            row_key='kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'ad', 'descending': False},
        ).classes('w-full').style('--table-extra-rows: 3;')
        table.props('flat bordered dense')

        # Para slotlari (NaN fix)
        table.add_slot('body-cell-devir', PARA_SLOT)
        table.add_slot('body-cell-alis', PARA_SLOT)
        table.add_slot('body-cell-satis', PARA_SLOT)
        table.add_slot('body-cell-odeme', PARA_SLOT)
        table.add_slot('body-cell-tahsilat', PARA_SLOT)

        # Bakiye renklendirme
        table.add_slot('body-cell-bakiye', '''
            <q-td :props="props">
                <span :class="props.value > 0 ? 'text-positive text-weight-bold' : props.value < 0 ? 'text-negative text-weight-bold' : ''">
                    {{ props.value != null && props.value !== 0 ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                </span>
            </q-td>
        ''')

        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round dense icon="drive_file_rename_outline" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)">
                    <q-tooltip>D\u00fczenle</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        def refresh_table():
            nonlocal all_data
            all_data = load_data()
            table.rows = get_filtered()
            table.update()
            _render_ozet()

        # Arama handler
        def on_search(e):
            search_value['text'] = e.args if isinstance(e.args, str) else (e.args or '')
            table.rows = get_filtered()
            table.update()
            _render_ozet()

        search_input.on('update:model-value', lambda e: on_search(e))

        # Ilk ozet render
        _render_ozet()

        # Satir tiklama - cari detaya git
        table.on('rowClick', lambda e: ui.navigate.to(f'/cari/{e.args[1]["kod"]}'))


        # Edit handler
        def handle_edit(e):
            row = e.args
            open_edit_firma_dialog(row)

        table.on('edit', handle_edit)

    # --- Yeni Firma Dialog (kompakt im-modal + Enter zinciri) ---
    def open_new_firma_dialog():
        auto_kod = generate_firma_kod()

        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 520px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('add_business').classes('im-ic')
                ui.label('Yeni Firma Ekle').classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Kod (readonly) + Firma Adi
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 110px'):
                        ui.label('KOD').classes('im-flabel')
                        ui.input(value=auto_kod).props('outlined dense readonly').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('F\u0130RMA ADI').classes('im-flabel')
                        ad_input = ui.input().props('outlined dense').classes('w-full cr-ad')
                # Telefon
                with ui.element('div').classes('im-field w-full'):
                    ui.label('TELEFON').classes('im-flabel')
                    tel_input = ui.input().props('outlined dense').classes('w-full cr-tel')
                # Adres
                with ui.element('div').classes('im-field w-full'):
                    ui.label('ADRES').classes('im-flabel')
                    adres_input = ui.input().props('outlined dense').classes('w-full cr-adres')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('\u23ce Enter ilerler \u00b7 F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('\u0130ptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def save():
                    kod = auto_kod
                    ad = (ad_input.value or '').strip()
                    if not ad:
                        notify_err('Ad alani zorunludur')
                        return
                    try:
                        add_firma({
                            'kod': kod,
                            'ad': ad,
                            'tel': (tel_input.value or '').strip(),
                            'adres': (adres_input.value or '').strip(),
                        })
                        notify_ok(f'Firma eklendi: {ad}')
                        dlg.close()
                        refresh_table()
                    except Exception as ex:
                        notify_err(f'Hata: {ex}')

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')

        dlg.open()
        # Acilinca odak Firma Adi'na
        ui.timer(0.2, lambda: ad_input.run_method('focus'), once=True)
        # Enter zinciri (CLIENT-SIDE): ad -> tel -> adres -> Kaydet; ok tuslari Kaydet<->Iptal
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__crFlow) return;
            modal.__crFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const sira = ['.cr-ad', '.cr-tel', '.cr-adres'];
            sira.forEach((cls, i) => {
                const el = modal.querySelector(cls + ' input');
                if(!el) return;
                el.addEventListener('keydown', (e) => {
                    if(e.key !== 'Enter') return;
                    e.preventDefault();
                    const nxt = sira[i + 1];
                    if(nxt){ const n = modal.querySelector(nxt + ' input'); if(n) n.focus(); }
                    else if(kaydet){ kaydet.focus(); }
                });
            });
            if(kaydet) kaydet.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowLeft'){ e.preventDefault(); if(iptal) iptal.focus(); }
            });
            if(iptal) iptal.addEventListener('keydown', (e) => {
                if(e.key === 'ArrowRight'){ e.preventDefault(); if(kaydet) kaydet.focus(); }
            });
        '''), once=True)

    # --- Edit Firma Dialog ---
    def open_edit_firma_dialog(row):
        ad_input = None
        tel_input = None
        adres_input = None

        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 400px'):
            ui.label('Firma D\u00fczenle').classes('text-h6 q-mb-md')
            ui.label(f'Kod: {row["kod"]}').classes('text-subtitle2 text-grey-7 q-mb-sm')
            ad_input = ui.input(label='Firma Ad\u0131', value=row.get('ad', '')).classes('w-full').props('outlined dense')
            tel_input = ui.input(label='Telefon', value=row.get('tel', '')).classes('w-full').props('outlined dense')
            adres_input = ui.textarea(label='Adres', value=row.get('adres', '')).classes('w-full').props('outlined dense')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('\u0130ptal', on_click=dlg.close).props('flat')

                def save_edit():
                    ad = ad_input.value.strip()
                    if not ad:
                        notify_err('Ad alan\u0131 zorunludur')
                        return
                    try:
                        update_firma(row['kod'], {
                            'ad': ad,
                            'tel': tel_input.value.strip(),
                            'adres': adres_input.value.strip(),
                        })
                        notify_ok(f'Firma g\u00fcncellendi: {ad}')
                        dlg.close()
                        refresh_table()
                    except Exception as ex:
                        notify_err(f'Hata: {ex}')

                ui.button('Kaydet', color='primary', on_click=save_edit).classes('im-btn-kaydet')

        dlg.open()
