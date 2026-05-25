"""Ödeme / Tahsilat Takibi — vade planı sayfası."""
from datetime import date
from nicegui import ui
from layout import create_layout, fmt_para, notify_ok, notify_err, confirm_dialog
from services.odeme_takibi_service import (
    list_odeme_takibi, get_ozet, add_odeme_takibi, update_odeme_takibi,
    delete_odeme_takibi, ode,
)
from services.cari_service import get_firma_list
from services.banka_service import list_banka_hesaplari

KAYNAK = {'CARI': 'Cari', 'KART': 'Kredi Kartı', 'VERGI': 'Vergi', 'SGK': 'SGK', 'CEK': 'Çek', 'DIGER': 'Diğer'}


@ui.page('/odeme-takibi')
def odeme_takibi_page():
    if not create_layout(active_path='/odeme-takibi', page_title='Ödeme Takibi'):
        return

    filtre = {'tip': None}
    tablo_box = None
    ozet_box = None

    def _refresh():
        _ozet()
        _tablo()

    def _ozet():
        ozet_box.clear()
        o = get_ozet()
        with ozet_box:
            for baslik, deger, renk in [
                ('Açık Borç', o['acik_borc'], 'negative'),
                ('Açık Alacak', o['acik_alacak'], 'positive'),
                ('Geçmiş Vade', o['gecmis_borc'], 'orange'),
            ]:
                with ui.element('div').classes('row items-center no-wrap q-px-sm') \
                        .style('background:#f5f5f5;border-radius:14px;gap:5px;height:28px'):
                    ui.label(baslik + ':').classes('text-caption text-grey-7')
                    ui.label(f"{fmt_para(deger)} TL").classes(f'text-caption text-weight-bold text-{renk}')

    def _tablo():
        tablo_box.clear()
        rows = list_odeme_takibi(tip=filtre['tip'])
        with tablo_box:
            if not rows:
                ui.label('Kayıt yok.').classes('text-grey-7 q-pa-md')
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
            for r in rows:
                kalan = float(r['tutar'] or 0) - float(r['odenen'] or 0)
                disp.append({
                    'id': r['id'],
                    'vade_tarih': r.get('vade_tarih', '') or '-',
                    'tip': 'Borç' if r['tip'] == 'BORC' else 'Alacak',
                    'kaynak': KAYNAK.get(r.get('kaynak'), r.get('kaynak', '')),
                    'firma_ad': r.get('firma_ad', '') or '-',
                    'aciklama': r.get('aciklama', '') or '',
                    'tutar': fmt_para(r['tutar']),
                    'kalan': fmt_para(kalan),
                    'durum': r['durum'],
                })
            tbl = ui.table(columns=columns, rows=disp, row_key='id',
                           pagination={'rowsPerPage': 0}).classes('w-full').props('flat bordered hide-bottom')
            tbl.add_slot('body-cell-durum', r'''
                <q-td :props="props">
                    <q-chip dense :color="props.value==='ODENDI'?'positive':props.value==='KISMI'?'orange':'grey'" text-color="white">
                        {{ props.value }}
                    </q-chip>
                </q-td>''')
            tbl.add_slot('body-cell-actions', r'''
                <q-td :props="props">
                    <q-btn v-if="props.row.durum!=='ODENDI'" flat round dense icon="paid" color="positive" size="sm"
                        @click="$parent.$emit('ode', props.row)"><q-tooltip>Öde/Tahsil</q-tooltip></q-btn>
                    <q-btn flat round dense icon="edit" color="primary" size="sm"
                        @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat round dense icon="delete" color="negative" size="sm"
                        @click="$parent.$emit('sil', props.row)" />
                </q-td>''')
            tbl.on('ode', lambda e: _ode_dialog(e.args))
            tbl.on('edit', lambda e: _form(e.args))
            tbl.on('sil', lambda e: _sil(e.args))

            # Dinamik toplam satiri (filtreye gore) — pagination yerine tek kompakt satir
            top_tutar = sum(float(r['tutar'] or 0) for r in rows)
            top_kalan = sum(float(r['tutar'] or 0) - float(r['odenen'] or 0) for r in rows)
            with ui.row().classes('w-full items-center justify-end no-wrap q-px-md') \
                    .style('background:#eceff1;border-radius:0 0 6px 6px;gap:18px;height:34px'):
                ui.label(f"{len(rows)} kayıt").classes('text-caption text-grey-7')
                ui.label(f"Toplam: {fmt_para(top_tutar)} TL").classes('text-caption text-weight-bold')
                ui.label(f"Kalan: {fmt_para(top_kalan)} TL").classes('text-caption text-weight-bold text-primary')

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

    def _sil(row):
        confirm_dialog(f"'{row['aciklama']}' kaydını silmek istediğinize emin misiniz?",
                       lambda: (delete_odeme_takibi(row['id']), notify_ok('Silindi'), _refresh()))

    # --- PAGE ---
    with ui.column().classes('w-full q-pa-sm gap-1'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Ödeme / Tahsilat Takibi').classes('text-h6 text-weight-bold')
            ui.button('Yeni Plan', icon='add', on_click=lambda: _form(), color='primary').props('unelevated dense')
        # Filtre butonlari + ozet badge'ler ayni satirda
        with ui.row().classes('w-full items-center gap-2'):
            for lbl, val in [('Tümü', None), ('Borçlar', 'BORC'), ('Alacaklar', 'ALACAK')]:
                ui.button(lbl, on_click=lambda v=val: (filtre.update(tip=v), _tablo())).props('outline dense size=sm')
            ozet_box = ui.row().classes('items-center gap-2 q-ml-sm')
        tablo_box = ui.column().classes('w-full')
    _refresh()
