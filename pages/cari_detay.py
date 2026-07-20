"""ALSE Plastik Hammadde - Cari Detay Sayfası"""
from datetime import date, datetime
from nicegui import ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, notify_ok, notify_err, normalize_search, donem_secici, _get_min_year, segment_group
from services.cari_service import (
    get_firma, get_cari_ekstre, get_firma_kasa, get_firma_cekler,
)
from services.kasa_service import add_kasa
from services.banka_service import list_banka_hesaplari
from services.pdf_service import (
    generate_cari_ekstre_pdf,
    generate_kasa_raporu_pdf,
    generate_cek_raporu_pdf,
    save_pdf_preview,
    save_shared_pdf,
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
    /* Coklu kalem akordeonu: acik grup vurgusu — ana satir + kalemler tek blok gibi */
    .cari-ekstre-table tbody tr.ekstre-grup-acik td { background: #e0f2fe !important; }
    .cari-ekstre-table tbody tr.ekstre-kalem-tr td { background: #f0f9ff !important; }
    .cari-ekstre-table tbody tr.ekstre-grup-acik td:first-child,
    .cari-ekstre-table tbody tr.ekstre-kalem-tr td:first-child { box-shadow: inset 3px 0 0 #0284c7; }
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

    def _tip_of(aciklama):
        """Aciklama prefix'inden tur tureti (ekran + PDF filtresi ayni kurali kullanir)."""
        ac = (
            str(aciklama or '').lower()
            .replace('ı', 'i').replace('ş', 's').replace('ö', 'o')
            .replace('ü', 'u').replace('ç', 'c').replace('ğ', 'g')
        )
        if ac.startswith('alis'):
            return 'ALIS'
        elif ac.startswith('satis'):
            return 'SATIS'
        elif ac.startswith('tahsilat'):
            return 'TAHSILAT'
        elif ac.startswith('odeme'):
            return 'ODEME'
        elif ac.startswith('gider'):
            return 'GIDER'
        elif ac.startswith('gelir'):
            return 'GELIR'
        elif 'cek' in ac or 'ciro' in ac:
            return 'CEK'
        elif 'devir' in ac:
            return 'DEVIR'
        return ''

    def _load_ekstre():
        src = get_cari_ekstre(firma_kod, yil=donem_state['yil'], ay=donem_state['ay'])
        src = list(reversed(src))
        for row in src:
            row['tip'] = _tip_of(row.get('aciklama', ''))
        return src

    ekstre_src = _load_ekstre()
    ekstre_rows = _with_ids(ekstre_src)

    kasa_rows = _with_ids(_desc(get_firma_kasa(firma_kod), 'tarih'))
    cek_rows = _with_ids(_desc(get_firma_cekler(firma_kod), 'vade_tarih'))

    son_bakiye = (ekstre_src[0]['bakiye'] if ekstre_src else 0)

    # Ekstre gorunum durumu: arama (q) + tur filtresi (tip). Birlikte uygulanir.
    ekstre_view = {'q': '', 'tip': None}

    with ui.column().classes('w-full q-pa-xs gap-1'):
        with ui.card().classes('w-full q-pa-none cari-top-card'):
            with ui.row().classes('w-full items-center gap-1 q-px-xs q-py-xs cari-topbar').style('flex-wrap: nowrap; overflow: hidden;'):
                with ui.row().classes('items-center gap-2 no-wrap'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/cari')).props('flat round dense')
                    ui.label(firma['ad']).style('font-size:15px;font-weight:700;color:#ffffff;background:#334155;padding:2px 12px;border-radius:6px;')
                    bakiye_color = '#16a34a' if son_bakiye > 0 else '#dc2626' if son_bakiye < 0 else '#64748b'
                    bakiye_desc = 'Alacak' if son_bakiye > 0 else 'Borç' if son_bakiye < 0 else ''
                    ui.label(f'{fmt_para(son_bakiye)} TL ({bakiye_desc})').style(f'font-size:13px;font-weight:600;color:{bakiye_color};')

                    # Tur filtresi (sadece Ekstre sekmesi icin) — bakiye yaninda, boslukla
                    def _on_tur(key):
                        ekstre_view['tip'] = None if key in (None, 'ALL') else key
                        _refresh_ekstre()
                    tur_filtre_box = ui.row().classes('items-center no-wrap q-ml-lg')
                    with tur_filtre_box:
                        segment_group(
                            [('ALL', 'Tümü', '#475569'), ('ALIS', 'Alış', '#1d4ed8'),
                             ('SATIS', 'Satış', '#0f766e'), ('TAHSILAT', 'Tahsilat', '#16a34a'),
                             ('ODEME', 'Ödeme', '#ea580c'), ('CEK', 'Çek', '#7c3aed')],
                            _on_tur, active='ALL')

                with ui.row().classes('items-center justify-center').style('min-width:0; flex:1;'):
                    with ui.tabs().classes('q-px-xs q-py-1 rounded-borders bg-blue-1 text-primary cari-top-tabs').style('max-width: 320px;').props('dense no-caps inline-label') as tabs:
                        ekstre_tab = ui.tab('Ekstre').classes('text-weight-medium')
                        kasa_tab = ui.tab('Kasa').classes('text-weight-medium')
                        cekler_tab = ui.tab('Çekler').classes('text-weight-medium')

                def _pdf_ekstre_top():
                    # Donem secimine gore meta bilgili ekstre cek (donem_label + devir + satirlar)
                    ekstre_meta = get_cari_ekstre(
                        firma_kod, yil=donem_state['yil'], ay=donem_state['ay'], with_meta=True
                    )
                    # Aktif tur filtresi varsa PDF de o filtreye gore (sadece bu sayfada)
                    t = ekstre_view['tip']
                    if t:
                        ekstre_meta = dict(ekstre_meta)
                        ekstre_meta['satirlar'] = [
                            s for s in ekstre_meta.get('satirlar', [])
                            if _tip_of(s.get('aciklama', '')) == t
                        ]
                        # Filtreli ekstrede yuruyen bakiye/devir anlamsiz — sifirla, basliga turu ekle
                        ekstre_meta['devir'] = 0
                        _tur_ad = {'ALIS': 'Alış', 'SATIS': 'Satış', 'TAHSILAT': 'Tahsilat',
                                   'ODEME': 'Ödeme', 'CEK': 'Çek'}.get(t, t)
                        _dl = (ekstre_meta.get('donem_label') or '').strip()
                        ekstre_meta['donem_label'] = (f'{_dl} — {_tur_ad}' if _dl else _tur_ad)
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
                            # Cek/Senet secenekleri kaldirildi: cek islemleri Cekler sayfasindan yapilir
                            # (cek_id NULL ile kasa kaydi aciliyordu - orphan/cift sayim sorununa yol aciyordu)
                            inp_yontem = ui.radio(
                                options={'NAKIT': 'Kasa (Nakit)', 'BANKA': 'Banka'},
                                value='NAKIT'
                            ).props('inline')

                            # Cek/Senet icin ÷Çekler sayfasi÷na yonlendir
                            with ui.row().classes('w-full items-center gap-2 q-mt-xs').style(
                                'background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 10px;'
                            ):
                                ui.icon('info_outline').style('color:#1d4ed8;')
                                ui.label('Çek / Senet için').style('font-size:12px;color:#1e3a8a;')
                                ui.button('Çekler Sayfası', icon='arrow_forward', on_click=lambda: ui.navigate.to('/cekler')).props(
                                    'flat dense color=primary size=sm no-caps'
                                )

                            banka_row_o = ui.row().classes('w-full')
                            banka_row_o.set_visibility(False)
                            with banka_row_o:
                                _bopts_o = {str(h['id']): h['ad'] for h in list_banka_hesaplari(sadece_aktif=True)}
                                inp_banka_o = ui.select(_bopts_o, label='Banka Hesabı').props('outlined dense').classes('col')

                            def _on_yontem(_e):
                                banka_row_o.set_visibility(inp_yontem.value == 'BANKA')
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
                                banka_hesap_id = int(inp_banka_o.value) if (yontem == 'BANKA' and inp_banka_o.value) else None
                                if yontem == 'BANKA' and not banka_hesap_id:
                                    notify_err('Banka hesabı seçmelisiniz')
                                    return
                                acik = (inp_aciklama_o.value or '').strip()
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
                                        'banka_hesap_id': banka_hesap_id,
                                    })
                                    notify_ok('Tahsilat kaydedildi' if is_tahsilat else 'Ödeme kaydedildi')
                                    odlg.close()
                                    ui.navigate.to(f'/cari/{firma_kod}')
                                except Exception as e:
                                    notify_err(f'Hata: {e}')

                            ui.button('Kaydet', color=renk, on_click=_save_odeme).props('unelevated')
                    odlg.open()

                def _normalize_tel(raw):
                    """Turk cep no -> uluslararasi (90...) formata cevirir."""
                    d = ''.join(ch for ch in (raw or '') if ch.isdigit())
                    if not d:
                        return ''
                    if d.startswith('0'):
                        d = d[1:]
                    if not d.startswith('90'):
                        d = '90' + d
                    return d

                async def _whatsapp_bakiye():
                    """Cari bakiye + 15 gün geçerli ekstre PDF linki ile WhatsApp mesajı hazırlar (önizlemeli)."""
                    bugun = datetime.now().strftime('%d.%m.%Y')
                    if son_bakiye > 0:
                        durum = f"Borç bakiyeniz: {fmt_para(son_bakiye)} TL"
                    elif son_bakiye < 0:
                        durum = f"Alacak bakiyeniz: {fmt_para(-son_bakiye)} TL"
                    else:
                        durum = "Bakiyeniz: 0,00 TL (hesabınız kapalı)"
                    # Ekstre PDF olustur + paylasilabilir link (15 gun gecerli)
                    pdf_satiri = ''
                    try:
                        origin = await ui.run_javascript('window.location.origin', timeout=5.0)
                        ekstre_meta = get_cari_ekstre(firma_kod, yil=donem_state['yil'],
                                                      ay=donem_state['ay'], with_meta=True)
                        # Kisa link: https://site/Seyfi_Kaya_Cari_ab12cd.pdf
                        # (firma adinin SADECE ilk iki kelimesi — tam unvan cirkin duruyor)
                        from services.settings_service import get_company_settings as _gcs
                        _fa = (_gcs().get('firma_adi') or '').strip() or 'Firma'
                        _fa = ' '.join(_fa.split()[:2])
                        rel = save_shared_pdf(generate_cari_ekstre_pdf(firma['ad'], ekstre_meta),
                                              prefix=f'ekstre_{firma_kod}',
                                              kisa_ad=f'{_fa} Cari')
                        if origin:
                            # Cari adi + gonderen dosya adinda: "kimin ekstresi, kimden geldi" net olsun
                            pdf_satiri = (f"\n\n📄 {firma['ad']} — detaylı cari hesap ekstreniz "
                                          f"(15 gün geçerlidir):\n{origin}{rel}")
                    except Exception:
                        pdf_satiri = ''
                    varsayilan = (
                        f"Sayın {firma['ad']},\n\n"
                        f"Cari hesabınızın {bugun} tarihli durumu:\n"
                        f"• {durum}"
                        f"{pdf_satiri}\n\n"
                        f"Bilgilerinize sunar, çalışmalarınızda başarılar dileriz."
                    )
                    with ui.dialog() as wdlg, ui.card().classes('alse-dialog').style('width:90vw;max-width:460px'):
                        with ui.element('div').classes('alse-dialog-header'):
                            ui.icon('chat')
                            ui.label('WhatsApp ile Bakiye Gönder').classes('dialog-title')
                        inp_tel = ui.input('Telefon (5xx...)', value=(firma.get('tel') or '')).props(
                            'outlined dense').classes('w-full q-mt-sm')
                        inp_msg = ui.textarea('Mesaj', value=varsayilan).props(
                            'outlined dense autogrow').classes('w-full')
                        if not pdf_satiri:
                            ui.label('Not: Ekstre linki oluşturulamadı, mesaj linksiz gidecek.').classes(
                                'text-caption text-orange-8 q-pl-sm')
                        with ui.row().classes('w-full justify-end q-mt-md'):
                            ui.button('İptal', on_click=wdlg.close).props('flat color=grey')
                            def _ac():
                                import urllib.parse
                                num = _normalize_tel(inp_tel.value)
                                if not num or len(num) < 12:
                                    notify_err('Geçerli telefon girin (örn 5321234567)')
                                    return
                                url = f"https://wa.me/{num}?text={urllib.parse.quote(inp_msg.value or '')}"
                                ui.navigate.to(url, new_tab=True)
                                wdlg.close()
                            ui.button("WhatsApp'ta Aç", icon='open_in_new', color='positive',
                                      on_click=_ac).props('unelevated')
                    wdlg.open()

                ui.button('Ödeme', color='negative',
                          on_click=lambda: _open_odeme_dialog(False)).props('dense no-caps')
                ui.button('Tahsilat', color='positive',
                          on_click=lambda: _open_odeme_dialog(True)).props('dense no-caps')
                ui.button('WhatsApp', icon='chat', color='green-7',
                          on_click=_whatsapp_bakiye).props('dense no-caps')
                ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_ekstre_top).props('dense')

        with ui.tab_panels(tabs, value=ekstre_tab).classes('w-full'):
            with ui.tab_panel(ekstre_tab).classes('q-pa-none'):
                ekstre_columns = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center', 'sortable': True},
                    {'name': 'tip', 'label': 'Tür', 'field': 'tip', 'align': 'center', 'sortable': True},
                    {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                    {'name': 'miktar', 'label': 'Miktar', 'field': 'miktar', 'align': 'right', 'sortable': True},
                    {'name': 'birim_fiyat', 'label': 'Birim Fiyat', 'field': 'birim_fiyat', 'align': 'right', 'sortable': True},
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

                def _refresh_ekstre():
                    # Arama + tur filtresini birlikte uygula
                    rows = ekstre_rows
                    if ekstre_view['tip']:
                        rows = [r for r in rows if r.get('tip') == ekstre_view['tip']]
                    rows = _filter(rows, ekstre_view['q'], ['aciklama'])
                    ekstre_table.rows = rows
                    # Tur filtresi aktifken yuruyen "Bakiye" yaniltici olur — kolonu gizle
                    has_filter = bool(ekstre_view['tip'])
                    ekstre_table.columns = (
                        [c for c in ekstre_columns if c['name'] != 'bakiye']
                        if has_filter else ekstre_columns
                    )
                    ekstre_table.update()

                def _ekstre_donem_change(yil, ay):
                    nonlocal ekstre_src, ekstre_rows, son_bakiye
                    donem_state['yil'] = yil
                    donem_state['ay'] = ay
                    ekstre_src = _load_ekstre()
                    ekstre_rows = _with_ids(ekstre_src)
                    son_bakiye = ekstre_src[0]['bakiye'] if ekstre_src else 0
                    _refresh_ekstre()

                with ui.row().classes('w-full items-center gap-1 q-mt-xs'):
                    ui.input(
                        placeholder='Ara',
                        on_change=lambda e: (ekstre_view.update(q=e.value), _refresh_ekstre()),
                    ).props('outlined dense clearable').classes('w-44')
                    # 3-modlu donem secici: Aylik / Yillik / Tumu (Rabia bildirimi: yil'da 'Tumu' yoktu)
                    # default_current_month=False -> ilk acilis Tumu modunda
                    donem_secici(_ekstre_donem_change, include_all=True, mode_toggle=True, default_current_month=False)

                ekstre_table.add_slot('header-cell-borc', '''
                    <q-th :props="props" class="text-center">Borç</q-th>
                ''')
                ekstre_table.add_slot('header-cell-alacak', '''
                    <q-th :props="props" class="text-center">Alacak</q-th>
                ''')
                ekstre_table.add_slot('header-cell-bakiye', '''
                    <q-th :props="props" class="text-center">Bakiye</q-th>
                ''')
                # Tek 'body' slot: hucre iceriklerinin yani sira coklu kalemli islemler icin
                # akordeon satiri (tiklayinca kalemler acilir)
                ekstre_table.add_slot('body', r'''
                    <q-tr :props="props"
                          :class="(props.row.kalemler && props.row.kalemler.length > 1 ? 'cursor-pointer ' : '') + (props.expand && props.row.kalemler && props.row.kalemler.length > 1 ? 'ekstre-grup-acik' : '')"
                          @click="props.row.kalemler && props.row.kalemler.length > 1 ? props.expand = !props.expand : null">
                        <q-td v-for="col in props.cols" :key="col.name" :props="props"
                              :class="col.name === 'tarih' && !props.row.tarih ? 'tarihsiz-cell' : ''">
                            <template v-if="col.name === 'tarih'">
                                <span v-if="props.row.tarih" style="font-weight:700;font-size:11px;color:#334155;">{{ props.row.tarih.split('-').reverse().join('.') }}</span>
                                <span v-else style="color:#b91c1c;font-weight:600;">⚠ TARİH YOK</span>
                            </template>
                            <template v-else-if="col.name === 'tip'">
                                <q-badge dense text-color="white"
                                    :color="props.row.tip === 'ALIS' ? 'blue-7' :
                                            props.row.tip === 'SATIS' ? 'teal-7' :
                                            props.row.tip === 'TAHSILAT' ? 'green-7' :
                                            props.row.tip === 'ODEME' ? 'orange-8' :
                                            props.row.tip === 'GIDER' ? 'red-7' :
                                            props.row.tip === 'GELIR' ? 'green-9' :
                                            props.row.tip === 'CEK' ? 'deep-purple-6' :
                                            props.row.tip === 'DEVIR' ? 'indigo-5' : 'grey-6'"
                                    class="q-mx-auto">
                                    {{ props.row.tip === 'ALIS' ? 'Alış' :
                                       props.row.tip === 'SATIS' ? 'Satış' :
                                       props.row.tip === 'TAHSILAT' ? 'Tahsilat' :
                                       props.row.tip === 'ODEME' ? 'Ödeme' :
                                       props.row.tip === 'GIDER' ? 'Gider' :
                                       props.row.tip === 'GELIR' ? 'Gelir' :
                                       props.row.tip === 'CEK' ? 'Çek' :
                                       props.row.tip === 'DEVIR' ? 'Devir' : '-' }}
                                </q-badge>
                            </template>
                            <template v-else-if="col.name === 'aciklama'">
                                <q-icon v-if="props.row.kalemler && props.row.kalemler.length > 1"
                                        :name="props.expand ? 'expand_less' : 'expand_more'"
                                        size="16px" class="q-mr-xs text-primary" />
                                <span>
                                    {{ String(props.row.aciklama || '').replace(/^\s*(Alış|Alis|Satış|Satis|Tahsilat|Ödeme|Odeme|Gider|Gelir)\s*:?\s*(\([^)]*\))?\s*:?\s*/i, '') }}
                                </span>
                            </template>
                            <template v-else-if="col.name === 'miktar'">
                                <span v-if="props.row.miktar != null && props.row.miktar !== 0" class="text-grey-9">
                                    {{ Number(props.row.miktar).toLocaleString('tr-TR', {minimumFractionDigits:0, maximumFractionDigits:2}) }}
                                    <span class="text-grey-6 text-caption q-ml-xs">{{ props.row.birim || 'KG' }}</span>
                                </span>
                            </template>
                            <template v-else-if="col.name === 'birim_fiyat'">
                                <span v-if="props.row.birim_fiyat != null && props.row.birim_fiyat !== 0" class="text-grey-9">
                                    {{ Number(props.row.birim_fiyat).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) }} TL
                                </span>
                            </template>
                            <template v-else-if="col.name === 'borc' || col.name === 'alacak'">
                                {{ props.row[col.name] != null && props.row[col.name] !== 0 ? (props.row[col.name] < 0 ? '-' : '') + Math.abs(props.row[col.name]).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                            </template>
                            <template v-else-if="col.name === 'bakiye'">
                                <span :class="props.row.bakiye > 0 ? 'text-positive text-weight-bold' : props.row.bakiye < 0 ? 'text-negative text-weight-bold' : ''">
                                    {{ props.row.bakiye != null && props.row.bakiye !== 0 ? (props.row.bakiye < 0 ? '-' : '') + Math.abs(props.row.bakiye).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' : '' }}
                                </span>
                            </template>
                            <template v-else>{{ col.value }}</template>
                        </q-td>
                    </q-tr>
                    <template v-if="props.row.kalemler && props.row.kalemler.length > 1 && props.expand">
                        <q-tr v-for="(k, ki) in props.row.kalemler" :key="'kalem' + ki" :props="props" class="ekstre-kalem-tr">
                            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                                <template v-if="col.name === 'aciklama'">
                                    <span style="display:inline-flex;align-items:center;color:#334155;font-weight:600;font-size:12px;">
                                        <q-icon name="subdirectory_arrow_right" size="14px" class="q-mr-xs text-grey-6" />
                                        {{ k.urun_ad }}
                                    </span>
                                </template>
                                <template v-else-if="col.name === 'miktar'">
                                    <span v-if="k.miktar != null" class="text-grey-8" style="font-size:12px;">
                                        {{ Number(k.miktar).toLocaleString('tr-TR', {minimumFractionDigits:0, maximumFractionDigits:2}) }}
                                        <span class="text-grey-6 text-caption q-ml-xs">{{ k.birim || 'KG' }}</span>
                                    </span>
                                </template>
                                <template v-else-if="col.name === 'birim_fiyat'">
                                    <span v-if="k.birim_fiyat != null" class="text-grey-8" style="font-size:12px;">
                                        {{ Number(k.birim_fiyat).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) }} TL
                                    </span>
                                </template>
                                <template v-else-if="col.name === 'borc'">
                                    <span v-if="props.row.borc" style="font-size:12px;color:#475569;">{{ Number(k.tutar || 0).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' }}</span>
                                </template>
                                <template v-else-if="col.name === 'alacak'">
                                    <span v-if="props.row.alacak" style="font-size:12px;color:#475569;">{{ Number(k.tutar || 0).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL' }}</span>
                                </template>
                            </q-td>
                        </q-tr>
                    </template>
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

        # Tur filtresi yalnizca Ekstre sekmesinde anlamli — diger sekmelerde gizle
        tabs.on_value_change(
            lambda e: tur_filtre_box.set_visibility(str(e.value) == 'Ekstre'))




