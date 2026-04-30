"""Urun karlilik ozeti."""
from nicegui import ui

from layout import create_layout, PARA_SLOT, MIKTAR_SLOT
from services.oneri_service import get_urun_karlilik_ozeti


@ui.page('/karlilik')
def karlilik_page():
    if not create_layout(active_path='/karlilik', page_title='Urun Karlilik'):
        return
    rows = get_urun_karlilik_ozeti()
    toplam_kar = sum(float(r.get('kar', 0) or 0) for r in rows)
    ort_marj = (sum(float(r.get('marj', 0) or 0) for r in rows) / len(rows)) if rows else 0

    def _filter(items, q):
        q = (q or '').strip().lower()
        if not q:
            return items
        return [r for r in items if q in str(r.get('urun_ad', '')).lower() or q in str(r.get('urun_kod', '')).lower()]

    with ui.column().classes('w-full q-pa-sm'):
        with ui.grid(columns='repeat(3, 1fr)').classes('w-full gap-2 q-mb-xs'):
            with ui.card().classes('q-pa-sm'):
                ui.label('Urun Sayisi').classes('text-caption text-grey-7')
                ui.label(str(len(rows))).classes('text-h6 text-weight-bold')
            with ui.card().classes('q-pa-sm'):
                ui.label('Toplam Kar').classes('text-caption text-grey-7')
                ui.label(f"{toplam_kar:,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')).classes(
                    'text-h6 text-weight-bold ' + ('text-positive' if toplam_kar >= 0 else 'text-negative')
                )
            with ui.card().classes('q-pa-sm'):
                ui.label('Ortalama Marj').classes('text-caption text-grey-7')
                ui.label(f"{ort_marj:.2f} %".replace('.', ',')).classes(
                    'text-h6 text-weight-bold ' + ('text-positive' if ort_marj >= 0 else 'text-negative')
                )

        with ui.row().classes('w-full items-center q-mb-xs'):
            ui.input(
                placeholder='Ara (urun kodu/adi)...',
                on_change=lambda e: (setattr(tbl, 'rows', _filter(rows, e.value)), tbl.update()),
            ).props('outlined dense clearable').classes('w-80')
            ui.space()

        cols = [
            {'name': 'urun_ad', 'label': 'Urun', 'field': 'urun_ad', 'align': 'left', 'sortable': True},
            {'name': 'alis_miktar', 'label': 'Alis Miktar', 'field': 'alis_miktar', 'align': 'right', 'sortable': True},
            {'name': 'satis_miktar', 'label': 'Satis Miktar', 'field': 'satis_miktar', 'align': 'right', 'sortable': True},
            {'name': 'alis_tutar', 'label': 'Alis Tutar', 'field': 'alis_tutar', 'align': 'right', 'sortable': True},
            {'name': 'satis_tutar', 'label': 'Satis Tutar', 'field': 'satis_tutar', 'align': 'right', 'sortable': True},
            {'name': 'kar', 'label': 'Kar', 'field': 'kar', 'align': 'right', 'sortable': True},
            {'name': 'marj', 'label': 'Marj %', 'field': 'marj', 'align': 'right', 'sortable': True},
        ]
        tbl = ui.table(
            columns=cols,
            rows=rows,
            row_key='urun_kod',
            pagination={'rowsPerPage': 50, 'sortBy': 'kar', 'descending': True},
        ).classes('w-full')
        tbl.props('flat bordered dense')
        tbl.add_slot('body-cell-alis_miktar', MIKTAR_SLOT)
        tbl.add_slot('body-cell-satis_miktar', MIKTAR_SLOT)
        tbl.add_slot('body-cell-alis_tutar', PARA_SLOT)
        tbl.add_slot('body-cell-satis_tutar', PARA_SLOT)
        tbl.add_slot('body-cell-kar', PARA_SLOT)
        tbl.add_slot('body-cell-marj', r'''
            <q-td :props="props">
                <span :class="props.value >= 0 ? 'text-positive text-weight-medium' : 'text-negative text-weight-medium'">
                    {{ props.value != null ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' %' : '' }}
                </span>
            </q-td>
        ''')
