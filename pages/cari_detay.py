"""ALSE Plastik Hammadde - Cari Detay Sayfası"""
from datetime import date, datetime
from nicegui import ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, normalize_search, donem_secici, _get_min_year
from services.cari_service import (
    get_firma, get_cari_ekstre, get_firma_hareketler, get_firma_kasa, get_firma_cekler,
)
from services.kasa_service import add_kasa
from services.pdf_service import (
    generate_cari_ekstre_pdf,
    generate_kasa_raporu_pdf,
    generate_cek_raporu_pdf,
    generate_table_pdf,
    generate_hizli_mutabakat_pdf,
    save_pdf_preview,
)
@ui.page('/cari/{firma_kod}')
def cari_detay_page(firma_kod: str):
    ui.add_css('''
    .cari-detay-table .q-table tbody td {
      padding-top: 7px !important;
      padding-bottom: 7px !important;
    }
    .cari-top-card {
      padding: 2px 4px !important;
    }
    .cari-topbar {
      min-height: 34px !important;
      padding-top: 2px !important;
      padding-bottom: 2px !important;
    }
    .cari-top-tabs .q-tab {
      min-height: 28px !important;
      padding: 0 8px !important;
    }
    .cari-detay-table .q-table__middle {
      max-height: calc(100vh - 360px) !important;
    }
    .cari-ekstre-table .q-table__middle {
      max-height: calc(100vh - 280px) !important;
    }
    .cari-hareketler-table .q-table__middle {
      max-height: calc(100vh - 280px) !important;
    }
    .cari-kasa-table .q-table__middle {
      max-height: calc(100vh - 280px) !important;
    }
    .cari-cekler-table .q-table__middle {
      max-height: calc(100vh - 280px) !important;
    }
    @media (max-width: 1200px) {
      .cari-detay-table .q-table__middle {
        max-height: calc(100vh - 330px) !important;
      }
      .cari-ekstre-table .q-table__middle {
        max-height: calc(100vh - 255px) !important;
      }
      .cari-hareketler-table .q-table__middle {
        max-height: calc(100vh - 255px) !important;
      }
      .cari-kasa-table .q-table__middle {
        max-height: calc(100vh - 255px) !important;
      }
      .cari-cekler-table .q-table__middle {
        max-height: calc(100vh - 255px) !important;
      }
    }
    @media (max-width: 900px) {
      .cari-detay-table .q-table__middle {
        max-height: calc(100vh - 305px) !important;
      }
      .cari-ekstre-table .q-table__middle {
        max-height: calc(100vh - 240px) !important;
      }
      .cari-hareketler-table .q-table__middle {
        max-height: calc(100vh - 240px) !important;
      }
      .cari-kasa-table .q-table__middle {
        max-height: calc(100vh - 240px) !important;
      }
      .cari-cekler-table .q-table__middle {
        max-height: calc(100vh - 240px) !important;
      }
    }
    ''')

    def _open_pdf(pdf_bytes, filename: str):
        preview_url = save_pdf_preview(pdf_bytes, filename)
        ui.run_javascript(f"window.open('{preview_url}', '_blank')")
    firma = get_firma(firma_kod)
    if not firma:
        if not create_layout(active_path='/cari', page_title='Cari Detay'):
            return
        with ui.column().classes('w-full q-pa-sm'):
            ui.label('Firma bulunamadı').classes('text-h6 text-negative')
            ui.button('Geri Dön', icon='arrow_back', on_click=lambda: ui.navigate.to('/cari')).props('flat')
        return

    if not create_layout(active_path='/cari', page_title='Cari Detay'):
        return

    def _with_ids(rows):
        out = []
        for i, r in enumerate(rows):
            x = dict(r)
            x['_rid'] = f"r{i}"
            out.append(x)
        return out

    def _desc(rows, key):
        return sorted(rows, key=lambda x: (x.get(key) or '', x.get('id') or 0), reverse=True)

    def _filter(rows, q, fields):
        q = normalize_search(q)
        if not q:
            return rows
        return [
            r for r in rows
            if any(q in normalize_search(r.get(f, '')) for f in fields)
        ]

    _now = datetime.now()
    donem_state = {'yil': None, 'ay': None}

    def _load_ekstre():
        src = get_cari_ekstre(firma_kod, yil=donem_state['yil'], ay=donem_state['ay'])
        src = list(reversed(src))
        for row in src:
            ac = (
                str(row.get('aciklama', '')).lower()
                .replace('ı', 'i')
                .replace('ş', 's')
                .replace('ö', 'o')
                .replace('ü', 'u')
                .replace('ç', 'c')
                .replace('ğ', 'g')
            )
            if ac.startswith('alis'):
                row['tip'] = 'ALIS'
            elif ac.startswith('satis'):
                row['tip'] = 'SATIS'
            elif ac.startswith('tahsilat'):
                row['tip'] = 'TAHSILAT'
            elif ac.startswith('odeme'):
                row['tip'] = 'ODEME'
            elif ac.startswith('gider'):
                row['tip'] = 'GIDER'
            elif ac.startswith('gelir'):
                row['tip'] = 'GELIR'
            elif 'devir' in ac:
                row['tip'] = 'DEVIR'
            else:
                row['tip'] = ''
        return src

    ekstre_src = _load_ekstre()
    ekstre_rows = _with_ids(ekstre_src)

    hareket_rows = _with_ids(_desc(get_firma_hareketler(firma_kod), 'tarih'))
    kasa_rows = _with_ids(_desc(get_firma_kasa(firma_kod), 'tarih'))
    cek_rows = _with_ids(_desc(get_firma_cekler(firma_kod), 'vade_tarih'))

    son_bakiye = (ekstre_src[0]['bakiye'] if ekstre_src else 0)

    with ui.column().classes('w-full q-pa-xs gap-1'):
        with ui.card().classes('w-full q-pa-none cari-top-card'):
            with ui.row().classes('w-full items-center gap-1 q-px-xs q-py-xs cari-topbar').style('flex-wrap: nowrap; overflow: hidden;'):
                with ui.row().classes('items-center gap-2 no-wrap'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/cari')).props('flat round dense')
                    with ui.column().classes('gap-0'):
                        ui.label(firma['ad']).style('font-size:15px;font-weight:700;line-height:1.2;color:#1e293b;')
                        bakiye_color = '#16a34a' if son_bakiye > 0 else '#dc2626' if son_bakiye < 0 else '#64748b'
                        bakiye_desc = 'Alacak' if son_bakiye > 0 else 'Borç' if son_bakiye < 0 else ''
                        ui.label(f'{fmt_para(son_bakiye)} TL · {bakiye_desc}').style(f'font-size:12px;font-weight:600;color:{bakiye_color};line-height:1.2;')

                with ui.row().classes('items-center justify-center').style('min-width:0; flex:1;'):
                    with ui.tabs().classes('q-px-xs q-py-1 rounded-borders bg-blue-1 text-primary cari-top-tabs').style('max-width: 360px;').props('dense no-caps inline-label') as tabs:
                        ekstre_tab = ui.tab('Ekstre').classes('text-weight-medium')
                        hareketler_tab = ui.tab('Hareketler').classes('text-weight-medium')
                        kasa_tab = ui.tab('Kasa').classes('text-weight-medium')
                        cekler_tab = ui.tab('Çekler').classes('text-weight-medium')

                def _pdf_ekstre_top():
                    # Donem secimine gore meta bilgili ekstre cek (donem_label + devir + satirlar)
                    ekstre_meta = get_cari_ekstre(
                        firma_kod, yil=donem_state['yil'], ay=donem_state['ay'], with_meta=True
                    )
                    _open_pdf(
                        generate_cari_ekstre_pdf(firma['ad'], ekstre_meta),
                        f"cari_ekstre_{firma_kod}.pdf"
                    )

                def _open_odeme_dialog(is_tahsilat=False):
                    """is_tahsilat=True → Tahsilat (firma bize oder), False → Odeme (biz firmaya oderiz)"""
                    baslik = 'Tahsilat Yap' if is_tahsilat else 'Ödeme Yap'
                    ikon = 'trending_up' if is_tahsilat else 'trending_down'
                    renk = 'positive' if is_tahsilat else 'negative'
                    # Varsayilan tutar: kalan borc/alacak
                    default_tutar = 0.0
                    if is_tahsilat and son_bakiye > 0:
                        default_tutar = son_bakiye
                    elif (not is_tahsilat) and son_bakiye < 0:
                        default_tutar = -son_bakiye

                    with ui.dialog() as odlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 460px'):
                        with ui.element('div').classes('alse-dialog-header'):
                            ui.icon(ikon)
                            ui.label(baslik).classes('dialog-title')
                            ui.space()
                            with ui.element('q-chip').props(f'dense color="{renk}" text-color="white"'):
                                ui.label(firma['ad']).classes('text-weight-medium')

                        with ui.column().classes('w-full q-mt-sm gap-sm'):
                            # Mevcut bakiye bilgisi
                            bak_info = ''
                            if son_bakiye > 0:
                                bak_info = f'Firma alacağı (tahsil edilecek): {fmt_para(son_bakiye)} TL'
                                bak_col = 'text-positive'
                            elif son_bakiye < 0:
                                bak_info = f'Firmaya borç (ödenecek): {fmt_para(-son_bakiye)} TL'
                                bak_col = 'text-negative'
                            else:
                                bak_info = 'Bakiye: 0 TL'
                                bak_col = 'text-grey-7'
                            ui.label(bak_info).classes(f'text-caption text-weight-medium {bak_col}')

                            inp_tarih_o = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                            with inp_tarih_o.add_slot('append'):
                                icon_to = ui.icon('event').classes('cursor-pointer')
                                with ui.menu() as menu_to:
                                    ui.date(on_change=lambda e: (inp_tarih_o.set_value(e.value), menu_to.close()))
                                icon_to.on('click', menu_to.open)

                            inp_tutar_o = ui.number('Tutar', value=default_tutar, format='%.2f').props('outlined dense').classes('w-full')

                            # Kasa / Banka secimi
                            inp_yontem = ui.radio(
                                options={'NAKIT': 'Kasa (Nakit)', 'HAVALE': 'Banka (Havale/EFT)', 'CEK': 'Çek', 'SENET': 'Senet'},
                                value='NAKIT'
                            ).props('inline')

                            banka_row_o = ui.row().classes('w-full')
                            banka_row_o.set_visibility(False)
                            with banka_row_o:
                                inp_banka_o = ui.input('Banka (isteğe bağlı)').props('outlined dense').classes('col')

                            def _on_yontem(_e):
                                banka_row_o.set_visibility(inp_yontem.value == 'HAVALE')
                            inp_yontem.on_value_change(_on_yontem)

                            inp_aciklama_o = ui.input('Açıklama').props('outlined dense').classes('w-full')

                        with ui.row().classes('w-full justify-end q-mt-md'):
                            ui.button('İptal', on_click=odlg.close).props('flat color=grey')

                            def _save_odeme():
                                tutar = float(inp_tutar_o.value or 0)
                                if tutar <= 0:
                                    notify_err("Tutar 0'dan büyük olmalı")
                                    return
                                yontem = inp_yontem.value or 'NAKIT'
                                banka = (inp_banka_o.value or '').strip() if yontem == 'HAVALE' else ''
                                acik = (inp_aciklama_o.value or '').strip()
                                if banka and yontem == 'HAVALE':
                                    acik = f'{acik} ({banka})' if acik else banka
                                if not acik:
                                    acik = 'Tahsilat' if is_tahsilat else 'Ödeme'
                                try:
                                    add_kasa({
                                        'tarih': inp_tarih_o.value or date.today().isoformat(),
                                        'firma_kod': firma_kod,
                                        'firma_ad': firma['ad'],
                                        'tur': 'GELIR' if is_tahsilat else 'GIDER',
                                        'tutar': tutar,
                                        'odeme_sekli': yontem,
                                        'aciklama': acik,
                                        'banka': banka,
                                    })
                                    notify_ok('Tahsilat kaydedildi' if is_tahsilat else 'Ödeme kaydedildi')
                                    odlg.close()
                                    ui.navigate.to(f'/cari/{firma_kod}')
                                except Exception as e:
                                    notify_err(f'Hata: {e}')

                            ui.button('Kaydet', color=renk, on_click=_save_odeme).props('unelevated')
                    odlg.open()

                ui.button('Ödeme Yap', icon='arrow_upward', color='negative',
                          on_click=lambda: _open_odeme_dialog(False)).props('dense')
                ui.button('Tahsilat Yap', icon='arrow_downward', color='positive',
                          on_click=lambda: _open_odeme_dialog(True)).props('dense')
                ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_ekstre_top).props('dense')

        with ui.tab_panels(tabs, value=ekstre_tab).classes('w-full'):
            with ui.tab_panel(ekstre_tab).classes('q-pa-none'):
                ekstre_columns = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                    {'name': 'tip', 'label': 'Tür', 'field': 'tip', 'align': 'center', 'sortable': True},
                    {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                    {'name': 'borc', 'label': 'Borç', 'field': 'borc', 'align': 'center'},
                    {'name': 'alacak', 'label': 'Alacak', 'field': 'alacak', 'align': 'center'},
                    {'name': 'bakiye', 'label': 'Bakiye', 'field': 'bakiye', 'align': 'center'},
                ]
                ekstre_table = ui.table(
                    columns=ekstre_columns,
                    rows=ekstre_rows,
                    row_key='_rid',
                    pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True},
                ).classes('w-full cari-detay-table cari-ekstre-table').style('--table-extra-rows: 8;')
                ekstre_table.props('flat bordered dense rows-per-page-options="[30]"')
                ekstre_table.pagination = {'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True}
                ekstre_table.update()

                def _ekstre_donem_change(yil, ay):
                    nonlocal ekstre_src, ekstre_rows, son_bakiye
                    donem_state['yil'] = yil
                    donem_state['ay'] = ay
                    ekstre_src = _load_ekstre()
                    ekstre_rows = _with_ids(ekstre_src)
                    son_bakiye = ekstre_src[0]['bakiye'] if ekstre_src else 0
                    ekstre_table.rows = ekstre_rows
                    ekstre_table.update()

                with ui.row().classes('w-full items-center gap-1 q-mt-xs'):
                    ui.input(
                        placeholder='Ara',
                        on_change=lambda e: (setattr(ekstre_table, 'rows', _filter(ekstre_rows, e.value, ['aciklama'])), ekstre_table.update()),
                    ).props('outlined dense clearable').classes('w-44')
                    donem_secici(_ekstre_donem_change, include_all=True)

                ekstre_table.add_slot('body-cell-tarih', TARIH_SLOT)
                ekstre_table.add_slot('header-cell-borc', '''
                    <q-th :props="props" class="text-center">Borç</q-th>
                ''')
                ekstre_table.add_slot('header-cell-alacak', '''
                    <q-th :props="props" class="text-center">Alacak</q-th>
                ''')
                ekstre_table.add_slot('header-cell-bakiye', '''
                    <q-th :props="props" class="text-center">Bakiye</q-th>
                ''')
                ekstre_table.add_slot('body-cell-borc', '''
                    <q-td :props="props" class="text-center">
                        {{ props.value != null && props.value !== 0 ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                    </q-td>
                ''')
                ekstre_table.add_slot('body-cell-alacak', '''
                    <q-td :props="props" class="text-center">
                        {{ props.value != null && props.value !== 0 ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                    </q-td>
                ''')
                ekstre_table.add_slot('body-cell-bakiye', '''
                    <q-td :props="props" class="text-center">
                        <span :class="props.value > 0 ? 'text-positive text-weight-bold' : props.value < 0 ? 'text-negative text-weight-bold' : ''">
                            {{ props.value != null && props.value !== 0 ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                        </span>
                    </q-td>
                ''')
                ekstre_table.add_slot('body-cell-tip', r'''
                    <q-td :props="props">
                        <q-badge dense text-color="white"
                            :color="props.row.tip === 'ALIS' ? 'blue-7' :
                                    props.row.tip === 'SATIS' ? 'teal-7' :
                                    props.row.tip === 'TAHSILAT' ? 'green-7' :
                                    props.row.tip === 'ODEME' ? 'orange-8' :
                                    props.row.tip === 'GIDER' ? 'red-7' :
                                    props.row.tip === 'GELIR' ? 'green-9' :
                                    props.row.tip === 'DEVIR' ? 'indigo-5' : 'grey-6'"
                            class="q-mx-auto">
                            {{ props.row.tip === 'ALIS' ? 'Alış' :
                               props.row.tip === 'SATIS' ? 'Satış' :
                               props.row.tip === 'TAHSILAT' ? 'Tahsilat' :
                               props.row.tip === 'ODEME' ? 'Ödeme' :
                               props.row.tip === 'GIDER' ? 'Gider' :
                               props.row.tip === 'GELIR' ? 'Gelir' :
                               props.row.tip === 'DEVIR' ? 'Devir' : '-' }}
                        </q-badge>
                    </q-td>
                ''')
                ekstre_table.add_slot('body-cell-aciklama', r'''
                    <q-td :props="props">
                        <span>
                            {{ String(props.value || '').replace(/^\s*(Alış|Alis|Satış|Satis|Tahsilat|Ödeme|Odeme|Gider|Gelir)\s*:?\s*(\([^)]*\))?\s*:?\s*/i, '') }}
                        </span>
                    </q-td>
                ''')

            with ui.tab_panel(hareketler_tab).classes('q-pa-none'):
                hareket_cols = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                    {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
                    {'name': 'urun_ad', 'label': 'Ürün', 'field': 'urun_ad', 'align': 'left', 'sortable': True},
                    {'name': 'miktar', 'label': 'Miktar', 'field': 'miktar', 'align': 'right'},
                    {'name': 'birim_fiyat', 'label': 'Birim Fiyat', 'field': 'birim_fiyat', 'align': 'right'},
                    {'name': 'kdvli_toplam', 'label': 'Toplam', 'field': 'kdvli_toplam', 'align': 'right'},
                ]
                hareket_table = ui.table(
                    columns=hareket_cols,
                    rows=hareket_rows,
                    row_key='_rid',
                    pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True},
                ).classes('w-full cari-detay-table cari-hareketler-table').style('--table-extra-rows: 8;')
                hareket_table.props('flat bordered dense rows-per-page-options="[30]"')

                with ui.row().classes('w-full items-center gap-1 q-mt-xs'):
                    ui.input(
                        placeholder='Ara (urun, tur)...',
                        on_change=lambda e: (setattr(hareket_table, 'rows', _filter(hareket_rows, e.value, ['urun_ad', 'tur'])), hareket_table.update()),
                    ).props('outlined dense clearable').classes('w-44')
                    ui.space()

                    def _pdf_hareket():
                        rows = [
                            [r.get('tarih', ''), r.get('tur', ''), r.get('urun_ad', ''), r.get('miktar', 0), r.get('birim_fiyat', 0), r.get('kdvli_toplam', 0)]
                            for r in hareket_rows
                        ]
                        _open_pdf(
                            generate_table_pdf(f"Cari Hareketler - {firma['ad']}", ['Tarih', 'Tür', 'Ürün', 'Miktar', 'Birim Fiyat', 'Toplam'], rows),
                            f"cari_hareketler_{firma_kod}.pdf",
                        )

                    ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_hareket).props('dense')

                hareket_table.add_slot('body-cell-tarih', TARIH_SLOT)
                hareket_table.add_slot('body-cell-birim_fiyat', PARA_SLOT)
                hareket_table.add_slot('body-cell-kdvli_toplam', PARA_SLOT)
                hareket_table.add_slot('body-cell-tur', '''
                    <q-td :props="props">
                        <q-badge :color="props.value === 'ALIS' ? 'blue' : 'green'">
                            {{ props.value === 'ALIS' ? 'Alış' : 'Satış' }}
                        </q-badge>
                    </q-td>
                ''')

            with ui.tab_panel(kasa_tab).classes('q-pa-none'):
                kasa_columns = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                    {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center', 'sortable': True},
                    {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right'},
                    {'name': 'odeme_sekli', 'label': 'Ödeme Sekli', 'field': 'odeme_sekli', 'align': 'center'},
                    {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                ]
                kasa_table = ui.table(
                    columns=kasa_columns,
                    rows=kasa_rows,
                    row_key='_rid',
                    pagination={'rowsPerPage': 50, 'sortBy': 'tarih', 'descending': True},
                ).classes('w-full cari-detay-table cari-kasa-table').style('--table-extra-rows: 8;')
                kasa_table.props('flat bordered dense rows-per-page-options="[30]"')

                with ui.row().classes('w-full items-center gap-1 q-mt-xs'):
                    ui.input(
                        placeholder='Ara (aciklama, odeme)...',
                        on_change=lambda e: (setattr(kasa_table, 'rows', _filter(kasa_rows, e.value, ['aciklama', 'odeme_sekli', 'tur'])), kasa_table.update()),
                    ).props('outlined dense clearable').classes('w-44')
                    ui.space()

                    def _pdf_kasa():
                        try:
                            bakiye_info = {
                                'giris': sum(float(r.get('tutar', 0) or 0) for r in kasa_rows if r.get('tur') == 'GELIR'),
                                'cikis': sum(float(r.get('tutar', 0) or 0) for r in kasa_rows if r.get('tur') == 'GIDER'),
                            }
                            bakiye_info['bakiye'] = bakiye_info['giris'] - bakiye_info['cikis']
                            _open_pdf(generate_kasa_raporu_pdf(kasa_rows, bakiye_info), f"cari_kasa_{firma_kod}.pdf")
                        except Exception as ex:
                            notify_err(f'PDF hatası: {ex}')

                    ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_kasa).props('dense')

                kasa_table.add_slot('body-cell-tarih', TARIH_SLOT)
                kasa_table.add_slot('body-cell-tutar', PARA_SLOT)
                kasa_table.add_slot('body-cell-tur', '''
                    <q-td :props="props">
                        <q-badge :color="props.value === 'GELIR' ? 'green' : 'red'">
                            {{ props.value === 'GELIR' ? 'Tahsilat' : 'Ödeme' }}
                        </q-badge>
                    </q-td>
                ''')

            with ui.tab_panel(cekler_tab).classes('q-pa-none'):
                cek_cols = [
                    {'name': 'cek_no', 'label': 'Çek No', 'field': 'cek_no', 'align': 'left', 'sortable': True},
                    {'name': 'vade_tarih', 'label': 'Vade Tarihi', 'field': 'vade_tarih', 'align': 'center', 'sortable': True},
                    {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right'},
                    {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center', 'sortable': True},
                ]
                cek_table = ui.table(
                    columns=cek_cols,
                    rows=cek_rows,
                    row_key='_rid',
                    pagination={'rowsPerPage': 50, 'sortBy': 'vade_tarih', 'descending': True},
                ).classes('w-full cari-detay-table cari-cekler-table').style('--table-extra-rows: 8;')
                cek_table.props('flat bordered dense rows-per-page-options="[30]"')

                with ui.row().classes('w-full items-center gap-1 q-mt-xs'):
                    ui.input(
                        placeholder='Ara (cek no, durum)...',
                        on_change=lambda e: (setattr(cek_table, 'rows', _filter(cek_rows, e.value, ['cek_no', 'durum'])), cek_table.update()),
                    ).props('outlined dense clearable').classes('w-44')
                    ui.space()

                    def _pdf_cek():
                        _open_pdf(generate_cek_raporu_pdf(cek_rows), f"cari_cekler_{firma_kod}.pdf")

                    ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_cek).props('dense')

                cek_table.add_slot('body-cell-vade_tarih', TARIH_SLOT)
                cek_table.add_slot('body-cell-tutar', PARA_SLOT)
                cek_table.add_slot('body-cell-durum', r'''
                    <q-td :props="props">
                        <q-chip dense text-color="white" size="sm"
                            :color="props.value === 'PORTFOYDE' ? 'blue' :
                                    props.value === 'TAHSILE_VERILDI' ? 'orange' :
                                    props.value === 'TAHSIL_EDILDI' ? 'green' :
                                    props.value === 'CIRO_EDILDI' ? 'purple' :
                                    props.value === 'IADE_EDILDI' ? 'grey' :
                                    props.value === 'KARSILIKSIZ' ? 'red' :
                                    props.value === 'KESILDI' ? 'blue' :
                                    props.value === 'ODENDI' ? 'green' : 'grey'">
                            {{ props.value }}
                        </q-chip>
                    </q-td>
                ''')




