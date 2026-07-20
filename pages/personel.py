"""Cari Takip - Personel Maas Takip Sayfasi (iki panelli: sol liste / sag detay)"""
import html as _html
from datetime import date, datetime, timedelta
from nicegui import ui
from layout import (
    create_layout, fmt_para, notify_ok, notify_err, confirm_dialog,
    IM_MODAL_CSS, f2_kisayolu,
)
from services.personel_service import (
    get_donem_ozet, add_personel, update_personel, delete_personel,
    add_hareket, delete_hareket, get_hareketler, get_son_mesai_ucreti,
    get_rapor_ozet, get_personel,
)
from services.settings_service import get_company_settings
from services.pdf_service import generate_table_pdf, save_pdf_preview

AY_ISIMLERI = {
    1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
    7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık',
}


def _get_haftalar(yil, ay):
    """Secili aydaki haftalari dondurur. Hafta Pazartesi baslar Pazar biter."""
    from calendar import monthrange
    result = []
    seen = set()
    _, gun_sayisi = monthrange(yil, ay)
    for gun in range(1, gun_sayisi + 1):
        d = date(yil, ay, gun)
        iso_yil, iso_hafta, _ = d.isocalendar()
        if iso_hafta in seen:
            continue
        seen.add(iso_hafta)
        pazartesi = d - timedelta(days=d.weekday())
        pazar = pazartesi + timedelta(days=6)
        ay_kisa = AY_ISIMLERI.get(pazartesi.month, '')[:3]
        label = f"{iso_hafta}. Hafta ({pazartesi.day}-{pazar.day} {ay_kisa})"
        result.append({'hafta': iso_hafta, 'baslangic': pazartesi.isoformat(),
                       'bitis': pazar.isoformat(), 'label': label})
    return result


def _fd(s):
    """'YYYY-MM-DD' -> 'dd.mm.yyyy'."""
    s = (s or '')[:10]
    if len(s) == 10 and s[4] == '-':
        return '.'.join(reversed(s.split('-')))
    return s


