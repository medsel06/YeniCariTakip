"""Firma master veri yönetimi."""
from nicegui import ui

from layout import create_layout, notify_ok, notify_err, confirm_dialog, PARA_SLOT, normalize_search, IM_MODAL_CSS
from services.cari_service import (
    get_firma_master_list, add_firma, update_firma, delete_firma, generate_firma_kod
)


@ui.page('/firma-master')
def firma_master_page():
    if not create_layout(active_path='/firma-master', page_title='Firma Master'):
        return
    ui.add_css(IM_MODAL_CSS)
    ui.add_css('''
        .fm-fhint { position:absolute; top:100%; left:50%; transform:translateX(-50%);
            font-size:8.5px; color:#94a3b8; font-weight:700; letter-spacing:.5px;
            line-height:1; margin-top:2px; pointer-events:none; }
    ''')
    all_rows = get_firma_master_list()

    def _filter_rows(query):
        q = normalize_search(query)
        if not q:
            return all_rows
        return [
            r for r in all_rows
            if q in normalize_search(r.get('kod', ''))
            or q in normalize_search(r.get('ad', ''))
            or q in normalize_search(r.get('vkn_tckn', ''))
            or q in normalize_search(r.get('email', ''))
        ]

    def _refresh():
        nonlocal all_rows
        all_rows = get_firma_master_list()
        table.rows = _filter_rows(search.value)
        table.update()
        lbl_toplam.set_text(f'Toplam Firma: {len(all_rows)}')

    def _open_detail(row):
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:560px'):
            ui.label(f"Firma Detayı - {row.get('ad', '')}").classes('text-h6')
            ui.separator().classes('q-my-sm')
            pairs = [
                ('Kod', row.get('kod', '-')),
                ('Firma', row.get('ad', '-')),
                ('VKN / TCKN', row.get('vkn_tckn', '-')),
                ('Telefon', row.get('tel', '-')),
                ('E-posta', row.get('email', '-')),
                ('Adres', row.get('adres', '-')),
                ('NACE', row.get('nace', '-')),
                ('İş Alanı', row.get('is_alani', '-')),
                ('Risk Limiti', f"{(row.get('risk_limiti') or 0):,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')),
            ]
            for label, value in pairs:
                with ui.row().classes('w-full items-center q-py-xs'):
                    ui.label(label).classes('text-grey-7').style('width:140px')
                    ui.label(str(value or '-')).classes('text-weight-medium')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    def _open_add():
        auto_kod = generate_firma_kod()
        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 580px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('add_business').classes('im-ic')
                ui.label('Yeni Firma').classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Kod (readonly) + Firma Adi
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 110px'):
                        ui.label('KOD').classes('im-flabel')
                        ui.input(value=auto_kod).props('outlined dense readonly').classes('w-full')
                    with ui.element('div').classes('im-field col'):
                        ui.label('FİRMA ADI').classes('im-flabel')
                        inp_ad = ui.input().props('outlined dense').classes('w-full fm-ad')
                # Satir 2: VKN + Vergi Dairesi
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('VKN / TCKN').classes('im-flabel')
                        inp_vkn = ui.input().props('outlined dense').classes('w-full fm-vkn')
                    with ui.element('div').classes('im-field col'):
                        ui.label('VERGİ DAİRESİ').classes('im-flabel')
                        inp_vergi = ui.input().props('outlined dense').classes('w-full fm-vergi')
                # Satir 3: Telefon + E-posta
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('TELEFON').classes('im-flabel')
                        inp_tel = ui.input().props('outlined dense').classes('w-full fm-tel')
                    with ui.element('div').classes('im-field col'):
                        ui.label('E-POSTA').classes('im-flabel')
                        inp_mail = ui.input().props('outlined dense').classes('w-full fm-mail')
                # Adres
                with ui.element('div').classes('im-field w-full'):
                    ui.label('ADRES').classes('im-flabel')
                    inp_adres = ui.input().props('outlined dense').classes('w-full fm-adres')
                # Satir 4: NACE + Is Alani + Risk Limiti
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 110px'):
                        ui.label('NACE').classes('im-flabel')
                        inp_nace = ui.input().props('outlined dense').classes('w-full fm-nace')
                    with ui.element('div').classes('im-field col'):
                        ui.label('İŞ ALANI').classes('im-flabel')
                        inp_is = ui.input().props('outlined dense').classes('w-full fm-is')
                    with ui.element('div').classes('im-field').style('flex:0 0 140px'):
                        ui.label('RİSK LİMİTİ').classes('im-flabel')
                        inp_risk = ui.number(value=0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full fm-risk')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def _save():
                    if not (inp_ad.value or '').strip():
                        notify_err('Firma adı zorunlu')
                        return
                    try:
                        is_alani = (inp_is.value or '').strip()
                        if inp_vergi.value:
                            is_alani = (is_alani + f" | VD: {inp_vergi.value.strip()}").strip()
                        add_firma({
                            'kod': auto_kod,
                            'ad': inp_ad.value.strip(),
                            'vkn_tckn': inp_vkn.value or '',
                            'tel': inp_tel.value or '',
                            'adres': inp_adres.value or '',
                            'email': inp_mail.value or '',
                            'nace': inp_nace.value or '',
                            'is_alani': is_alani,
                            'risk_limiti': float(inp_risk.value or 0),
                        })
                        notify_ok('Firma eklendi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                btn_kaydet = ui.button('Kaydet', on_click=_save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')
        dlg.open()
        # Acilinca odak Firma Adi'na
        ui.timer(0.2, lambda: inp_ad.run_method('focus'), once=True)
        # Enter zinciri (CLIENT-SIDE): ad -> vkn -> vergi -> tel -> mail -> adres
        # -> nace -> is alani -> risk -> Kaydet; ok tuslari Kaydet<->Iptal
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__fmFlow) return;
            modal.__fmFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const sira = ['.fm-ad', '.fm-vkn', '.fm-vergi', '.fm-tel', '.fm-mail',
                          '.fm-adres', '.fm-nace', '.fm-is', '.fm-risk'];
            sira.forEach((cls, i) => {
                const el = modal.querySelector(cls + ' input');
                if(!el) return;
                el.addEventListener('keydown', (e) => {
                    if(e.key !== 'Enter') return;
                    e.preventDefault();
                    const nxt = sira[i + 1];
                    if(nxt){ const n = modal.querySelector(nxt + ' input'); if(n){ n.focus(); if(n.select) n.select(); } }
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

    def _open_edit(row):
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:520px'):
            ui.label(f"Firma Düzenle - {row.get('kod', '')}").classes('text-h6')
            inp_ad = ui.input('Firma Adı', value=row.get('ad', '')).props('outlined dense').classes('w-full')
            inp_vkn = ui.input('VKN / TCKN', value=row.get('vkn_tckn', '')).props('outlined dense').classes('w-full')
            inp_tel = ui.input('Telefon', value=row.get('tel', '')).props('outlined dense').classes('w-full')
            inp_mail = ui.input('E-posta', value=row.get('email', '')).props('outlined dense').classes('w-full')
            inp_adres = ui.input('Adres', value=row.get('adres', '')).props('outlined dense').classes('w-full')
            inp_nace = ui.input('NACE', value=row.get('nace', '')).props('outlined dense').classes('w-full')
            inp_is = ui.input('İş Alanı', value=row.get('is_alani', '')).props('outlined dense').classes('w-full')
            inp_risk = ui.number('Risk Limiti', value=row.get('risk_limiti', 0) or 0, format='%.2f').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('İptal', on_click=dlg.close).props('flat')

                def _save():
                    if not (inp_ad.value or '').strip():
                        notify_err('Firma adı zorunlu')
                        return
                    try:
                        update_firma(row['kod'], {
                            'ad': inp_ad.value.strip(),
                            'vkn_tckn': inp_vkn.value or '',
                            'tel': inp_tel.value or '',
                            'adres': inp_adres.value or '',
                            'email': inp_mail.value or '',
                            'nace': inp_nace.value or '',
                            'is_alani': inp_is.value or '',
                            'risk_limiti': float(inp_risk.value or 0),
                        })
                        notify_ok('Firma güncellendi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=_save)
        dlg.open()

    def _delete(row):
        confirm_dialog(
            f"{row.get('ad', '')} kaydını silmek istediğinize emin misiniz?",
            lambda: (delete_firma(row['kod']), notify_ok('Firma silindi'), _refresh()),
        )

    with ui.column().classes('w-full q-pa-xs gap-1'):
        with ui.row().classes('w-full items-center gap-2 no-wrap q-px-xs'):
            search = ui.input(
                placeholder='Ara (kod, ad, vkn, e-posta)...',
                on_change=lambda e: (setattr(table, 'rows', _filter_rows(e.value)), table.update()),
            ).props('outlined dense clearable').classes('w-64')
            lbl_toplam = ui.label(f'Toplam Firma: {len(all_rows)}').classes('text-caption text-grey-7')
            ui.space()
            with ui.element('div').style('position:relative'):
                ui.button('YENİ', icon='add_business', color='primary', on_click=_open_add).props('dense no-caps')
                ui.label('F2').classes('fm-fhint')

        # F2 kisayolu: modal kapaliysa Yeni Firma acar; acik modalda Kaydet'e tiklar
        def _fm_fkey(e):
            if (e.args or {}).get('key') == 'F2':
                _open_add()
        ui.on('fm_fkey', _fm_fkey)
        ui.run_javascript('''
            if(!window.__fmFkeys){
                window.__fmFkeys = true;
                document.addEventListener('keydown', (e) => {
                    if(e.key !== 'F2') return;
                    const b = [...document.querySelectorAll('.q-dialog .im-btn-kaydet')].pop();
                    if(b){ e.preventDefault(); b.click(); return; }
                    if(document.querySelector('.q-dialog')) return;
                    e.preventDefault();
                    emitEvent('fm_fkey', {key: 'F2'});
                }, true);
            }
        ''')

        columns = [
            {'name': 'ad', 'label': 'Firma', 'field': 'ad', 'align': 'left', 'sortable': True},
            {'name': 'vkn_tckn', 'label': 'VKN/TCKN', 'field': 'vkn_tckn', 'align': 'left', 'sortable': True},
            {'name': 'tel', 'label': 'Telefon', 'field': 'tel', 'align': 'left', 'sortable': True},
            {'name': 'email', 'label': 'E-posta', 'field': 'email', 'align': 'left', 'sortable': True},
            {'name': 'risk_limiti', 'label': 'Risk Limiti', 'field': 'risk_limiti', 'align': 'right', 'sortable': True},
            {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center'},
        ]
        table = ui.table(
            columns=columns,
            rows=all_rows,
            row_key='kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'ad', 'descending': False},
        ).classes('w-full').style('--table-extra-rows: 3;')
        table.props('flat bordered dense')
        table.add_slot('body-cell-risk_limiti', PARA_SLOT)
        table.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="visibility" color="grey-8" size="sm"
                    @click.stop="$parent.$emit('detail', props.row)" />
                <q-btn flat round dense icon="edit" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit', props.row)" />
                <q-btn flat round dense icon="delete" color="negative" size="sm"
                    @click.stop="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')
        table.on('detail', lambda e: _open_detail(e.args))
        table.on('edit', lambda e: _open_edit(e.args))
        table.on('delete', lambda e: _delete(e.args))
        table.on('rowClick', lambda e: _open_detail(e.args[1]))
