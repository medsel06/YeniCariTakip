"""Söküm Verimi — parti bazlı ayrıştırma kâr/verim takibi (hurda)."""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, IM_MODAL_CSS, f2_kisayolu
from services.sokum_service import (
    get_sokum_partileri, add_sokum_parti, update_sokum_parti, delete_sokum_parti, get_sokum_ozet,
)


def _vd(iso):
    return '-' if not iso else '.'.join(reversed(str(iso)[:10].split('-')))


def _kg(v):
    return f"{float(v or 0):,.0f}".replace(',', '.') + ' kg'


@ui.page('/sokum')
def sokum_page():
    if not create_layout(active_path='/sokum', page_title='Söküm Verimi'):
        return

    container = ui.column().classes('w-full q-pa-sm gap-3')
    ui.add_css(IM_MODAL_CSS)
    f2_kisayolu(lambda: _dialog())

    def _do_delete(pid):
        delete_sokum_parti(pid)
        notify_ok('Parti silindi')
        _reload()

    def _dialog(parti=None):
        is_edit = parti is not None
        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width:92vw;max-width:660px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('recycling')
                ui.label('Söküm Partisi' + (' — Düzenle' if is_edit else '')).classes('dialog-title')
            with ui.column().classes('w-full q-mt-sm').style('gap:10px'):
                with ui.row().classes('w-full gap-md'):
                    inp_tarih = ui.input('Tarih', value=(parti.get('tarih') if is_edit else date.today().isoformat())).props(
                        'outlined dense type=date').classes('col')
                    inp_acik = ui.input('Parti / Giriş açıklaması (örn. Karışık motosiklet hurdası)',
                                        value=(parti.get('aciklama', '') if is_edit else '')).props('outlined dense').classes('col-7')
                with ui.row().classes('w-full gap-md'):
                    inp_gkg = ui.number('Giriş miktarı (kg)', value=(parti.get('giris_miktar', 0) if is_edit else 0),
                                        min=0).props('outlined dense').classes('col')
                    inp_gmal = ui.number('Giriş maliyeti (TL)', value=(parti.get('giris_maliyet', 0) if is_edit else 0),
                                         min=0).props('outlined dense').classes('col')

                ui.label('Çıkan Malzemeler (ayrıştırma sonrası satılan)').classes(
                    'text-caption text-weight-bold text-grey-8')
                cikti_box = ui.column().classes('w-full').style('gap:6px')
                cikti_rows = []

                def _kar_guncelle():
                    cikti_t = sum(float(r['tutar'].value or 0) for r in cikti_rows)
                    cikti_kg = sum(float(r['miktar'].value or 0) for r in cikti_rows)
                    kar = cikti_t - float(inp_gmal.value or 0)
                    fire = float(inp_gkg.value or 0) - cikti_kg
                    lbl_kar.set_text(
                        f"Çıkış: {fmt_para(cikti_t)} TL / {_kg(cikti_kg)}   •   "
                        f"Kâr: {fmt_para(kar)} TL   •   Fire: {_kg(fire)}")
                    lbl_kar.style(f"color:{'#16a34a' if kar >= 0 else '#dc2626'};font-size:13px;font-weight:700")

                def _malzeme_soru():
                    """Son cikti satirinda Enter: yeni malzeme satiri? Enter=Hayir(notlara), sag ok=Evet."""
                    with ui.dialog() as sdlg, ui.card().classes('q-pa-md im-confirm-card').style(
                            'min-width:360px;border-radius:12px'):
                        ui.label('Yeni malzeme satırı eklensin mi?').classes('text-subtitle2 text-weight-bold').style('color:#0f766e')
                        ui.label('Enter = Hayır (notlara geçer)   ·   → ile Evet').classes('text-caption text-grey-6 q-mb-sm')

                        def _evet():
                            sdlg.close()
                            _add_cikti()
                            cikti_rows[-1]['malzeme'].run_method('focus')

                        def _hayir():
                            sdlg.close()
                            inp_notlar.run_method('focus')

                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Hayır', on_click=_hayir).props('flat color=grey')
                            ui.button('Evet', on_click=_evet).props('unelevated color=positive')
                    sdlg.open()
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

                def _add_cikti(m='', kg=0, t=0):
                    with cikti_box:
                        with ui.row().classes('w-full items-center no-wrap').style('gap:6px') as rw:
                            mi = ui.input('Malzeme', value=m).props('outlined dense').classes('col')
                            mk = ui.number('kg', value=kg, min=0).props('outlined dense').classes('col-3')
                            tu = ui.number('Satış TL', value=t, min=0).props('outlined dense').classes('col-3')
                            row_d = {'malzeme': mi, 'miktar': mk, 'tutar': tu}
                            tu.on('blur', lambda: _kar_guncelle())
                            mk.on('blur', lambda: _kar_guncelle())

                            # Enter zinciri (satir ici): malzeme -> kg -> TL -> sonraki satir / soru
                            mi.on('keydown.enter.prevent', lambda mk=mk: (mk.run_method('focus'), mk.run_method('select')))
                            mk.on('keydown.enter.prevent', lambda tu=tu: (tu.run_method('focus'), tu.run_method('select')))

                            def _tu_enter(row_d=row_d):
                                _kar_guncelle()
                                try:
                                    idx = cikti_rows.index(row_d)
                                except ValueError:
                                    return
                                if idx + 1 < len(cikti_rows):
                                    nxt = cikti_rows[idx + 1]['malzeme']
                                    nxt.run_method('focus')
                                else:
                                    _malzeme_soru()
                            tu.on('keydown.enter.prevent', _tu_enter)

                            def _sil():
                                if row_d in cikti_rows:
                                    cikti_rows.remove(row_d)
                                cikti_box.remove(rw)
                                _kar_guncelle()
                            ui.button(icon='close', on_click=_sil).props('flat dense round color=grey-6')
                    cikti_rows.append(row_d)

                ui.button('Malzeme Ekle', icon='add', on_click=lambda: _add_cikti()).props(
                    'flat dense no-caps color=deep-purple')
                lbl_kar = ui.label('')
                inp_gmal.on('blur', lambda: _kar_guncelle())
                inp_gkg.on('blur', lambda: _kar_guncelle())
                inp_notlar = ui.textarea('Notlar', value=(parti.get('notlar', '') if is_edit else '')).props(
                    'outlined dense autogrow').classes('w-full')

                # Enter zinciri (ust alanlar): tarih -> aciklama -> giris kg -> maliyet -> ilk malzeme
                inp_tarih.on('keydown.enter.prevent', lambda: inp_acik.run_method('focus'))
                inp_acik.on('keydown.enter.prevent', lambda: (inp_gkg.run_method('focus'), inp_gkg.run_method('select')))
                inp_gkg.on('keydown.enter.prevent', lambda: (inp_gmal.run_method('focus'), inp_gmal.run_method('select')))

                def _gmal_enter():
                    _kar_guncelle()
                    if cikti_rows:
                        cikti_rows[0]['malzeme'].run_method('focus')
                inp_gmal.on('keydown.enter.prevent', _gmal_enter)

                if is_edit:
                    for c in parti.get('ciktilar_list', []):
                        _add_cikti(c.get('malzeme', ''), c.get('miktar', 0), c.get('tutar', 0))
                if not cikti_rows:
                    _add_cikti()
                    _add_cikti()
                _kar_guncelle()

                with ui.row().classes('w-full justify-end items-center q-mt-sm').style('gap:8px'):
                    ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                    if is_edit:
                        ui.button('Sil', icon='delete', color='negative',
                                  on_click=lambda: (dlg.close(), _do_delete(parti['id']))).props('flat')
                    ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                    def _save():
                        ciktilar = [
                            {'malzeme': (r['malzeme'].value or '').strip(),
                             'miktar': float(r['miktar'].value or 0),
                             'tutar': float(r['tutar'].value or 0)}
                            for r in cikti_rows
                            if (r['malzeme'].value or '').strip() or float(r['tutar'].value or 0) > 0
                        ]
                        data = {
                            'tarih': inp_tarih.value or '', 'aciklama': inp_acik.value or '',
                            'giris_miktar': float(inp_gkg.value or 0), 'giris_maliyet': float(inp_gmal.value or 0),
                            'ciktilar': ciktilar, 'notlar': inp_notlar.value or '',
                        }
                        if is_edit:
                            update_sokum_parti(parti['id'], data)
                        else:
                            add_sokum_parti(data)
                        dlg.close()
                        notify_ok('Parti kaydedildi')
                        _reload()
                    ui.button('Kaydet', color=None, on_click=_save).props('unelevated').classes('im-btn-kaydet').style(
                        'background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff')
        dlg.open()
        # Acilinca odak Tarih'e
        ui.timer(0.2, lambda: inp_tarih.run_method('focus'), once=True)

    def _reload():
        container.clear()
        rows = get_sokum_partileri()
        ozet = get_sokum_ozet()
        with container:
            with ui.row().classes('w-full gap-3 no-wrap'):
                def _kart(baslik, deger, renk, ikon):
                    with ui.card().classes('col q-pa-md').style(f'border-left:5px solid {renk}'):
                        with ui.row().classes('items-center gap-2 no-wrap'):
                            ui.icon(ikon).style(f'color:{renk};font-size:24px')
                            with ui.column().classes('gap-0'):
                                ui.label(baslik).classes('text-caption text-grey-7')
                                ui.label(deger).style(f'font-size:17px;font-weight:800;color:{renk}')
                _kart('Parti Sayısı', str(ozet['parti']), '#6d28d9', 'recycling')
                _kart('Giriş Maliyeti', f"{fmt_para(ozet['giris_maliyet'])} TL", '#dc2626', 'south_west')
                _kart('Çıkış Değeri', f"{fmt_para(ozet['cikti_toplam'])} TL", '#16a34a', 'north_east')
                _kart('Toplam Kâr', f"{fmt_para(ozet['kar'])} TL",
                      '#2563eb' if ozet['kar'] >= 0 else '#dc2626', 'savings')

            with ui.row().classes('w-full items-center'):
                ui.label('Söküm Partileri').classes('text-subtitle2 text-weight-bold')
                ui.space()
                with ui.element('div').style('position:relative'):
                    ui.button('Yeni Parti', icon='add', color=None, on_click=lambda: _dialog()).props('unelevated').style(
                        'background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff')
                    ui.label('F2').classes('fkey-hint')

            cols = [
                {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'left'},
                {'name': 'aciklama', 'label': 'Parti (Giriş)', 'field': 'aciklama', 'align': 'left'},
                {'name': 'giris_miktar', 'label': 'Giriş', 'field': 'giris_miktar', 'align': 'right'},
                {'name': 'giris_maliyet', 'label': 'Maliyet', 'field': 'giris_maliyet', 'align': 'right'},
                {'name': 'cikti_miktar', 'label': 'Çıkış', 'field': 'cikti_miktar', 'align': 'right'},
                {'name': 'cikti_toplam', 'label': 'Çıkış Değeri', 'field': 'cikti_toplam', 'align': 'right'},
                {'name': 'kar', 'label': 'Kâr', 'field': 'kar', 'align': 'right'},
                {'name': 'verim', 'label': 'Verim', 'field': 'verim', 'align': 'right'},
            ]
            disp = [{
                'id': r['id'], 'tarih': _vd(r.get('tarih')),
                'aciklama': r.get('aciklama', '') or '-',
                'giris_miktar': _kg(r.get('giris_miktar')),
                'giris_maliyet': fmt_para(r.get('giris_maliyet', 0)),
                'cikti_miktar': _kg(r.get('cikti_miktar')),
                'cikti_toplam': fmt_para(r.get('cikti_toplam', 0)),
                'kar': fmt_para(r.get('kar', 0)), '_kar': r.get('kar', 0),
                'verim': f"%{r.get('verim', 0):.0f}",
            } for r in rows]

            tbl = ui.table(columns=cols, rows=disp, row_key='id',
                           pagination={'rowsPerPage': 0}).classes('w-full').props('flat bordered dense hide-bottom')
            tbl.add_slot('body-cell-kar', r'''
                <q-td :props="props" class="text-right">
                    <span :class="props.row._kar >= 0 ? 'text-positive text-weight-bold' : 'text-negative text-weight-bold'">
                        {{ props.value }} TL</span>
                </q-td>''')
            tbl.add_slot('no-data', r'''
                <div class="full-width row flex-center q-pa-lg text-grey-6" style="gap:8px;">
                    <q-icon name="recycling" size="20px" />
                    <span style="font-size:12.5px;">Henüz söküm partisi yok. "Yeni Parti" ile ekleyin.</span>
                </div>''')
            tbl.on('row-click', lambda e: _dialog(next((p for p in rows if p['id'] == e.args[1]['id']), None)))
            ui.label('Satıra tıkla → düzenle/sil').classes('text-caption text-grey-5')

    _reload()
