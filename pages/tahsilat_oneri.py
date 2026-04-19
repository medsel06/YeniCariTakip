"""Otomatik tahsilat onerisi sayfasi."""
from nicegui import ui

from layout import create_layout, PARA_SLOT, TARIH_SLOT
from services.oneri_service import get_tahsilat_onerileri


@ui.page('/tahsilat-oneri')
def tahsilat_oneri_page():
    if not create_layout(active_path='/tahsilat-oneri', page_title='Tahsilat Onerisi'):
        return
    rows = get_tahsilat_onerileri()
    toplam_oneri = sum(float(r.get('onerilen_tahsilat', 0) or 0) for r in rows)

    def _filter(items, q):
        q = (q or '').strip().lower()
        if not q:
            return items
        return [r for r in items if q in str(r.get('firma_ad', '')).lower() or q in str(r.get('firma_kod', '')).lower()]

    with ui.column().classes('w-full q-pa-sm'):
        with ui.grid(columns='repeat(2, 1fr)').classes('w-full gap-2 q-mb-xs'):
            with ui.card().classes('q-pa-sm'):
                ui.label('Oneri Sayisi').classes('text-caption text-grey-7')
                ui.label(str(len(rows))).classes('text-h6 text-weight-bold')
            with ui.card().classes('q-pa-sm'):
                ui.label('Toplam Onerilen Tahsilat').classes('text-caption text-grey-7')
                ui.label(f"{toplam_oneri:,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')).classes('text-h6 text-weight-bold text-primary')

        with ui.row().classes('w-full items-center q-mb-xs'):
            ui.input(
                placeholder='Ara (firma kodu/adi)...',
                on_change=lambda e: (setattr(tbl, 'rows', _filter(rows, e.value)), tbl.update()),
            ).props('outlined dense clearable').classes('w-80')
            ui.space()
            ui.label(f'Kayit: {len(rows)}').classes('text-caption text-grey-7')

        cols = [
            {'name': 'firma_kod', 'label': 'Kod', 'field': 'firma_kod', 'align': 'left', 'sortable': True},
            {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
            {'name': 'onerilen_tahsilat', 'label': 'Önerilen Tahsilat', 'field': 'onerilen_tahsilat', 'align': 'right', 'sortable': True},
            {'name': 'risk_yuzdesi', 'label': 'Risk %', 'field': 'risk_yuzdesi', 'align': 'center', 'sortable': True},
            {'name': 'en_eski_satis', 'label': 'En Eski Satış', 'field': 'en_eski_satis', 'align': 'center', 'sortable': True},
            {'name': 'gecikme_gun', 'label': 'Gecikme (Gün)', 'field': 'gecikme_gun', 'align': 'right', 'sortable': True},
            {'name': 'oncelik_skoru', 'label': 'Öncelik', 'field': 'oncelik_skoru', 'align': 'right', 'sortable': True},
        ]
        tbl = ui.table(
            columns=cols,
            rows=rows,
            row_key='firma_kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'oncelik_skoru', 'descending': True},
        ).classes('w-full')
        tbl.props('flat bordered dense')
        tbl.add_slot('body-cell-onerilen_tahsilat', PARA_SLOT)
        tbl.add_slot('body-cell-en_eski_satis', TARIH_SLOT)
        tbl.add_slot('body-cell-risk_yuzdesi', r'''
            <q-td :props="props">
                <q-badge dense text-color="white"
                    :color="props.value > 100 ? 'red-7' : props.value >= 80 ? 'orange-7' : props.value >= 50 ? 'amber-8' : props.value > 0 ? 'green-7' : 'grey-5'">
                    {{ props.value > 0 ? props.value.toFixed(1) + '%' : '-' }}
                </q-badge>
            </q-td>
        ''')
