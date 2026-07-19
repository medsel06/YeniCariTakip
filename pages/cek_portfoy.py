"""Çek/Senet Portföyü — aktif (kapanmamış) çekler; girecek/çıkacak para ve vade aksiyonu."""
from nicegui import ui
from layout import create_layout, fmt_para
from services.cek_service import get_cek_portfoy


@ui.page('/cek-portfoy')
def cek_portfoy_page():
    if not create_layout(active_path='/cek-portfoy', page_title='Çek Portföyü'):
        return
    data = get_cek_portfoy()

    def _vade_disp(iso):
        return '-' if not iso else '.'.join(reversed(str(iso)[:10].split('-')))

    def _gun_text(g):
        if g is None:
            return ('', 'grey')
        if g < 0:
            return (f'{abs(g)} gün geçti', 'red')
        if g == 0:
            return ('bugün', 'orange')
        if g <= 7:
            return (f'{g} gün kaldı', 'orange')
        return (f'{g} gün', 'grey')

    with ui.column().classes('w-full q-pa-sm gap-3'):
        # --- Ozet kartlari: girecek / cikacak / net ---
        with ui.row().classes('w-full gap-3 no-wrap'):
            def _ozet_kart(baslik, tutar, renk, ikon):
                with ui.card().classes('col q-pa-md').style(f'border-left:5px solid {renk}'):
                    with ui.row().classes('items-center gap-2 no-wrap'):
                        ui.icon(ikon).style(f'color:{renk};font-size:26px')
                        with ui.column().classes('gap-0'):
                            ui.label(baslik).classes('text-caption text-grey-7')
                            ui.label(f'{fmt_para(tutar)} TL').style(
                                f'font-size:18px;font-weight:800;color:{renk}')
            _ozet_kart('Girecek (Tahsil Edilecek)', data['toplam_tahsil'], '#16a34a', 'south_west')
            _ozet_kart('Çıkacak (Ödenecek)', data['toplam_odeme'], '#dc2626', 'north_east')
            net = data['net']
            _ozet_kart('Net', net, '#2563eb' if net >= 0 else '#dc2626', 'account_balance')

        # --- iki bolum: tahsil edilecek / odenecek ---
        def _bolum(baslik, rows, bucket, bos_msg):
            geciken = bucket['geciken']
            with ui.card().classes('w-full q-pa-sm'):
                with ui.row().classes('w-full items-center q-mb-xs gap-2'):
                    ui.label(baslik).classes('text-subtitle2 text-weight-bold')
                    ui.space()
                    if geciken > 0:
                        ui.label(f'⚠ Geciken: {fmt_para(geciken)} TL').classes('text-caption text-weight-bold') \
                            .style('color:#b91c1c;background:#fee2e2;padding:2px 8px;border-radius:6px')
                    ui.label(f'{len(rows)} adet').classes('text-caption text-grey-7')
                if not rows:
                    with ui.row().classes('w-full flex-center q-pa-md text-grey-6'):
                        ui.icon('inbox').style('font-size:18px')
                        ui.label(bos_msg).style('font-size:12.5px')
                    return
                cols = [
                    {'name': 'vade', 'label': 'Vade', 'field': 'vade', 'align': 'left'},
                    {'name': 'durum_gun', 'label': 'Durum', 'field': 'durum_gun', 'align': 'left'},
                    {'name': 'cek_no', 'label': 'No', 'field': 'cek_no', 'align': 'left'},
                    {'name': 'firma_ad', 'label': 'Firma / Keşideci', 'field': 'firma_ad', 'align': 'left'},
                    {'name': 'evrak', 'label': 'Tür', 'field': 'evrak', 'align': 'center'},
                    {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right'},
                ]
                disp = []
                for r in rows:
                    gtext, grenk = _gun_text(r.get('_gun'))
                    disp.append({
                        'id': r.get('id'),
                        'vade': _vade_disp(r.get('vade_tarih')),
                        '_gtext': gtext, '_grenk': grenk,
                        'cek_no': r.get('cek_no', '') or '-',
                        'firma_ad': r.get('firma_ad', '') or r.get('kesideci', '') or '-',
                        'evrak': 'Senet' if r.get('evrak_tipi') == 'SENET' else 'Çek',
                        'tutar': fmt_para(r.get('tutar', 0)),
                    })
                tbl = ui.table(columns=cols, rows=disp, row_key='id',
                               pagination={'rowsPerPage': 0}).classes('w-full').props('flat bordered dense hide-bottom')
                tbl.add_slot('body-cell-durum_gun', r'''
                    <q-td :props="props">
                        <span v-if="props.row._gtext"
                            :style="'display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap;' + (
                                props.row._grenk==='red' ? 'background:#fee2e2;color:#b91c1c;' :
                                props.row._grenk==='orange' ? 'background:#fef3c7;color:#b45309;' :
                                'background:#f1f5f9;color:#475569;')">{{ props.row._gtext }}</span>
                    </q-td>''')
                tbl.add_slot('body-cell-tutar', r'''
                    <q-td :props="props" class="text-right text-weight-bold">{{ props.value }} TL</q-td>''')
                tbl.on('row-click', lambda e: ui.navigate.to('/cekler'))
                ui.label('Aksiyon için satıra tıkla → Çek/Senet sayfası').classes('text-caption text-grey-5 q-mt-xs')

        _bolum('💰 Tahsil Edilecek — Alınan Çek/Senet', data['tahsil'], data['tahsil_bucket'],
               'Portföyde bekleyen alınan çek/senet yok.')
        _bolum('💸 Ödenecek — Verilen Çek/Senet', data['odeme'], data['odeme_bucket'],
               'Ödenmeyi bekleyen verilen çek/senet yok.')