@ui.page('/personel')
def personel_page():
    if not create_layout(active_path='/personel', page_title='Personel'):
        return

    ui.add_css('''
        .nicegui-content{overflow:hidden !important;}
        .pers-wrap{border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;background:#fff;}
        .pers-menu2{flex:0 0 236px;min-width:0;border-right:1px solid #e2e8f0;background:#faf8ff;display:flex;flex-direction:column;}
        .pers-detay2{flex:1;min-width:0;}
        .pers-seg{display:flex;gap:2px;background:#eef2f6;border-radius:9px;padding:3px;margin:8px 8px 0;flex:0 0 auto;}
        .pers-tab{flex:1;border-radius:7px;font-size:12px !important;color:#64748b;min-height:30px;}
        .pers-tab-act{background:#fff !important;color:#0f172a !important;box-shadow:0 1px 3px rgba(0,0,0,.12);}
        .pers-ozet{padding:9px 12px;border-bottom:1px solid #ece9f6;flex:0 0 auto;}
        .pers-foot{padding:8px;border-top:1px solid #ece9f6;flex:0 0 auto;gap:6px;align-items:center;margin-top:auto;}
        .pers-list{overflow-y:auto;flex:0 0 auto;max-height:360px;padding:6px;}
        .pers-list::-webkit-scrollbar{width:6px;}
        .pers-list::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:6px;}
        .pers-list::-webkit-scrollbar-track{background:transparent;}
        .pers-item{padding:8px 10px;border-radius:10px;gap:9px;margin-bottom:2px;transition:background .12s;}
        .pers-item:hover{background:#f0ebff;}
        .pers-item-sec{background:#f0ebff;box-shadow:inset 3px 0 0 #7c3aed;}
        .pers-ad{font-size:13px;font-weight:600;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;}
        /* KPI ozet seridi */
        .pers-kpi{display:flex;gap:0;border:1px solid #eef0f4;border-radius:10px;overflow:hidden;background:#fcfcfd;}
        .pers-kpi > div{flex:1;padding:7px 11px;border-right:1px solid #eef0f4;min-width:0;}
        .pers-kpi > div:last-child{border-right:none;}
        .pers-kpi .k-lbl{font-size:9px;color:#94a3b8;font-weight:800;letter-spacing:.4px;text-transform:uppercase;}
        .pers-kpi .k-val{font-size:14px;font-weight:800;color:#0f172a;white-space:nowrap;margin-top:1px;}
        /* Sabit tablo (satir sayisindan bagimsiz ayni yukseklik/sutun) */
        .pers-scroll{height:clamp(350px, calc(100vh - 266px), 700px);overflow-y:auto;border:1px solid #e5e7eb;border-radius:10px;background:#fff;}
        .pers-scroll::-webkit-scrollbar{width:8px;}
        .pers-scroll::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:8px;}
        .pers-scroll::-webkit-scrollbar-track{background:transparent;}
        .pers-htbl{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12.5px;}
        .pers-htbl thead th{position:sticky;top:0;z-index:2;background:#1e293b;color:#fff;padding:9px 12px;font-size:11px;font-weight:700;letter-spacing:.2px;}
        .pers-htbl td{padding:7px 12px;border-bottom:1px solid #e2e8f0;color:#334155;overflow:hidden;vertical-align:middle;}
        .pers-htbl tbody tr:nth-child(even){background:#f1f5f9;}
        .pers-htbl tbody tr:hover{background:#eef2ff;}
        .pers-htbl .c-empty{text-align:center;color:#94a3b8;padding:44px 12px;}
        .pers-htbl td .q-btn{opacity:.5;}
        .pers-htbl td .q-btn:hover{opacity:1;}
    ''')

    now = datetime.now()
    ayarlar = get_company_settings()
    is_haftalik = (ayarlar.get('ucret_periyodu') or 'AYLIK') == 'HAFTALIK'

    state = {'tab': 'AKTIF', 'secili': None, 'yil': now.year, 'ay': now.month, 'hafta': 0}

    if is_haftalik:
        _hlar = _get_haftalar(state['yil'], state['ay'])
        _bugun_iso = date.today().isocalendar()[1]
        state['hafta'] = next((h['hafta'] for h in _hlar if h['hafta'] == _bugun_iso),
                              (_hlar[0]['hafta'] if _hlar else 1))

    menu_box = None
    name_slot = None
    btns_slot = None
    body_box = None
    ozet_box = None
    btn_aktif = None
    btn_pasif = None

    def _list_data():
        hafta = state['hafta'] if is_haftalik else 0
        return get_donem_ozet(state['yil'], state['ay'], hafta=hafta, durum=state['tab'])

    # ============================ DIALOGLAR ============================

    def open_personel_dialog(edit_row=None):
        is_edit = edit_row is not None
        title = 'Personel Düzenle' if is_edit else 'Yeni Personel'
        with ui.dialog() as dlg, ui.card().classes('alse-dialog im-modal').style(
                'width: 92vw; max-width: 540px; max-height: 92vh; display: flex; flex-direction: column; padding:0;'):
            with ui.element('div').classes('im-head'):
                ui.icon('badge' if not is_edit else 'drive_file_rename_outline').classes('im-ic')
                ui.label(title).classes('im-title')

            with ui.column().classes('w-full im-body gap-1').style(
                    'overflow-y:auto;flex:1 1 auto;min-height:0;'):
                # Satir 1: Ad Soyad + Durum
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field col'):
                        ui.label('AD SOYAD').classes('im-flabel')
                        inp_ad = ui.input(value=edit_row.get('ad', '') if is_edit else '').props(
                            'outlined dense').classes('w-full pr-ad')
                    with ui.element('div').classes('im-field').style('flex:0 0 110px'):
                        ui.label('DURUM').classes('im-flabel')
                        inp_durum = ui.select(
                            options={'AKTIF': 'Aktif', 'PASIF': 'Pasif'},
                            value=edit_row.get('durum', 'AKTIF') if is_edit else 'AKTIF'
                        ).props('outlined dense').classes('w-full')
                # Satir 2: Maas + Giris + Cikis
                with ui.row().classes('w-full gap-sm no-wrap'):
                    with ui.element('div').classes('im-field').style('flex:0 0 130px'):
                        ui.label('MAAŞ').classes('im-flabel')
                        inp_maas = ui.number(value=edit_row.get('maas', 0) if is_edit else 0, format='%.2f').props(
                            'outlined dense input-class=text-right').classes('w-full pr-maas')
                    with ui.element('div').classes('im-field col'):
                        ui.label('GİRİŞ TARİHİ').classes('im-flabel')
                        inp_giris = ui.input(
                            value=edit_row.get('giris_tarih', '') if is_edit else date.today().isoformat()
                        ).props('outlined dense type=date').classes('w-full pr-giris')
                    with ui.element('div').classes('im-field col'):
                        ui.label('ÇIKIŞ TARİHİ').classes('im-flabel')
                        inp_cikis = ui.input(value=edit_row.get('cikis_tarih', '') if is_edit else '').props(
                            'outlined dense type=date clearable').classes('w-full pr-cikis')
                # Telefon
                with ui.element('div').classes('im-field w-full'):
                    ui.label('TELEFON').classes('im-flabel')
                    inp_tel = ui.input(value=edit_row.get('telefon', '') if is_edit else '').props(
                        'outlined dense').classes('w-full pr-tel')

            with ui.row().classes('w-full justify-end items-center').style(
                    'flex:0 0 auto;overflow:visible;padding:11px 16px;border-top:1px solid #eef2f6;'):
                ui.label('⏎ Enter ilerler · F2 kaydeder').classes('im-enter-hint').style('margin-right:auto')
                btn_iptal = ui.button('İptal', on_click=dlg.close).props('flat color=grey').classes('im-btn-iptal')

                def save():
                    ad = inp_ad.value.strip() if inp_ad.value else ''
                    if not ad:
                        notify_err('Ad Soyad zorunlu')
                        return
                    data = {
                        'ad': ad,
                        'maas': float(inp_maas.value or 0),
                        'durum': inp_durum.value,
                        'giris_tarih': inp_giris.value or '',
                        'cikis_tarih': inp_cikis.value or '',
                        'telefon': inp_tel.value.strip() if inp_tel.value else '',
                    }
                    try:
                        if is_edit:
                            update_personel(edit_row['id'], data)
                            notify_ok('Personel güncellendi')
                        else:
                            add_personel(data)
                            notify_ok('Personel eklendi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                btn_kaydet = ui.button('Kaydet', on_click=save, color=None).props('unelevated no-caps') \
                    .classes('im-btn-kaydet').style(
                    'background:#059669;color:#fff;font-weight:700;padding:7px 22px;border-radius:9px')
        dlg.open()
        # Acilinca odak Ad Soyad'a
        ui.timer(0.2, lambda: inp_ad.run_method('focus'), once=True)
        # Enter zinciri (CLIENT-SIDE): ad -> maas -> giris -> cikis -> telefon -> Kaydet
        ui.timer(0.3, lambda: ui.run_javascript('''
            const modal = [...document.querySelectorAll('.im-modal')].pop();
            if(!modal || modal.__prFlow) return;
            modal.__prFlow = true;
            const kaydet = modal.querySelector('.im-btn-kaydet');
            const iptal = modal.querySelector('.im-btn-iptal');
            const sira = ['.pr-ad', '.pr-maas', '.pr-giris', '.pr-cikis', '.pr-tel'];
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

    def do_delete_personel(pid):
        def confirmed():
            try:
                delete_personel(pid)
                notify_ok('Personel silindi')
                if state['secili'] == pid:
                    state['secili'] = None
                _refresh()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu personeli ve tüm kayıtlarını silmek istediğinize emin misiniz?', confirmed)

    def open_mesai_dialog(row):
        pid = row['personel_id']
        maas = row['maas']
        saat_boleni = 45 if is_haftalik else 225
        default_saat_ucret = (maas / saat_boleni) * 1.5 if maas > 0 else 0
        son_ucret = get_son_mesai_ucreti(pid)
        initial_saat_ucret = son_ucret if son_ucret and son_ucret > 0 else default_saat_ucret

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 480px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('schedule')
                ui.label(f'Mesai Gir - {row["ad"]}').classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                inp_tarih_m = ui.input('Mesai Tarihi', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_tarih_m.add_slot('append'):
                    icon_m = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_m:
                        ui.date(on_change=lambda e: (inp_tarih_m.set_value(e.value), menu_m.close()))
                    icon_m.on('click', menu_m.open)

                with ui.row().classes('w-full gap-md no-wrap'):
                    inp_ucret = ui.number('Saat Ücreti (TL)', value=round(initial_saat_ucret, 2), format='%.2f').props('outlined dense').classes('col')
                    inp_saat = ui.number('Mesai Saat', value=0, format='%.1f').props('outlined dense').classes('col')

                ui.label(
                    f'Standart ücret: {fmt_para(default_saat_ucret)} TL (Maaş/{saat_boleni}×1.5)'
                    + (f'  •  Son girilen: {fmt_para(son_ucret)} TL' if son_ucret else '')
                ).classes('text-caption text-grey-7')

                lbl_tutar = ui.label('Mesai Tutarı: 0,00 TL').classes('text-subtitle2 text-weight-bold text-primary')

                def recalc():
                    s = float(inp_saat.value or 0)
                    u = float(inp_ucret.value or 0)
                    lbl_tutar.set_text(f'Mesai Tutarı: {fmt_para(s * u)} TL')
                inp_saat.on_value_change(lambda _: recalc())
                inp_ucret.on_value_change(lambda _: recalc())

                inp_aciklama = ui.input('Açıklama').props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    saat = float(inp_saat.value or 0)
                    ucret = float(inp_ucret.value or 0)
                    if saat <= 0:
                        notify_err('Saat 0\'dan büyük olmalı')
                        return
                    if ucret <= 0:
                        notify_err('Saat ücreti 0\'dan büyük olmalı')
                        return
                    try:
                        add_hareket({
                            'personel_id': pid, 'yil': state['yil'], 'ay': state['ay'],
                            'hafta': state['hafta'] if is_haftalik else 0,
                            'tur': 'MESAI', 'saat': saat, 'tutar': saat * ucret,
                            'tarih': inp_tarih_m.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        })
                        notify_ok('Mesai kaydedildi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated').classes('im-btn-kaydet')
        dlg.open()

    def open_avans_dialog(row):
        pid = row['personel_id']
        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 420px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('money_off')
                ui.label(f'Avans Ver - {row["ad"]}').classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_tarih.add_slot('append'):
                    icon_t = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_t:
                        ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu_t.close()))
                    icon_t.on('click', menu_t.open)

                inp_tutar = ui.number('Tutar', value=0, format='%.2f').props('outlined dense').classes('w-full')
                inp_odeme = ui.select(options={'NAKIT': 'Nakit', 'HAVALE': 'Havale/EFT'}, label='Ödeme Şekli', value='NAKIT').props('outlined dense').classes('w-full')
                inp_aciklama = ui.input('Açıklama').props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    tutar = float(inp_tutar.value or 0)
                    if tutar <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return
                    try:
                        add_hareket({
                            'personel_id': pid, 'yil': state['yil'], 'ay': state['ay'],
                            'hafta': state['hafta'] if is_haftalik else 0,
                            'tur': 'AVANS', 'tutar': tutar,
                            'tarih': inp_tarih.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                            'odeme_sekli': inp_odeme.value or 'NAKIT',
                        })
                        notify_ok('Avans kaydedildi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated').classes('im-btn-kaydet')
        dlg.open()

    def open_odeme_dialog(row):
        pid = row['personel_id']
        kalan = row.get('kalan', 0)
        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 420px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('payments')
                ui.label(f'Maaş Ödeme - {row["ad"]}').classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                ui.label(f'Kalan: {fmt_para(kalan)} TL').classes('text-subtitle2 text-weight-bold text-negative')

                inp_tarih = ui.input('Tarih', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_tarih.add_slot('append'):
                    icon_t = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_t:
                        ui.date(on_change=lambda e: (inp_tarih.set_value(e.value), menu_t.close()))
                    icon_t.on('click', menu_t.open)

                inp_tutar = ui.number('Tutar', value=max(kalan, 0), format='%.2f').props('outlined dense').classes('w-full')
                inp_odeme = ui.select(options={'NAKIT': 'Nakit', 'HAVALE': 'Havale/EFT'}, label='Ödeme Şekli', value='NAKIT').props('outlined dense').classes('w-full')
                inp_aciklama = ui.input('Açıklama').props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

                def save():
                    tutar = float(inp_tutar.value or 0)
                    if tutar <= 0:
                        notify_err('Tutar 0\'dan büyük olmalı')
                        return
                    try:
                        add_hareket({
                            'personel_id': pid, 'yil': state['yil'], 'ay': state['ay'],
                            'hafta': state['hafta'] if is_haftalik else 0,
                            'tur': 'MAAS_ODEME', 'tutar': tutar,
                            'tarih': inp_tarih.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                            'odeme_sekli': inp_odeme.value or 'NAKIT',
                        })
                        notify_ok('Ödeme kaydedildi')
                        dlg.close()
                        _refresh()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated').classes('im-btn-kaydet')
        dlg.open()

    def open_rapor_dialog():
        with ui.dialog() as rdlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 520px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('assessment')
                ui.label('Personel Raporu').classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                inp_rapor_tipi = ui.radio(options={'YILLIK': 'Yıllık Rapor', 'AYLIK_ARALIK': 'Ay Aralığı'}, value='YILLIK').props('inline')
                inp_rapor_yil = ui.select(options={y: str(y) for y in range(now.year - 2, now.year + 2)}, value=now.year, label='Yıl').props('outlined dense').classes('w-32')

                aralik_row = ui.row().classes('w-full gap-md')
                aralik_row.set_visibility(False)
                with aralik_row:
                    inp_ay1 = ui.select(options={m: AY_ISIMLERI[m] for m in range(1, 13)}, value=1, label='Başlangıç Ay').props('outlined dense').classes('col')
                    inp_ay2 = ui.select(options={m: AY_ISIMLERI[m] for m in range(1, 13)}, value=12, label='Bitiş Ay').props('outlined dense').classes('col')

                inp_rapor_tipi.on_value_change(lambda e: aralik_row.set_visibility(e.value == 'AYLIK_ARALIK'))

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=rdlg.close).props('flat color=grey')

                def _rapor_pdf():
                    try:
                        yil = inp_rapor_yil.value
                        if inp_rapor_tipi.value == 'AYLIK_ARALIK':
                            ay1, ay2 = inp_ay1.value, inp_ay2.value
                            baslik = f'Personel Raporu - {AY_ISIMLERI[ay1]}-{AY_ISIMLERI[ay2]} {yil}'
                        else:
                            ay1 = ay2 = None
                            baslik = f'Personel Raporu - {yil} Yıllık'

                        rapor = get_rapor_ozet(yil, ay1, ay2)
                        headers = ['Personel', 'Durum', 'Maaş', 'Mesai Saat', 'Mesai Tutar', 'Avans', 'Hak Ediş', 'Ödenen', 'Kalan']
                        data_rows = []
                        for r in rapor:
                            data_rows.append([
                                r['ad'], 'Aktif' if r['durum'] == 'AKTIF' else 'Pasif',
                                f"{r['maas']:.2f}",
                                f"{r['toplam_mesai_saat']:.1f}" if r['toplam_mesai_saat'] else '',
                                f"{r['toplam_mesai_tutar']:.2f}" if r['toplam_mesai_tutar'] else '',
                                f"{r['toplam_avans']:.2f}" if r['toplam_avans'] else '',
                                f"{r['toplam_hakedis']:.2f}", f"{r['toplam_odenen']:.2f}", f"{r['toplam_kalan']:.2f}",
                            ])
                        data_rows.append([
                            'TOPLAM', '',
                            f"{sum(r['maas'] for r in rapor):.2f}",
                            f"{sum(r['toplam_mesai_saat'] for r in rapor):.1f}",
                            f"{sum(r['toplam_mesai_tutar'] for r in rapor):.2f}",
                            f"{sum(r['toplam_avans'] for r in rapor):.2f}",
                            f"{sum(r['toplam_hakedis'] for r in rapor):.2f}",
                            f"{sum(r['toplam_odenen'] for r in rapor):.2f}",
                            f"{sum(r['toplam_kalan'] for r in rapor):.2f}",
                        ])
                        pdf_bytes = generate_table_pdf(baslik, headers, data_rows)
                        preview_url = save_pdf_preview(pdf_bytes, f'personel_rapor_{yil}.pdf')
                        ui.run_javascript(f"window.open('{preview_url}', '_blank')")
                        rdlg.close()
                    except Exception as e:
                        notify_err(f'Rapor hatası: {e}')

                ui.button('PDF Oluştur', icon='picture_as_pdf', color='primary', on_click=_rapor_pdf).props('unelevated')
        rdlg.open()

    def _pdf_kisi(p, ozet, hareketler):
        try:
            def _ft(t):
                return {'AVANS': 'Avans', 'MESAI': 'Mesai', 'MAAS_ODEME': 'Maaş Ödeme'}.get(t, t)
            ozet_rows = [
                ['Maaş', '', f"{ozet['maas']:.2f} TL"],
                ['Mesai', f"{ozet['mesai_saat']:.1f} saat", f"{ozet['mesai_tutar']:.2f} TL"],
                ['Hak Ediş', '', f"{ozet['hakedis']:.2f} TL"],
                ['Avans Toplam', '', f"{ozet['avans_toplam']:.2f} TL"],
                ['Ödenen', '', f"{ozet['odenen']:.2f} TL"],
                ['Kalan', '', f"{ozet['kalan']:.2f} TL"],
            ]
            hareket_rows = [
                [h.get('tarih', ''), _ft(h.get('tur', '')), f"{h.get('tutar', 0):.2f}",
                 f"{h.get('saat', 0):.1f}" if h.get('saat', 0) else '', h.get('aciklama', '') or '']
                for h in hareketler
            ]
            all_rows_pdf = [['--- ÖZET ---', '', '', '', '']] \
                + [[r[0], '', r[2], r[1], ''] for r in ozet_rows] \
                + [['--- HAREKETLER ---', '', '', '', '']] + hareket_rows
            baslik = f"Personel Detay - {p['ad']} - {AY_ISIMLERI[state['ay']]} {state['yil']}"
            pdf_bytes = generate_table_pdf(baslik, ['Tarih / Başlık', 'Tür', 'Tutar', 'Saat/Ek', 'Açıklama'], all_rows_pdf)
            preview_url = save_pdf_preview(pdf_bytes, f"personel_{p['id']}_{state['yil']}_{state['ay']}.pdf")
            ui.run_javascript(f"window.open('{preview_url}', '_blank')")
        except Exception as e:
            notify_err(f'PDF hatası: {e}')

    def _sil_hareket(h):
        def ok():
            try:
                delete_hareket(h['id'])
                notify_ok('Hareket silindi')
                _refresh()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu hareketi silmek istediğinize emin misiniz?', ok)

    # ============================ RENDER ============================

    def _render_tablo(hareketler):
        cols = [('Tarih', '92px', 'left'), ('Tür', '118px', 'center'),
                ('Tutar', '128px', 'right'), ('Saat', '66px', 'center'),
                ('Açıklama', None, 'center'), ('', '46px', 'center')]
        tur_map = {
            'AVANS': ('Avans', '#fef3c7', '#b45309'),
            'MESAI': ('Mesai', '#dbeafe', '#1d4ed8'),
            'MAAS_ODEME': ('Maaş Ödeme', '#dcfce7', '#15803d'),
        }
        with ui.element('div').classes('pers-scroll w-full'):
            with ui.element('table').classes('pers-htbl'):
                with ui.element('thead'):
                    with ui.element('tr'):
                        for label, w, al in cols:
                            with ui.element('th').style((f'width:{w};' if w else '') + f'text-align:{al};'):
                                if label:
                                    ui.html(label)
                with ui.element('tbody'):
                    if not hareketler:
                        with ui.element('tr'):
                            with ui.element('td').props('colspan=6').classes('c-empty'):
                                ui.html('Bu dönemde hareket yok.')
                    else:
                        for h in hareketler:
                            _tur = h.get('tur', '')
                            lbl, bg, fg = tur_map.get(_tur, (_tur, '#e2e8f0', '#475569'))
                            saat = float(h.get('saat', 0) or 0)
                            _kesinti = (_tur == 'AVANS')
                            _tutar_str = ('-' if _kesinti else '') + f'{fmt_para(h.get("tutar", 0))} ₺'
                            _tutar_renk = '#dc2626' if _kesinti else '#334155'
                            with ui.element('tr'):
                                with ui.element('td').style('text-align:left;'):
                                    ui.html(_fd(h.get('tarih', '')))
                                with ui.element('td').style('text-align:center;'):
                                    ui.html(f'<span style="background:{bg};color:{fg};padding:1px 9px;'
                                            f'border-radius:999px;font-size:10.5px;font-weight:700;">{lbl}</span>')
                                with ui.element('td').style(f'text-align:right;font-weight:700;color:{_tutar_renk};'):
                                    ui.html(_tutar_str)
                                with ui.element('td').style('text-align:center;'):
                                    ui.html(f'{saat:.1f}' if saat > 0 else '')
                                with ui.element('td').style('text-align:center;'):
                                    ui.html(_html.escape(h.get('aciklama', '') or '')).classes('ellipsis')
                                with ui.element('td').style('text-align:center;'):
                                    ui.button(icon='close', on_click=lambda hh=h: _sil_hareket(hh)) \
                                        .props('flat round dense size=sm color=grey-6').tooltip('Sil')

    def _ozet(data):
        if ozet_box is None:
            return
        ozet_box.clear()
        with ozet_box:
            if not data:
                return
            toplam_kalan = sum(x['kalan'] for x in data)
            ui.label('TOPLAM KALAN').style('font-size:9px;color:#94a3b8;font-weight:800;letter-spacing:.4px')
            ui.label(f"{fmt_para(toplam_kalan)} ₺").style(
                f"font-size:16px;font-weight:800;color:{'#b91c1c' if toplam_kalan > 0 else '#059669'}")

    def _kartlar(data):
        menu_box.clear()
        with menu_box:
            if data and not any(x['personel_id'] == state['secili'] for x in data):
                state['secili'] = data[0]['personel_id']
            elif not data:
                state['secili'] = None
            if not data:
                with ui.column().classes('w-full items-center justify-center text-grey-6').style('min-height:220px;gap:6px'):
                    ui.icon('person_off').style('font-size:30px;opacity:.35')
                    ui.label(f'{"Aktif" if state["tab"] == "AKTIF" else "Pasif"} personel yok').style('font-size:12.5px')
                    ui.label('"YENİ" ile ekleyin').style('font-size:11px;opacity:.7')
                return
            for x in data:
                sec = (x['personel_id'] == state['secili'])
                kalan = x['kalan']
                krenk = '#dc2626' if kalan > 0 else '#94a3b8'
                with ui.row().classes('w-full items-center no-wrap cursor-pointer pers-item' + (' pers-item-sec' if sec else '')) \
                        .on('click', lambda pid=x['personel_id']: _sec(pid)):
                    ui.icon('account_circle').style(f"font-size:19px;color:{'#7c3aed' if sec else '#94a3b8'}")
                    with ui.column().classes('gap-0').style('flex:1;min-width:0'):
                        ui.label(x['ad']).classes('pers-ad')
                        ui.label(f"Kalan {fmt_para(kalan)} ₺").style(f'font-size:11px;font-weight:700;color:{krenk}')

    def _sec(pid):
        state['secili'] = pid
        _refresh()

    def _detay(data):
        name_slot.clear()
        btns_slot.clear()
        body_box.clear()
        pid = state['secili']
        p = get_personel(pid) if pid else None
        ozet = next((x for x in data if x['personel_id'] == pid), None) if pid else None
        if not p or ozet is None:
            with name_slot:
                ui.label('Personel seçilmedi').style('font-size:14px;font-weight:700;color:#94a3b8')
            with body_box:
                with ui.column().classes('w-full items-center justify-center text-grey-5').style('min-height:340px;gap:8px'):
                    ui.icon('badge').style('font-size:34px;opacity:.3')
                    ui.label('Soldan bir personel seçin').style('font-size:13px')
            return

        hafta = state['hafta'] if is_haftalik else 0
        hareketler = get_hareketler(pid, state['yil'], state['ay'], hafta=hafta)
        aktif = (p['durum'] == 'AKTIF')

        # --- Baslik: isim + bilgi ---
        with name_slot:
            ui.icon('account_circle').style('font-size:30px;color:#7c3aed')
            with ui.column().classes('gap-0').style('min-width:0'):
                with ui.row().classes('items-center no-wrap gap-2'):
                    ui.label(p['ad']).classes('pers-ad').style('font-size:16px;font-weight:800;color:#0f172a;line-height:1.15;max-width:220px')
                    ui.html(f'<span style="background:{"#dcfce7" if aktif else "#e2e8f0"};'
                            f'color:{"#15803d" if aktif else "#64748b"};padding:1px 8px;border-radius:999px;'
                            f'font-size:10px;font-weight:700;">{"Aktif" if aktif else "Pasif"}</span>')
                _info = []
                if p.get('telefon'):
                    _info.append(p['telefon'])
                if p.get('giris_tarih'):
                    _info.append('Giriş ' + _fd(p['giris_tarih']))
                if p.get('cikis_tarih'):
                    _info.append('Çıkış ' + _fd(p['cikis_tarih']))
                ui.label('  ·  '.join(_info) if _info else '—').style('font-size:11px;color:#94a3b8;line-height:1.2')

        # --- Baslik: islem ikonlari ---
        with btns_slot:
            ui.button(icon='more_time', on_click=lambda: open_mesai_dialog(ozet)).props('flat round dense color=blue-7').tooltip('Mesai Gir')
            ui.button(icon='account_balance_wallet', on_click=lambda: open_avans_dialog(ozet)).props('flat round dense color=orange-8').tooltip('Avans Ver')
            ui.button(icon='paid', on_click=lambda: open_odeme_dialog(ozet)).props('flat round dense color=green-7').tooltip('Maaş Öde')
            ui.button(icon='description', on_click=lambda: _pdf_kisi(p, ozet, hareketler)).props('flat round dense color=grey-7').tooltip('PDF')
            ui.element('div').style('width:1px;height:22px;background:#e2e8f0;margin:0 3px')
            ui.button(icon='edit', on_click=lambda: open_personel_dialog(edit_row=p)).props('flat round dense color=grey-7').tooltip('Düzenle')
            ui.button(icon='delete', on_click=lambda: do_delete_personel(pid)).props('flat round dense color=grey-6').tooltip('Sil')

        # --- Govde: KPI + sabit tablo ---
        with body_box:
            with ui.element('div').classes('pers-kpi w-full q-mb-sm'):
                def kpi(lbl, val, color=None, sub=None):
                    cstyle = f'color:{color};' if color else ''
                    substr = f'<span style="font-size:10px;color:#94a3b8;font-weight:600;"> · {sub}</span>' if sub else ''
                    with ui.element('div'):
                        ui.html(f'<div class="k-lbl">{lbl}</div><div class="k-val" style="{cstyle}">{val}{substr}</div>')
                kpi('Maaş', f'{fmt_para(ozet["maas"])} ₺')
                kpi('Mesai', f'{fmt_para(ozet["mesai_tutar"])} ₺', sub=(f'{ozet["mesai_saat"]:.1f}s' if ozet['mesai_saat'] else None))
                kpi('Hakediş', f'{fmt_para(ozet["hakedis"])} ₺')
                kpi('Avans', f'{fmt_para(ozet["avans_toplam"])} ₺', color=('#d97706' if ozet['avans_toplam'] else None))
                kpi('Ödenen', f'{fmt_para(ozet["odenen"])} ₺', color=('#059669' if ozet['odenen'] else None))
                kpi('Kalan', f'{fmt_para(ozet["kalan"])} ₺', color=('#dc2626' if ozet['kalan'] > 0 else '#0f172a'))
            _render_tablo(hareketler)

    def _build_donem_pill():
        def _lbl():
            base = f"{AY_ISIMLERI[state['ay']]} {state['yil']}"
            if is_haftalik and state.get('hafta'):
                base += f" · {state['hafta']}.Hf"
            return base
        pill = ui.button(icon='calendar_month').props('flat round dense color=deep-purple-6')
        with pill:
            tt = ui.tooltip(_lbl())
            with ui.menu().props('anchor="bottom middle" self="top middle"'):
                with ui.column().classes('q-pa-sm gap-2').style('min-width:240px'):
                    ui.label('Dönem').classes('text-caption text-grey-7')
                    ay_opts = {m: AY_ISIMLERI[m] for m in range(1, 13)}
                    yil_opts = {y: str(y) for y in range(now.year - 2, now.year + 2)}
                    with ui.row().classes('w-full gap-2 no-wrap'):
                        p_ay = ui.select(ay_opts, value=state['ay'], label='Ay').props('outlined dense').classes('col')
                        p_yil = ui.select(yil_opts, value=state['yil'], label='Yıl').props('outlined dense').classes('col')
                    p_hafta = None
                    if is_haftalik:
                        _ho = {h['hafta']: h['label'] for h in _get_haftalar(state['yil'], state['ay'])}
                        p_hafta = ui.select(_ho, value=state['hafta'], label='Hafta').props('outlined dense').classes('w-full')

                    def _apply():
                        state['yil'] = p_yil.value
                        state['ay'] = p_ay.value
                        if is_haftalik and p_hafta is not None:
                            yeni = _get_haftalar(state['yil'], state['ay'])
                            p_hafta.options = {h['hafta']: h['label'] for h in yeni}
                            if yeni and p_hafta.value not in p_hafta.options:
                                p_hafta.value = yeni[0]['hafta']
                            p_hafta.update()
                            state['hafta'] = p_hafta.value
                        tt.set_text(_lbl())
                        _refresh()

                    p_ay.on_value_change(lambda _: _apply())
                    p_yil.on_value_change(lambda _: _apply())
                    if p_hafta is not None:
                        p_hafta.on_value_change(lambda _: _apply())
        return pill

    def _refresh():
        data = _list_data()
        _ozet(data)
        _kartlar(data)
        _detay(data)

    def _tab_degis(tab):
        state['tab'] = tab
        state['secili'] = None
        if btn_aktif and btn_pasif:
            if tab == 'AKTIF':
                btn_aktif.classes('pers-tab-act')
                btn_pasif.classes(remove='pers-tab-act')
            else:
                btn_aktif.classes(remove='pers-tab-act')
                btn_pasif.classes('pers-tab-act')
        _refresh()

    # ============================ PAGE ============================

    with ui.column().classes('w-full').style('padding:6px 14px 4px;gap:0;'):
        # Iki panel (banka ile ayni yapi) — donem secici sag panelin basliginda
        with ui.row().classes('w-full items-stretch no-wrap pers-wrap'):
            # SOL: Aktif/Pasif + toplam kalan + liste + Yeni/Rapor
            with ui.column().classes('pers-menu2'):
                with ui.row().classes('pers-seg'):
                    btn_aktif = ui.button('Aktif', on_click=lambda: _tab_degis('AKTIF')) \
                        .props('flat no-caps dense').classes('pers-tab pers-tab-act')
                    btn_pasif = ui.button('Pasif', on_click=lambda: _tab_degis('PASIF')) \
                        .props('flat no-caps dense').classes('pers-tab')
                ozet_box = ui.column().classes('pers-ozet w-full gap-0')
                menu_box = ui.column().classes('pers-list w-full gap-0')
                with ui.row().classes('pers-foot w-full no-wrap'):
                    with ui.element('div').style('position:relative;flex:1;display:flex'):
                        ui.button('Yeni', icon='person_add', on_click=lambda: open_personel_dialog()) \
                            .props('unelevated dense no-caps') \
                            .style('flex:1;height:34px;font-size:12px;background:#0f172a;color:#fff;border-radius:9px')
                        ui.label('F2').classes('fkey-hint')
                    ui.button(icon='assessment', on_click=open_rapor_dialog).props('flat dense round color=grey-7') \
                        .tooltip('Personel raporu')
            # SAG: baslik (isim | donem pill | islem ikonlari) + govde
            with ui.column().classes('pers-detay2'):
                with ui.column().classes('w-full').style('padding:12px 16px;gap:0;'):
                    with ui.row().classes('w-full items-center no-wrap q-mb-sm'):
                        name_slot = ui.row().classes('items-center no-wrap gap-2').style('min-width:0;max-width:55%')
                        ui.space()
                        with ui.row().classes('items-center no-wrap gap-1'):
                            _build_donem_pill()
                            btns_slot = ui.row().classes('items-center no-wrap gap-1')
                    body_box = ui.column().classes('w-full gap-0')

    ui.add_css(IM_MODAL_CSS)
    f2_kisayolu(lambda: open_personel_dialog())
    _refresh()
