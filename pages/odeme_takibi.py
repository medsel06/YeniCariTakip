"""Ödeme / Tahsilat Takibi — vade planı sayfası."""
from datetime import date, datetime
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog, segment_group, donem_popover_btn
from services.odeme_takibi_service import (
    list_odeme_takibi, get_ozet, add_odeme_takibi, update_odeme_takibi,
    delete_odeme_takibi, ode, ode_toplu, get_vadeli_cari, get_cek_vadeleri,
)
from services.cari_service import get_firma_list
from services.banka_service import list_banka_hesaplari
from services.kasa_service import add_kasa

KAYNAK = {'CARI': 'Cari', 'KART': 'Kredi Kartı', 'VERGI': 'Vergi', 'SGK': 'SGK', 'CEK': 'Çek', 'DIGER': 'Diğer'}
DURUM_TR = {'ACIK': 'Açık', 'ODENDI': 'Ödendi', 'KISMI': 'Kısmi'}


@ui.page('/odeme-takibi')
def odeme_takibi_page():
    if not create_layout(active_path='/odeme-takibi', page_title='Ödeme Takibi'):
        return

    # Stok sayfasindaki davranis: scroll sayfada degil, tablo govdesinde kalsin.
    # Min-height'i sifirliyoruz ki az kayitta altta bos gri alan olusmasin.
    ui.add_css('''
        .odeme-tbl td, .odeme-tbl th { padding: 2px 10px !important; }
        .odeme-tbl tbody tr { height: 34px; background: #fff; }
        .odeme-tbl tbody td { border-bottom: 1px solid #e0e0e0; }
        .odeme-tbl .q-table__middle {
            min-height: 0 !important;
            max-height: calc(100vh - 210px) !important;
            overflow: auto !important;
            overscroll-behavior: contain;
        }
        .odeme-tbl .q-table { table-layout: fixed; }
        /* Secim modu: checkbox kolonu icin sabit yukseklik/fixed-layout kaldir (kirpilmasin) */
        .odeme-sel .q-table { table-layout: auto !important; }
        .odeme-sel.odeme-tbl tbody tr { height: auto !important; }
        .odeme-sel .q-table tbody td, .odeme-sel .q-table thead th { padding: 4px 10px !important; }
        /* Filtre cubugu butonlarini kompakt yap (segmentler + donem pill) */
        .odeme-filtre .q-btn { min-height: 26px !important; padding: 2px 11px !important; font-size: 11px !important; }
        .odeme-filtre .q-btn .q-icon { font-size: 15px !important; }
        @media (max-width: 1200px) {
            .odeme-tbl .q-table__middle { max-height: calc(100vh - 190px) !important; }
        }
        @media (max-width: 900px) {
            .odeme-tbl .q-table__middle { max-height: calc(100vh - 180px) !important; }
        }
    ''')

    _now = date.today()
    # Varsayilan: icinde bulundugumuz ay (liste kalabalik olmasin). Tumu ile hepsi.
    filtre = {'tip': None, 'kaynak': None, 'yil': _now.year, 'ay': _now.month}
    # Toplu odeme (kredi karti) secim modu: aciksa tablo sadece odenmemis KART borclarini
    # gosterir + checkbox cikar.
    mode = {'secim': False}
    tablo_box = None
    ozet_box = None
    bugun = _now.isoformat()

    def _in_donem(vt):
        if not filtre['yil']:
            return True
        if not vt:
            return False
        if filtre['ay']:
            return str(vt)[:7] == f"{filtre['yil']}-{filtre['ay']:02d}"
        return str(vt)[:4] == str(filtre['yil'])

    def _urgency(vt, durumraw):
        """Vade aciliyeti: ODENDI ise yok; vadesi gectiyse GECIKTI (kirmizi);
        0-7 gun kala YAKLASIYOR (pembe). Doner: (urg, gun_kalan)."""
        if durumraw == 'ODENDI' or not vt:
            return ('', None)
        try:
            d = datetime.strptime(str(vt)[:10], '%Y-%m-%d').date()
        except ValueError:
            return ('', None)
        gk = (d - _now).days
        if gk < 0:
            return ('GECIKTI', gk)
        if gk <= 7:
            return ('YAKLASIYOR', gk)
        return ('', gk)

    def _load_all():
        """Manuel + cari vadeli (FIFO) + cek/senet vadelerini tek listede birlestirir."""
        rows = []
        for r in list_odeme_takibi():
            rows.append({
                '_src': 'MANUEL', 'id': r['id'], 'tip': r['tip'],
                'kaynak': r.get('kaynak', 'DIGER'),
                'kaynak_label': KAYNAK.get(r.get('kaynak'), r.get('kaynak', '')),
                'firma_kod': r.get('firma_kod', '') or '', 'firma_ad': r.get('firma_ad', '') or '',
                'aciklama': r.get('aciklama', '') or '',
                'tutar': float(r['tutar'] or 0), 'odenen': float(r['odenen'] or 0),
                'kalan': float(r['tutar'] or 0) - float(r['odenen'] or 0),
                'vade_tarih': r.get('vade_tarih', '') or '', 'durum': r['durum'],
            })
        for r in get_vadeli_cari():
            d = dict(r); d['_src'] = 'CARI'; rows.append(d)
        for r in get_cek_vadeleri():
            d = dict(r); d['_src'] = 'CEK'; rows.append(d)
        # Toplu odeme modunda: sadece odenmemis kredi karti borclari (donem/diger filtre bypass)
        if mode['secim']:
            rows = [r for r in rows if r['_src'] == 'MANUEL' and r.get('kaynak') == 'KART'
                    and r['tip'] == 'BORC' and r['durum'] != 'ODENDI']
            rows.sort(key=lambda r: (r.get('vade_tarih') or ''), reverse=True)
            return rows
        if filtre['tip']:
            rows = [r for r in rows if r['tip'] == filtre['tip']]
        if filtre['kaynak']:
            rows = [r for r in rows if r['_src'] == filtre['kaynak']]
        rows = [r for r in rows if _in_donem(r.get('vade_tarih', ''))]
        # Vadeye gore azalan: en buyuk (en ileri) vade en ustte, en kucuk en altta.
        # Vadesi bos olanlar en alta.
        rows.sort(key=lambda r: (r.get('vade_tarih') or ''), reverse=True)
        return rows

    def _refresh():
        data = _load_all()
        _ozet(data)
        _tablo(data)

    def _ozet(data):
        ozet_box.clear()
        acik_borc = sum(r['kalan'] for r in data if r['tip'] == 'BORC' and r['durum'] != 'ODENDI')
        acik_alacak = sum(r['kalan'] for r in data if r['tip'] == 'ALACAK' and r['durum'] != 'ODENDI')
        gecmis = sum(r['kalan'] for r in data
                     if r['durum'] != 'ODENDI' and r.get('vade_tarih') and r['vade_tarih'] < bugun)
        with ozet_box:
            for baslik, deger, bg, fg, icon in [
                ('Açık Borç', acik_borc, '#fef2f2', '#b91c1c', 'south_west'),
                ('Açık Alacak', acik_alacak, '#f0fdf4', '#15803d', 'north_east'),
                ('Geçmiş Vade', gecmis, '#fff7ed', '#c2410c', 'warning_amber'),
            ]:
                with ui.element('div').style(
                    f'background:{bg};border:1px solid {fg}33;border-radius:8px;'
                    'padding:3px 10px;min-width:118px;'
                ):
                    with ui.row().classes('items-center no-wrap gap-1'):
                        ui.icon(icon).style(f'color:{fg};font-size:16px')
                        with ui.column().classes('gap-0'):
                            ui.label(baslik).style('font-size:8px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.4px')
                            ui.label(f"{fmt_para(deger)} ₺").style(f'font-size:12.5px;font-weight:800;color:{fg};line-height:1.05')

    def _secim_iptal_bar(mesaj=None):
        """Secim modunda her zaman gorunen ust cubuk (Iptal cikisi garanti)."""
        with ui.row().classes('w-full items-center gap-3 q-pa-sm') \
                .style('background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'):
            ui.icon('credit_card').style('color:#1d4ed8;font-size:22px')
            ui.label(mesaj or 'Kredi Kartı Toplu Ödeme — ekstredeki harcamaları seçip tek ödemede kapatın') \
                .style('font-size:12px;color:#1e3a8a;font-weight:600')
            ui.space()
            ui.button('İptal', on_click=lambda: (mode.update(secim=False), _refresh())) \
                .props('flat dense no-caps color=grey-7')

    def _tablo(data):
        tablo_box.clear()
        with tablo_box:
            if not data:
                if mode['secim']:
                    _secim_iptal_bar('Ödenmemiş kredi kartı harcaması yok. (İptal ile çıkın)')
                else:
                    ui.label('Kayıt yok. Vadeli alış/satış girince veya manuel plan ekleyince burada görünür.').classes('text-grey-7 q-pa-md')
                return
            columns = [
                {'name': 'vade_tarih', 'label': 'Vade', 'field': 'vade_tarih', 'align': 'left', 'sortable': True},
                {'name': 'tip', 'label': 'Tip', 'field': 'tip', 'align': 'center'},
                {'name': 'kaynak', 'label': 'Kaynak', 'field': 'kaynak', 'align': 'center'},
                {'name': 'firma_ad', 'label': 'Kişi/Firma', 'field': 'firma_ad', 'align': 'left'},
                {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
                {'name': 'kalan', 'label': 'Kalan', 'field': 'kalan', 'align': 'right'},
                {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center'},
                {'name': 'actions', 'label': 'İşlem', 'field': 'actions', 'align': 'center'},
            ]
            disp = []
            for r in data:
                src = r['_src']
                rid = f"M{r.get('id')}" if src == 'MANUEL' else (
                    f"C{r.get('hareket_id')}" if src == 'CARI' else f"K{r.get('cek_id')}")
                vt = r.get('vade_tarih', '') or ''
                urg, gk = _urgency(vt, r['durum'])
                vade_disp = '-' if not vt else '.'.join(reversed(str(vt)[:10].split('-')))
                if urg == 'GECIKTI':
                    urgtext = f"{abs(gk)} gün geçti"
                elif urg == 'YAKLASIYOR':
                    urgtext = 'bugün' if gk == 0 else f"{gk} gün kaldı"
                else:
                    urgtext = ''
                disp.append({
                    '_rid': rid, '_src': src,
                    'id': r.get('id'), 'firma_kod': r.get('firma_kod', '') or '',
                    'firma_ad': r.get('firma_ad', '') or '-',
                    'tip': 'Borç' if r['tip'] == 'BORC' else 'Alacak', '_tipraw': r['tip'],
                    'kaynak': r.get('kaynak_label', ''), '_kkod': r.get('kaynak', '') or '',
                    'aciklama': r.get('aciklama', '') or '',
                    'tutar': fmt_para(r['tutar']), '_kalanraw': r['kalan'],
                    'kalan': fmt_para(r['kalan']),
                    'vade_tarih': vade_disp, '_vade_disp': vade_disp,
                    '_urg': urg, '_urgtext': urgtext,
                    'durum': DURUM_TR.get(r['durum'], r['durum']), '_durumraw': r['durum'],
                })
            if mode['secim']:
                _bar = ui.row().classes('w-full items-center gap-3 q-pa-sm') \
                    .style('background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;')
            tbl = ui.table(
                columns=columns, rows=disp, row_key='_rid',
                selection='multiple' if mode['secim'] else None,
                pagination={'rowsPerPage': len(disp) or 1},
            ).classes('w-full odeme-tbl' + (' odeme-sel' if mode['secim'] else '')).props('flat bordered hide-bottom dense')
            if mode['secim']:
                with _bar:
                    ui.icon('credit_card').style('color:#1d4ed8;font-size:22px')
                    ui.label('Kredi Kartı Toplu Ödeme — ekstredeki harcamaları seçip tek ödemede kapatın').style('font-size:12px;color:#1e3a8a;font-weight:600')
                    ui.space()
                    ui.label().bind_text_from(
                        tbl, 'selected',
                        lambda s: f"{len(s)} seçildi · {fmt_para(sum(float(x.get('_kalanraw') or 0) for x in s))} ₺"
                    ).style('font-size:12px;font-weight:700;color:#0f172a')
                    ui.button('Seçilenleri Öde', icon='account_balance_wallet', color='positive',
                              on_click=lambda: _ode_secili(tbl)).props('unelevated dense no-caps')
                    ui.button('İptal', on_click=lambda: (mode.update(secim=False), _refresh())).props('flat dense no-caps color=grey-7')
            tbl.add_slot('body-cell-vade_tarih', r'''
                <q-td :props="props"
                    :style="props.row._urg==='GECIKTI' ? 'border-left:4px solid #ef4444;' :
                            props.row._urg==='YAKLASIYOR' ? 'border-left:4px solid #ec4899;' :
                            'border-left:4px solid transparent;'">
                    <span style="display:inline-block;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px;white-space:nowrap;"
                        :style="props.row._urg==='GECIKTI' ? 'background:#fee2e2;color:#b91c1c;' :
                                props.row._urg==='YAKLASIYOR' ? 'background:#fce7f3;color:#be185d;' :
                                'background:transparent;color:#334155;'">
                        {{ props.row._vade_disp }}
                        <q-tooltip v-if="props.row._urgtext">{{ props.row._urgtext }}</q-tooltip>
                    </span>
                </q-td>''')
            tbl.add_slot('body-cell-kaynak', r'''
                <q-td :props="props">
                    <div class="row items-center no-wrap justify-center" style="gap:4px;">
                        <q-chip dense square text-color="white"
                            :icon="props.row._kkod==='KART' ? 'credit_card' :
                                   props.row._kkod==='CARI' ? 'people' :
                                   props.row._kkod==='CEK' ? 'description' :
                                   props.row._kkod==='VERGI' ? 'gavel' :
                                   props.row._kkod==='SGK' ? 'health_and_safety' :
                                   (props.row._kkod==='KREDI' || props.row._kkod==='BANKA_KREDI') ? 'account_balance' : 'label'"
                            :color="props.row._kkod==='KART' ? 'deep-purple' :
                                    props.row._kkod==='CARI' ? 'blue-7' :
                                    props.row._kkod==='CEK' ? 'orange-8' :
                                    props.row._kkod==='VERGI' ? 'red-7' :
                                    props.row._kkod==='SGK' ? 'teal-7' :
                                    (props.row._kkod==='KREDI' || props.row._kkod==='BANKA_KREDI') ? 'indigo-7' : 'blue-grey-5'"
                            style="font-size:10.5px;height:20px;margin:0;">
                            {{ props.value }}
                        </q-chip>
                        <q-icon :name="props.row._src==='MANUEL' ? 'edit_note' : 'autorenew'" size="14px"
                            :color="props.row._src==='MANUEL' ? 'grey-6' : 'cyan-7'">
                            <q-tooltip>{{ props.row._src==='MANUEL' ? 'Manuel eklendi' : 'Otomatik oluştu (vadeli işlem / çek)' }}</q-tooltip>
                        </q-icon>
                    </div>
                </q-td>''')
            tbl.add_slot('body-cell-durum', r'''
                <q-td :props="props">
                    <span style="display:inline-block;min-width:64px;text-align:center;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:0.2px;"
                        :style="props.value==='Ödendi' ? 'background:#dcfce7;color:#15803d;' :
                                props.value==='Kısmi' ? 'background:#fef3c7;color:#b45309;' :
                                'background:#e0f2fe;color:#0369a1;'">
                        {{ props.value }}
                    </span>
                </q-td>''')
            tbl.add_slot('body-cell-actions', r'''
                <q-td :props="props">
                    <q-btn v-if="props.row._src==='MANUEL' && props.row._durumraw!=='ODENDI'" flat round dense icon="account_balance_wallet" color="positive" size="sm"
                        @click="$parent.$emit('ode', props.row)"><q-tooltip>Öde/Tahsil</q-tooltip></q-btn>
                    <q-btn v-if="props.row._src==='MANUEL'" flat round dense icon="edit" color="primary" size="sm"
                        @click="$parent.$emit('edit', props.row)" />
                    <q-btn v-if="props.row._src==='MANUEL'" flat round dense icon="delete" color="negative" size="sm"
                        @click="$parent.$emit('sil', props.row)" />
                    <q-btn v-if="props.row._src==='CARI' && props.row._durumraw!=='ODENDI'" flat round dense icon="account_balance_wallet" color="positive" size="sm"
                        @click="$parent.$emit('cari_ode', props.row)"><q-tooltip>Tahsilat / Ödeme yap</q-tooltip></q-btn>
                    <q-btn v-if="props.row._src==='CEK'" flat round dense icon="open_in_new" color="primary" size="sm"
                        @click="$parent.$emit('goto_cek', props.row)"><q-tooltip>Çek Sayfası</q-tooltip></q-btn>
                </q-td>''')
            tbl.on('ode', lambda e: _ode_dialog(e.args))
            tbl.on('edit', lambda e: _edit_manuel(e.args))
            tbl.on('sil', lambda e: _sil(e.args))
            tbl.on('cari_ode', lambda e: _cari_ode_dialog(e.args))
            tbl.on('goto_cek', lambda e: ui.navigate.to('/cekler'))

            top_tutar = sum(float(r['tutar'] or 0) for r in data)
            top_kalan = sum(float(r['kalan'] or 0) for r in data)
            with ui.row().classes('w-full items-center justify-end no-wrap q-px-md') \
                    .style('background:#eceff1;border-radius:0 0 6px 6px;gap:18px;height:34px'):
                ui.label(f"{len(data)} kayıt").classes('text-caption text-grey-7')
                ui.label(f"Toplam: {fmt_para(top_tutar)} TL").classes('text-caption text-weight-bold')
                ui.label(f"Kalan: {fmt_para(top_kalan)} TL").classes('text-caption text-weight-bold text-primary')

    def _cari_ode_dialog(row):
        """Cari vadeli satir icin tahsilat/odeme — normal kasa kaydi olusturur,
        FIFO bunu otomatik yansitir (nereden kapatilirsa kapatilsin senkron)."""
        is_tahsilat = row.get('_tipraw') == 'ALACAK'
        baslik = 'Tahsilat Yap' if is_tahsilat else 'Ödeme Yap'
        hesap_opts = {'__nakit__': 'Nakit Kasa'}
        for h in list_banka_hesaplari(sadece_aktif=True):
            hesap_opts[str(h['id'])] = h['ad']
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 380px'):
            ui.label(baslik).classes('text-h6')
            ui.label(f"{row.get('firma_ad', '')} — {row.get('aciklama', '')}").classes('text-caption text-grey-7')
            inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
            with inp_tarih.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as m:
                    ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), m.close()))
                ic.on('click', m.open)
            inp_tutar = ui.number('Tutar', value=float(row.get('_kalanraw') or 0), format='%.2f').props('outlined dense').classes('w-full')
            inp_hesap = ui.select(hesap_opts, value='__nakit__', label='Hesap (nakit/banka)').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    tutar = float(inp_tutar.value or 0)
                    if tutar <= 0:
                        notify_err("Tutar 0'dan büyük olmalı"); return
                    bhid = None if inp_hesap.value == '__nakit__' else int(inp_hesap.value)
                    try:
                        add_kasa({
                            'tarih': inp_tarih.value or date.today().isoformat(),
                            'firma_kod': row.get('firma_kod', ''), 'firma_ad': row.get('firma_ad', ''),
                            'tur': 'GELIR' if is_tahsilat else 'GIDER', 'tutar': tutar,
                            'odeme_sekli': 'BANKA' if bhid else 'NAKIT',
                            'aciklama': ('Tahsilat' if is_tahsilat else 'Ödeme') + f": {row.get('aciklama', '')}",
                            'banka_hesap_id': bhid,
                        })
                        notify_ok('Kaydedildi')
                        dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')
                ui.button('Onayla', color='positive', on_click=_save).props('unelevated')
        dlg.open()

    def _form(row=None):
        duzenle = row is not None
        firmalar = get_firma_list()
        firma_opts = {f['kod']: f['ad'] for f in firmalar}
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 420px'):
            ui.label('Ödeme/Tahsilat Düzenle' if duzenle else 'Yeni Ödeme/Tahsilat Planı').classes('text-h6')
            inp_tip = ui.select({'BORC': 'Borç (ödenecek)', 'ALACAK': 'Alacak (tahsil)'},
                                value=row['tip'] if duzenle else 'BORC', label='Tip').props('outlined dense').classes('w-full')
            inp_kaynak = ui.select(KAYNAK, value=row.get('kaynak', 'DIGER') if duzenle else 'DIGER',
                                   label='Kaynak').props('outlined dense').classes('w-full')
            inp_firma = ui.select(firma_opts, value=row.get('firma_kod') or None if duzenle else None,
                                  label='Kişi/Firma (cari)', with_input=True).props('outlined dense clearable').classes('w-full')
            inp_aciklama = ui.input('Açıklama', value=row.get('aciklama', '') if duzenle else '').props('outlined dense').classes('w-full')
            inp_tutar = ui.number('Tutar', value=float(row['tutar']) if duzenle else 0, format='%.2f').props('outlined dense').classes('w-full')
            inp_vade = ui.input('Vade Tarihi', value=row.get('vade_tarih', '') if duzenle else date.today().isoformat()).props('outlined dense').classes('w-full')
            with inp_vade.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as m:
                    ui.date(on_change=lambda e: (inp_vade.set_value(e.value), m.close()))
                ic.on('click', m.open)
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    if not inp_tutar.value or float(inp_tutar.value) <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı'); return
                    data = {
                        'tip': inp_tip.value, 'kaynak': inp_kaynak.value,
                        'firma_kod': inp_firma.value or '', 'firma_ad': firma_opts.get(inp_firma.value, ''),
                        'aciklama': inp_aciklama.value or '', 'tutar': inp_tutar.value,
                        'vade_tarih': inp_vade.value or '',
                    }
                    try:
                        if duzenle:
                            update_odeme_takibi(row['id'], data); notify_ok('Güncellendi')
                        else:
                            add_odeme_takibi(data); notify_ok('Eklendi')
                        dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')
                ui.button('Kaydet', color='primary', on_click=_save).props('unelevated')
        dlg.open()

    def _ode_dialog(row):
        hesap_opts = {'__nakit__': 'Nakit Kasa'}
        for h in list_banka_hesaplari(sadece_aktif=True):
            hesap_opts[str(h['id'])] = h['ad']
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 380px'):
            ui.label('Öde / Tahsil Et').classes('text-h6')
            ui.label(f"{row['firma_ad']} — {row['aciklama']}").classes('text-caption text-grey-7')
            inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
            with inp_tarih.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as m:
                    ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), m.close()))
                ic.on('click', m.open)
            inp_hesap = ui.select(hesap_opts, value='__nakit__', label='Hesap (nakit/banka)').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    bhid = None if inp_hesap.value == '__nakit__' else int(inp_hesap.value)
                    try:
                        ode(row['id'], tarih=inp_tarih.value, banka_hesap_id=bhid)
                        notify_ok('Ödeme/tahsilat kaydedildi')
                        dlg.close(); _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')
                ui.button('Onayla', color='positive', on_click=_save).props('unelevated')
        dlg.open()

    def _edit_manuel(disp_row):
        """Manuel kaydi DUZENLE: tablodaki gosterim satiri degil, ham DB kaydiyla ac."""
        rid = disp_row.get('id')
        rec = next((x for x in list_odeme_takibi() if x['id'] == rid), None)
        if rec:
            _form(rec)
        else:
            notify_err('Kayıt bulunamadı')

    def _sil(row):
        confirm_dialog(f"'{row['aciklama']}' kaydını silmek istediğinize emin misiniz?",
                       lambda: (delete_odeme_takibi(row['id']), notify_ok('Silindi'), _refresh()))

    def _ode_secili(tbl):
        """Toplu odeme: secili kredi karti borclarini tek odemede kapat."""
        sel = [s for s in (tbl.selected or [])
               if s.get('_src') == 'MANUEL' and s.get('_kkod') == 'KART'
               and s.get('_tipraw') == 'BORC' and s.get('_durumraw') != 'ODENDI']
        if not sel:
            notify_err('Ödenecek kredi kartı harcaması seçmediniz')
            return
        ids = [s.get('id') for s in sel]
        toplam = sum(float(s.get('_kalanraw') or 0) for s in sel)
        hesap_opts = {'__nakit__': 'Nakit Kasa'}
        for h in list_banka_hesaplari(sadece_aktif=True):
            hesap_opts[str(h['id'])] = h['ad']
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width: 400px'):
            ui.label('Kredi Kartı Toplu Ödeme').classes('text-h6')
            ui.label(f"{len(ids)} harcama · Toplam {fmt_para(toplam)} ₺ tek ödemede kapatılacak").classes('text-caption text-grey-7')
            inp_tarih = ui.input('Ödeme Tarihi', value=date.today().isoformat()).props('outlined dense').classes('w-full')
            with inp_tarih.add_slot('append'):
                ic = ui.icon('event').classes('cursor-pointer')
                with ui.menu() as m:
                    ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), m.close()))
                ic.on('click', m.open)
            inp_hesap = ui.select(hesap_opts, value='__nakit__', label='Ödeme Hesabı (nakit/banka)').props('outlined dense').classes('w-full')
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def _save():
                    bhid = None if inp_hesap.value == '__nakit__' else int(inp_hesap.value)
                    try:
                        sonuc = ode_toplu(ids, tarih=inp_tarih.value, banka_hesap_id=bhid)
                        notify_ok(f"{sonuc['adet']} harcama ödendi · {fmt_para(sonuc['toplam'])} ₺")
                        dlg.close()
                        mode.update(secim=False)
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')
                ui.button('Öde', color='positive', on_click=_save).props('unelevated')
        dlg.open()

    def _ipucu_dialog():
        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width:92vw; max-width:640px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('lightbulb')
                ui.label('Ödeme Takibi — Nasıl Kullanılır?').classes('dialog-title')
            with ui.element('div').classes('alse-dialog-body').style('max-height:70vh;overflow-y:auto'):
                def baslik(t):
                    ui.label(t).style('font-size:14px;font-weight:800;color:#1c4461;margin-top:8px')
                def md(t):
                    ui.markdown(t).style('font-size:12.5px;color:#334155')

                baslik('Bu ekran ne işe yarar?')
                md('Vadesi gelecek **ödeme ve tahsilatlarınızı tek yerden** takip edersiniz. '
                   'Üç kaynak otomatik birleşir:')
                md('- **Cari (otomatik):** İşlemler\'de alış/satışa **vade** girdiyseniz buraya düşer. '
                   'Yeşil ⟳ *otomatik* simgesiyle gösterilir. Cariyi nereden kapatırsanız kapatın '
                   '(havale, nakit, cari ekstre) durum otomatik güncellenir (FIFO: en eski vade önce kapanır).\n'
                   '- **Çek / Senet (otomatik):** Açık çek/senet vadeleri otomatik listelenir. Ödeme/tahsilat '
                   '**Çek/Senet sayfasından** yapılır (buradaki ↗ buton oraya götürür).\n'
                   '- **Manuel:** Vergi, SGK, kira, kredi kartı gibi kayıtları **+ Yeni Plan** ile elle eklersiniz.')

                baslik('Renkler ve aciliyet')
                md('- **Sol kenar pembe çubuk + pembe tarih:** vadesine **7 gün ve altı** kaldı.\n'
                   '- **Sol kenar kırmızı çubuk + kırmızı tarih:** vadesi **geçti**.\n'
                   '- Fareyle tarihin üstüne gelince "kaç gün kaldı / kaç gün geçti" görünür.\n'
                   '- **Durum:** Açık (mavi) · Kısmi (turuncu) · Ödendi (yeşil).')

                baslik('Bir kaydı ödemek / tahsil etmek')
                md('İşlem sütununda **cüzdan** simgesine basın. Açılan pencerede tarih ve '
                   '**Nakit Kasa / Banka Hesabı** seçersiniz — banka seçerseniz para o hesaptan düşer. '
                   'Onaylayınca kasa/banka hareketi oluşur ve kayıt **Ödendi** olur.')

                baslik('Kredi kartı toplu ödeme')
                md('Karta ay boyunca birçok harcama girersiniz; ekstre gelince hepsini **tek ödemede** kaparsınız:\n'
                   '1. Üstte **Toplu Ödeme** butonuna basın → tablo otomatik **sadece ödenmemiş kredi kartı** '
                   'harcamalarına süzülür ve seçim kutuları çıkar.\n'
                   '2. Ekstredekileri işaretleyin (1 veya 10 — fark etmez).\n'
                   '3. **Seçilenleri Öde** → tarih + nakit/banka seçin. Tek banka çıkışı oluşur, '
                   'seçilenlerin hepsi **Ödendi** olur. **İptal** ile moddan çıkarsınız.')

                baslik('Filtreler')
                md('- **Göster:** Tümü / Borçlar / Alacaklar.\n'
                   '- **Kaynak:** Tümü / Cari / Çek-Senet / Manuel.\n'
                   '- **Dönem:** 📅 buton → Aylık / Yıllık / Tümü. Varsayılan **içinde bulunduğunuz ay** '
                   '(liste sade kalsın diye); geçmiş/gelecek için değiştirin.')
            with ui.element('div').classes('alse-dialog-footer'):
                ui.button('Anladım', on_click=dlg.close).props('unelevated color=primary no-caps')
        dlg.open()

    # --- PAGE ---
    with ui.column().classes('w-full q-pa-sm gap-2'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Ödeme / Tahsilat Takibi').classes('text-h6 text-weight-bold')
            with ui.row().classes('items-center gap-2 no-wrap'):
                ui.button('İpucu', icon='help_outline', on_click=_ipucu_dialog).props('flat dense no-caps size=sm color=primary')
                ui.button('Toplu Ödeme', icon='checklist',
                          on_click=lambda: (mode.update(secim=True), _refresh())).props('outline dense no-caps size=sm color=deep-purple')
                ui.button('Yeni Plan', icon='add', on_click=lambda: _form(), color='primary').props('unelevated dense')

        # --- Filtre cubugu: bagli segmentler + tek pill donem + ozet (sagda) ---
        with ui.row().classes('w-full items-center gap-3 q-row-mobile-wrap odeme-filtre'):
            def _on_tip(key):
                filtre.update(tip=None if key in (None, 'ALL') else key)
                _refresh()
            with ui.column().classes('gap-0'):
                ui.label('Göster').style('font-size:8.5px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.5px')
                segment_group(
                    [('ALL', 'Tümü', '#475569'), ('BORC', 'Borçlar', '#dc2626'), ('ALACAK', 'Alacaklar', '#16a34a')],
                    _on_tip, active='ALL')

            def _on_kaynak(key):
                filtre.update(kaynak=None if key in (None, 'ALL') else key)
                _refresh()
            with ui.column().classes('gap-0'):
                ui.label('Kaynak').style('font-size:8.5px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.5px')
                segment_group(
                    [('ALL', 'Tümü', '#475569'), ('CARI', 'Cari', '#2563eb'),
                     ('CEK', 'Çek/Senet', '#ea580c'), ('MANUEL', 'Manuel', '#64748b')],
                    _on_kaynak, active='ALL')

            def _on_donem(yil, ay):
                filtre.update(yil=yil, ay=ay)
                _refresh()
            with ui.column().classes('gap-0'):
                ui.label('Dönem').style('font-size:8.5px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.5px')
                donem_popover_btn(_on_donem, default_current_month=True)

            ui.space()
            # Ozet mini kartlar (sagda, kompakt)
            ozet_box = ui.row().classes('items-center gap-2')

        tablo_box = ui.column().classes('w-full')
    _refresh()
