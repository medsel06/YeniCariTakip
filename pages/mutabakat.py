"""Cari mutabakat ekrani."""
from datetime import date
from nicegui import ui

from layout import create_layout, notify_ok, notify_err, PARA_SLOT, TARIH_SLOT
from services.cari_service import get_firma_list, get_cari_bakiye_list
from services.mutabakat_service import list_mutabakat, add_mutabakat


@ui.page('/mutabakat')
def mutabakat_page():
    if not create_layout(active_path='/mutabakat', page_title='Cari Mutabakat'):
        return
    rows = list_mutabakat()
    firms = get_firma_list()
    firma_options = {f['kod']: f['ad'] for f in firms}

    def _sistem_bakiye(kod):
        for r in get_cari_bakiye_list():
            if r['kod'] == kod:
                return float(r.get('bakiye', 0) or 0)
        return 0.0

    tam_sayisi = len([r for r in rows if r.get('durum') == 'TAM'])
    farkli_sayisi = len(rows) - tam_sayisi

    with ui.column().classes('w-full q-pa-sm'):
        with ui.grid(columns='repeat(3, 1fr)').classes('w-full gap-2 q-mb-xs'):
            with ui.card().classes('q-pa-sm'):
                ui.label('Toplam Mutabakat').classes('text-caption text-grey-7')
                ui.label(str(len(rows))).classes('text-h6 text-weight-bold')
            with ui.card().classes('q-pa-sm'):
                ui.label('Tam Eslesme').classes('text-caption text-positive')
                ui.label(str(tam_sayisi)).classes('text-h6 text-weight-bold text-positive')
            with ui.card().classes('q-pa-sm'):
                ui.label('Farkli Kayit').classes('text-caption text-negative')
                ui.label(str(farkli_sayisi)).classes('text-h6 text-weight-bold text-negative')

        with ui.card().classes('w-full q-pa-sm q-mb-xs'):
            with ui.row().classes('w-full items-center gap-2'):
                inp_firma = ui.select(firma_options, label='Firma', with_input=True).props('outlined dense').classes('w-80')
                inp_tarih = ui.input('Mutabakat Tarihi').props('outlined dense').classes('w-40')
                inp_tarih.value = date.today().isoformat()
                inp_firma_bakiye = ui.number('Firma Beyan Bakiyesi', value=0, format='%.2f').props('outlined dense').classes('w-48')
                inp_not = ui.input('Not').props('outlined dense').classes('w-64')

                def _kaydet():
                    try:
                        if not inp_firma.value:
                            notify_err('Firma secmelisiniz')
                            return
                        sistem = _sistem_bakiye(inp_firma.value)
                        firma_b = float(inp_firma_bakiye.value or 0)
                        fark = firma_b - sistem
                        durum = 'TAM' if abs(fark) < 0.01 else 'FARKLI'
                        add_mutabakat({
                            'firma_kod': inp_firma.value,
                            'firma_ad': firma_options.get(inp_firma.value, ''),
                            'mutabakat_tarih': inp_tarih.value or '',
                            'sistem_bakiye': sistem,
                            'firma_bakiye': firma_b,
                            'fark': fark,
                            'durum': durum,
                            'notlar': inp_not.value or '',
                        })
                        notify_ok('Mutabakat kaydi eklendi')
                        table.rows = list_mutabakat()
                        table.update()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', icon='save', color='primary', on_click=_kaydet)

        columns = [
            {'name': 'mutabakat_tarih', 'label': 'Tarih', 'field': 'mutabakat_tarih', 'align': 'center', 'sortable': True},
            {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
            {'name': 'sistem_bakiye', 'label': 'Sistem', 'field': 'sistem_bakiye', 'align': 'right', 'sortable': True},
            {'name': 'firma_bakiye', 'label': 'Firma Beyan', 'field': 'firma_bakiye', 'align': 'right', 'sortable': True},
            {'name': 'fark', 'label': 'Fark', 'field': 'fark', 'align': 'right', 'sortable': True},
            {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center', 'sortable': True},
            {'name': 'notlar', 'label': 'Not', 'field': 'notlar', 'align': 'left'},
        ]
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'mutabakat_tarih', 'descending': True},
        ).classes('w-full')
        table.props('flat bordered dense')
        table.add_slot('body-cell-mutabakat_tarih', TARIH_SLOT)
        table.add_slot('body-cell-sistem_bakiye', PARA_SLOT)
        table.add_slot('body-cell-firma_bakiye', PARA_SLOT)
        table.add_slot('body-cell-fark', PARA_SLOT)
        table.add_slot('body-cell-durum', r'''
            <q-td :props="props">
                <q-chip dense :color="props.value === 'TAM' ? 'positive' : 'negative'" text-color="white">
                    {{ props.value }}
                </q-chip>
            </q-td>
        ''')
