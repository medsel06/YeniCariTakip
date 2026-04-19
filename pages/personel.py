"""Cari Takip - Personel Maas Takip Sayfasi"""
from datetime import date, datetime, timedelta
from nicegui import ui
from layout import (
    create_layout, fmt_para, PARA_SLOT, TARIH_SLOT,
    notify_ok, notify_err, confirm_dialog,
)
from services.personel_service import (
    get_personel_list, get_aktif_personel, add_personel, update_personel,
    delete_personel, get_donem_ozet, add_hareket, delete_hareket, get_hareketler,
    get_son_mesai_ucreti, get_rapor_ozet,
)
from services.settings_service import get_company_settings
from services.pdf_service import generate_table_pdf, save_pdf_preview

AY_ISIMLERI = {
    1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
    7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık',
}


def _get_haftalar(yil, ay):
    """Secili aydaki haftalari dondurur. Hafta Pazartesi baslar Pazar biter.
    Returns: [{hafta: iso_week, baslangic: 'dd.mm', bitis: 'dd.mm', label: '15. Hafta (6-12 Nis)'}]
    """
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
        # Haftanin pazartesi ve pazari
        pazartesi = d - timedelta(days=d.weekday())
        pazar = pazartesi + timedelta(days=6)
        cumartesi = pazartesi + timedelta(days=5)
        ay_kisa = AY_ISIMLERI.get(pazartesi.month, '')[:3]
        label = f"{iso_hafta}. Hafta ({pazartesi.day}-{pazar.day} {ay_kisa})"
        result.append({
            'hafta': iso_hafta,
            'baslangic': pazartesi.isoformat(),
            'bitis': pazar.isoformat(),
            'cumartesi': cumartesi.isoformat(),
            'label': label,
        })
    return result


@ui.page('/personel')
def personel_page():
    if not create_layout(active_path='/personel', page_title='Personel'):
        return

    now = datetime.now()
    state = {
        'yil': now.year,
        'ay': now.month,
    }

    personel_table_ref = None
    aylik_table_ref = None
    aylik_container = None

    # ===================== PERSONEL LISTESI =====================

    personel_columns = [
        {'name': 'ad', 'label': 'Ad Soyad', 'field': 'ad', 'align': 'left', 'sortable': True},
        {'name': 'maas', 'label': 'Maaş', 'field': 'maas', 'align': 'right', 'sortable': True},
        {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center', 'sortable': True},
        {'name': 'giris_tarih', 'label': 'Giriş Tarihi', 'field': 'giris_tarih', 'align': 'center', 'sortable': True},
        {'name': 'telefon', 'label': 'Telefon', 'field': 'telefon', 'align': 'left'},
        {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center'},
    ]

    def load_personel():
        nonlocal personel_table_ref
        rows = get_personel_list()
        if personel_table_ref:
            personel_table_ref.rows = rows
            personel_table_ref.update()

    def open_personel_dialog(edit_row=None):
        is_edit = edit_row is not None
        title = 'Personel Düzenle' if is_edit else 'Yeni Personel'

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('badge' if not is_edit else 'edit')
                ui.label(title).classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                inp_ad = ui.input('Ad Soyad', value=edit_row.get('ad', '') if is_edit else '').props('outlined dense').classes('w-full')
                inp_maas = ui.number('Maaş', value=edit_row.get('maas', 0) if is_edit else 0, format='%.2f').props('outlined dense').classes('w-full')
                inp_durum = ui.select(
                    options={'AKTIF': 'Aktif', 'PASIF': 'Pasif'},
                    label='Durum', value=edit_row.get('durum', 'AKTIF') if is_edit else 'AKTIF'
                ).props('outlined dense').classes('w-full')

                inp_giris = ui.input('Giriş Tarihi', value=edit_row.get('giris_tarih', '') if is_edit else date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_giris.add_slot('append'):
                    icon_g = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_g:
                        ui.date(on_change=lambda e: (inp_giris.set_value(e.value), menu_g.close()))
                    icon_g.on('click', menu_g.open)

                inp_cikis = ui.input('Çıkış Tarihi', value=edit_row.get('cikis_tarih', '') if is_edit else '').props('outlined dense').classes('w-full')
                with inp_cikis.add_slot('append'):
                    icon_c = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_c:
                        ui.date(on_change=lambda e: (inp_cikis.set_value(e.value), menu_c.close()))
                    icon_c.on('click', menu_c.open)

                inp_tel = ui.input('Telefon', value=edit_row.get('telefon', '') if is_edit else '').props('outlined dense').classes('w-full')

            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('İptal', on_click=dlg.close).props('flat color=grey')

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
                        load_personel()
                        load_aylik()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def do_delete_personel(pid):
        def confirmed():
            try:
                delete_personel(pid)
                notify_ok('Personel silindi')
                load_personel()
                load_aylik()
            except Exception as e:
                notify_err(f'Hata: {e}')
        confirm_dialog('Bu personeli ve tüm kayıtlarını silmek istediğinize emin misiniz?', confirmed)

    # ===================== AYLIK ISLEMLER =====================

    def load_aylik():
        nonlocal aylik_table_ref
        hafta = state.get('hafta', 0) if is_haftalik else 0
        rows = get_donem_ozet(state['yil'], state['ay'], hafta=hafta)
        if aylik_table_ref:
            aylik_table_ref.rows = rows
            aylik_table_ref.update()

    def open_mesai_dialog(row):
        pid = row['personel_id']
        maas = row['maas']
        saat_boleni = 45 if is_haftalik else 225
        default_saat_ucret = (maas / saat_boleni) * 1.5 if maas > 0 else 0

        # Son kullanilan saat ucretini hatirla
        son_ucret = get_son_mesai_ucreti(pid)
        initial_saat_ucret = son_ucret if son_ucret and son_ucret > 0 else default_saat_ucret

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 480px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('schedule')
                ui.label(f'Mesai Gir - {row["ad"]}').classes('dialog-title')

            with ui.column().classes('w-full q-mt-sm gap-sm'):
                # Tarih ustte
                inp_tarih_m = ui.input('Mesai Tarihi', value=date.today().isoformat()).props('outlined dense').classes('w-full')
                with inp_tarih_m.add_slot('append'):
                    icon_m = ui.icon('event').classes('cursor-pointer')
                    with ui.menu() as menu_m:
                        ui.date(on_change=lambda e: (inp_tarih_m.set_value(e.value), menu_m.close()))
                    icon_m.on('click', menu_m.open)

                # Saat Ucreti + Mesai Saat yan yana
                with ui.row().classes('w-full gap-md no-wrap'):
                    inp_ucret = ui.number(
                        'Saat Ücreti (TL)', value=round(initial_saat_ucret, 2), format='%.2f',
                    ).props('outlined dense').classes('col')
                    inp_saat = ui.number(
                        'Mesai Saat', value=0, format='%.1f',
                    ).props('outlined dense').classes('col')

                # Bilgi notu
                lbl_info = ui.label(
                    f'Standart ücret: {fmt_para(default_saat_ucret)} TL (Maaş/{saat_boleni}×1.5)'
                    + (f'  •  Son girilen: {fmt_para(son_ucret)} TL' if son_ucret else '')
                ).classes('text-caption text-grey-7')

                lbl_tutar = ui.label('Mesai Tutarı: 0,00 TL').classes('text-subtitle2 text-weight-bold text-primary')

                def recalc():
                    s = float(inp_saat.value or 0)
                    u = float(inp_ucret.value or 0)
                    t = s * u
                    lbl_tutar.set_text(f'Mesai Tutarı: {fmt_para(t)} TL')
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
                            'personel_id': pid,
                            'yil': state['yil'],
                            'ay': state['ay'],
                            'hafta': state.get('hafta', 0) if is_haftalik else 0,
                            'tur': 'MESAI',
                            'saat': saat,
                            'tutar': saat * ucret,
                            'tarih': inp_tarih_m.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                        })
                        notify_ok('Mesai kaydedildi')
                        dlg.close()
                        load_aylik()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
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
                inp_odeme = ui.select(
                    options={'NAKIT': 'Nakit', 'HAVALE': 'Havale/EFT'},
                    label='Ödeme Şekli', value='NAKIT'
                ).props('outlined dense').classes('w-full')
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
                            'personel_id': pid,
                            'yil': state['yil'],
                            'ay': state['ay'],
                            'hafta': state.get('hafta', 0) if is_haftalik else 0,
                            'tur': 'AVANS',
                            'tutar': tutar,
                            'tarih': inp_tarih.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                            'odeme_sekli': inp_odeme.value or 'NAKIT',
                        })
                        notify_ok('Avans kaydedildi')
                        dlg.close()
                        load_aylik()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
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
                inp_odeme = ui.select(
                    options={'NAKIT': 'Nakit', 'HAVALE': 'Havale/EFT'},
                    label='Ödeme Şekli', value='NAKIT'
                ).props('outlined dense').classes('w-full')
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
                            'personel_id': pid,
                            'yil': state['yil'],
                            'ay': state['ay'],
                            'hafta': state.get('hafta', 0) if is_haftalik else 0,
                            'tur': 'MAAS_ODEME',
                            'tutar': tutar,
                            'tarih': inp_tarih.value or date.today().isoformat(),
                            'aciklama': inp_aciklama.value.strip() if inp_aciklama.value else '',
                            'odeme_sekli': inp_odeme.value or 'NAKIT',
                        })
                        notify_ok('Ödeme kaydedildi')
                        dlg.close()
                        load_aylik()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', color='primary', on_click=save).props('unelevated')
        dlg.open()

    def open_detay_dialog(row):
        pid = row['personel_id']
        hafta_val = state.get('hafta', 0) if is_haftalik else 0
        hareketler = get_hareketler(pid, state['yil'], state['ay'], hafta=hafta_val)

        tur_labels = {'AVANS': 'Avans', 'MESAI': 'Mesai', 'MAAS_ODEME': 'Maaş Ödeme'}

        with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 650px'):
            with ui.element('div').classes('alse-dialog-header'):
                ui.icon('list_alt')
                ui.label(f'{row["ad"]} - {AY_ISIMLERI[state["ay"]]} {state["yil"]} Detay').classes('dialog-title')

            if not hareketler:
                ui.label('Bu dönemde hareket bulunmuyor.').classes('text-grey-7 q-mt-md')
            else:
                det_cols = [
                    {'name': 'tarih', 'label': 'Tarih', 'field': 'tarih', 'align': 'center'},
                    {'name': 'tur', 'label': 'Tür', 'field': 'tur', 'align': 'center'},
                    {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right'},
                    {'name': 'saat', 'label': 'Saat', 'field': 'saat', 'align': 'center'},
                    {'name': 'aciklama', 'label': 'Açıklama', 'field': 'aciklama', 'align': 'left'},
                    {'name': 'del', 'label': '', 'field': 'id', 'align': 'center'},
                ]
                det_table = ui.table(columns=det_cols, rows=hareketler, row_key='id').classes('w-full q-mt-sm').props('flat bordered dense')
                det_table.add_slot('body-cell-tarih', TARIH_SLOT)
                det_table.add_slot('body-cell-tutar', PARA_SLOT)
                det_table.add_slot('body-cell-tur', r'''
                    <q-td :props="props">
                        <q-chip dense size="sm"
                            :color="props.value === 'AVANS' ? 'warning' : props.value === 'MESAI' ? 'blue-5' : 'positive'"
                            text-color="white">
                            {{ props.value === 'AVANS' ? 'Avans' : props.value === 'MESAI' ? 'Mesai' : 'Maaş Ödeme' }}
                        </q-chip>
                    </q-td>
                ''')
                det_table.add_slot('body-cell-saat', r'''
                    <q-td :props="props">
                        {{ props.value > 0 ? props.value.toFixed(1) : '' }}
                    </q-td>
                ''')
                det_table.add_slot('body-cell-del', r'''
                    <q-td :props="props">
                        <q-btn flat round dense icon="delete" color="negative" size="sm"
                            @click.stop="$parent.$emit('del_hareket', props.row)">
                            <q-tooltip>Sil</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')

                def on_del(e):
                    h_id = e.args['id']
                    def confirmed():
                        try:
                            delete_hareket(h_id)
                            notify_ok('Hareket silindi')
                            dlg.close()
                            load_aylik()
                        except Exception as ex:
                            notify_err(f'Hata: {ex}')
                    confirm_dialog('Bu hareketi silmek istediğinize emin misiniz?', confirmed)

                det_table.on('del_hareket', on_del)

            def _pdf_detay():
                try:
                    def _fmt_tur(t):
                        return {'AVANS': 'Avans', 'MESAI': 'Mesai', 'MAAS_ODEME': 'Maaş Ödeme'}.get(t, t)
                    # Ozet satirlari
                    maas = row.get('maas', 0)
                    hakedis = row.get('hakedis', 0)
                    mesai_saat = row.get('mesai_saat', 0)
                    mesai_tutar = row.get('mesai_tutar', 0)
                    avans = row.get('avans_toplam', 0)
                    odenen = row.get('odenen', 0)
                    kalan = row.get('kalan', 0)

                    ozet_rows = [
                        ['Maaş', '', f'{maas:.2f} TL'],
                        ['Mesai', f'{mesai_saat:.1f} saat', f'{mesai_tutar:.2f} TL'],
                        ['Hak Ediş', '', f'{hakedis:.2f} TL'],
                        ['Avans Toplam', '', f'{avans:.2f} TL'],
                        ['Ödenen', '', f'{odenen:.2f} TL'],
                        ['Kalan', '', f'{kalan:.2f} TL'],
                    ]
                    hareket_data_rows = [
                        [h.get('tarih', ''), _fmt_tur(h.get('tur', '')),
                         f"{h.get('tutar', 0):.2f}",
                         f"{h.get('saat', 0):.1f}" if h.get('saat', 0) else '',
                         h.get('aciklama', '') or '']
                        for h in hareketler
                    ]
                    # Iki tablo birlesik - once ozet sonra hareketler
                    all_rows_pdf = [
                        ['--- ÖZET ---', '', '', '', ''],
                    ] + [[r[0], '', r[2], r[1], ''] for r in ozet_rows] + [
                        ['--- HAREKETLER ---', '', '', '', ''],
                    ] + hareket_data_rows

                    baslik = f"Personel Detay - {row['ad']} - {AY_ISIMLERI[state['ay']]} {state['yil']}"
                    pdf_bytes = generate_table_pdf(
                        baslik,
                        ['Tarih / Başlık', 'Tür', 'Tutar', 'Saat/Ek', 'Açıklama'],
                        all_rows_pdf,
                    )
                    preview_url = save_pdf_preview(pdf_bytes, f"personel_{row['personel_id']}_{state['yil']}_{state['ay']}.pdf")
                    ui.run_javascript(f"window.open('{preview_url}', '_blank')")
                except Exception as e:
                    notify_err(f'PDF hatası: {e}')

            with ui.row().classes('w-full justify-end q-mt-md gap-sm'):
                ui.button('PDF', icon='picture_as_pdf', color='primary', on_click=_pdf_detay).props('dense')
                ui.button('Kapat', on_click=dlg.close).props('flat')
        dlg.open()

    # ===================== PAGE CONTENT =====================

    with ui.column().classes('w-full q-pa-sm').style('max-width: 1400px; margin: 0 auto'):

        # --- Ust: Personel Listesi ---
        with ui.card().classes('w-full q-pa-xs q-mb-sm'):
            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                ui.label('Personel Listesi').classes('text-h6 text-weight-bold')
                ui.space()

                def open_rapor_dialog():
                    with ui.dialog() as rdlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 520px'):
                        with ui.element('div').classes('alse-dialog-header'):
                            ui.icon('assessment')
                            ui.label('Personel Raporu').classes('dialog-title')

                        with ui.column().classes('w-full q-mt-sm gap-sm'):
                            inp_rapor_tipi = ui.radio(
                                options={
                                    'YILLIK': 'Yıllık Rapor',
                                    'AYLIK_ARALIK': 'Ay Aralığı',
                                },
                                value='YILLIK',
                            ).props('inline')

                            inp_rapor_yil = ui.select(
                                options={y: str(y) for y in range(now.year - 2, now.year + 2)},
                                value=now.year, label='Yıl'
                            ).props('outlined dense').classes('w-32')

                            aralik_row = ui.row().classes('w-full gap-md')
                            aralik_row.set_visibility(False)
                            with aralik_row:
                                inp_ay1 = ui.select(options={m: AY_ISIMLERI[m] for m in range(1, 13)}, value=1, label='Başlangıç Ay').props('outlined dense').classes('col')
                                inp_ay2 = ui.select(options={m: AY_ISIMLERI[m] for m in range(1, 13)}, value=12, label='Bitiş Ay').props('outlined dense').classes('col')

                            def _tip_change(e):
                                aralik_row.set_visibility(e.value == 'AYLIK_ARALIK')
                            inp_rapor_tipi.on_value_change(_tip_change)

                        with ui.row().classes('w-full justify-end q-mt-md'):
                            ui.button('İptal', on_click=rdlg.close).props('flat color=grey')

                            def _rapor_pdf():
                                try:
                                    yil = inp_rapor_yil.value
                                    if inp_rapor_tipi.value == 'AYLIK_ARALIK':
                                        ay1 = inp_ay1.value
                                        ay2 = inp_ay2.value
                                        baslik = f'Personel Raporu - {AY_ISIMLERI[ay1]}-{AY_ISIMLERI[ay2]} {yil}'
                                    else:
                                        ay1 = None
                                        ay2 = None
                                        baslik = f'Personel Raporu - {yil} Yıllık'

                                    rapor = get_rapor_ozet(yil, ay1, ay2)
                                    headers = ['Personel', 'Durum', 'Maaş', 'Mesai Saat', 'Mesai Tutar', 'Avans', 'Hak Ediş', 'Ödenen', 'Kalan']
                                    data_rows = []
                                    for r in rapor:
                                        data_rows.append([
                                            r['ad'],
                                            'Aktif' if r['durum'] == 'AKTIF' else 'Pasif',
                                            f"{r['maas']:.2f}",
                                            f"{r['toplam_mesai_saat']:.1f}" if r['toplam_mesai_saat'] else '',
                                            f"{r['toplam_mesai_tutar']:.2f}" if r['toplam_mesai_tutar'] else '',
                                            f"{r['toplam_avans']:.2f}" if r['toplam_avans'] else '',
                                            f"{r['toplam_hakedis']:.2f}",
                                            f"{r['toplam_odenen']:.2f}",
                                            f"{r['toplam_kalan']:.2f}",
                                        ])
                                    # Toplam satiri
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

                ui.button('Rapor', icon='assessment', color='secondary', on_click=open_rapor_dialog).props('dense')
                ui.button('Yeni Personel', icon='person_add', color='primary',
                          on_click=lambda: open_personel_dialog()).props('dense')

        personel_rows = get_personel_list()
        personel_table_ref = ui.table(
            columns=personel_columns, rows=personel_rows, row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'ad'}
        ).classes('w-full').props('flat bordered dense')

        personel_table_ref.add_slot('body-cell-maas', PARA_SLOT)
        personel_table_ref.add_slot('body-cell-giris_tarih', TARIH_SLOT)

        personel_table_ref.add_slot('body-cell-durum', r'''
            <q-td :props="props">
                <q-chip dense size="sm"
                    :color="props.value === 'AKTIF' ? 'positive' : 'grey-5'"
                    text-color="white">
                    {{ props.value === 'AKTIF' ? 'Aktif' : 'Pasif' }}
                </q-chip>
            </q-td>
        ''')

        personel_table_ref.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="edit" color="primary" size="sm"
                    @click.stop="$parent.$emit('edit_personel', props.row)">
                    <q-tooltip>Düzenle</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete" color="negative" size="sm"
                    @click.stop="$parent.$emit('del_personel', props.row)">
                    <q-tooltip>Sil</q-tooltip>
                </q-btn>
            </q-td>
        ''')
        personel_table_ref.on('edit_personel', lambda e: open_personel_dialog(edit_row=e.args))
        personel_table_ref.on('del_personel', lambda e: do_delete_personel(e.args['id']))

        ui.separator().classes('q-my-sm')

        # --- Alt: Donem Ozet (Aylik veya Haftalik) ---
        ayarlar = get_company_settings()
        is_haftalik = (ayarlar.get('ucret_periyodu') or 'AYLIK') == 'HAFTALIK'
        baslik = 'Haftalık Maaş Tablosu' if is_haftalik else 'Aylık Maaş Tablosu'

        with ui.card().classes('w-full q-pa-xs q-mb-xs'):
            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                ui.label(baslik).classes('text-h6 text-weight-bold')
                ui.space()

                yil_options = {y: str(y) for y in range(now.year - 2, now.year + 2)}
                ay_options = {m: AY_ISIMLERI[m] for m in range(1, 13)}

                sel_ay = ui.select(options=ay_options, value=state['ay'], label='Ay').props('outlined dense').classes('w-32')
                sel_yil = ui.select(options=yil_options, value=state['yil'], label='Yıl').props('outlined dense').classes('w-28')

                # Haftalik ise hafta secici
                sel_hafta = None
                if is_haftalik:
                    haftalar = _get_haftalar(state['yil'], state['ay'])
                    # Mevcut haftayi bul
                    bugun = date.today()
                    bugun_iso_hafta = bugun.isocalendar()[1]
                    default_hafta = haftalar[0]['hafta'] if haftalar else 1
                    for h in haftalar:
                        if h['hafta'] == bugun_iso_hafta:
                            default_hafta = h['hafta']
                            break
                    state['hafta'] = default_hafta
                    hafta_options = {h['hafta']: h['label'] for h in haftalar}
                    sel_hafta = ui.select(options=hafta_options, value=default_hafta, label='Hafta').props('outlined dense').classes('w-56')

                def on_donem_change():
                    state['yil'] = sel_yil.value
                    state['ay'] = sel_ay.value
                    if is_haftalik and sel_hafta:
                        # Ay degisince haftalar guncellenmeli
                        yeni_haftalar = _get_haftalar(state['yil'], state['ay'])
                        yeni_opts = {h['hafta']: h['label'] for h in yeni_haftalar}
                        sel_hafta.options = yeni_opts
                        if yeni_haftalar:
                            sel_hafta.value = yeni_haftalar[0]['hafta']
                        sel_hafta.update()
                        state['hafta'] = sel_hafta.value
                    load_aylik()

                def on_hafta_change():
                    if sel_hafta:
                        state['hafta'] = sel_hafta.value
                    load_aylik()

                sel_ay.on_value_change(lambda _: on_donem_change())
                sel_yil.on_value_change(lambda _: on_donem_change())
                if sel_hafta:
                    sel_hafta.on_value_change(lambda _: on_hafta_change())

        aylik_columns = [
            {'name': 'ad', 'label': 'Çalışan', 'field': 'ad', 'align': 'left', 'sortable': True},
            {'name': 'maas', 'label': 'Maaş', 'field': 'maas', 'align': 'right', 'sortable': True},
            {'name': 'mesai_saat', 'label': 'Mesai Saat', 'field': 'mesai_saat', 'align': 'center'},
            {'name': 'mesai_tutar', 'label': 'Mesai Tutar', 'field': 'mesai_tutar', 'align': 'right'},
            {'name': 'avans_toplam', 'label': 'Avans', 'field': 'avans_toplam', 'align': 'right'},
            {'name': 'hakedis', 'label': 'Hak Ediş', 'field': 'hakedis', 'align': 'right'},
            {'name': 'odenen', 'label': 'Ödenen', 'field': 'odenen', 'align': 'right'},
            {'name': 'kalan', 'label': 'Kalan', 'field': 'kalan', 'align': 'right'},
            {'name': 'actions', 'label': 'İşlemler', 'field': 'actions', 'align': 'center'},
        ]

        hafta_init = state.get('hafta', 0) if is_haftalik else 0
        aylik_rows = get_donem_ozet(state['yil'], state['ay'], hafta=hafta_init)
        aylik_table_ref = ui.table(
            columns=aylik_columns, rows=aylik_rows, row_key='personel_id',
            pagination={'rowsPerPage': 50}
        ).classes('w-full').props('flat bordered dense')

        aylik_table_ref.add_slot('body-cell-maas', PARA_SLOT)
        aylik_table_ref.add_slot('body-cell-mesai_tutar', PARA_SLOT)
        aylik_table_ref.add_slot('body-cell-avans_toplam', PARA_SLOT)
        aylik_table_ref.add_slot('body-cell-hakedis', PARA_SLOT)
        aylik_table_ref.add_slot('body-cell-odenen', PARA_SLOT)

        # Mesai saat - bos gosterme
        aylik_table_ref.add_slot('body-cell-mesai_saat', r'''
            <q-td :props="props">
                {{ props.value > 0 ? props.value.toFixed(1) : '' }}
            </q-td>
        ''')

        # Kalan - kirmizi renk
        aylik_table_ref.add_slot('body-cell-kalan', r'''
            <q-td :props="props">
                <span :style="props.value > 0 ? 'color: #C10015; font-weight: bold' : ''">
                    {{ props.value != null && props.value !== 0
                        ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
                        : '' }}
                </span>
            </q-td>
        ''')

        # Islem butonlari
        aylik_table_ref.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn flat round dense icon="schedule" color="blue-7" size="sm"
                    @click.stop="$parent.$emit('mesai', props.row)">
                    <q-tooltip>Mesai Gir</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="money_off" color="warning" size="sm"
                    @click.stop="$parent.$emit('avans', props.row)">
                    <q-tooltip>Avans Ver</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="payments" color="positive" size="sm"
                    @click.stop="$parent.$emit('odeme', props.row)">
                    <q-tooltip>Maaş Ödeme</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="list_alt" color="grey-7" size="sm"
                    @click.stop="$parent.$emit('detay', props.row)">
                    <q-tooltip>Detay</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        aylik_table_ref.on('mesai', lambda e: open_mesai_dialog(e.args))
        aylik_table_ref.on('avans', lambda e: open_avans_dialog(e.args))
        aylik_table_ref.on('odeme', lambda e: open_odeme_dialog(e.args))
        aylik_table_ref.on('detay', lambda e: open_detay_dialog(e.args))
