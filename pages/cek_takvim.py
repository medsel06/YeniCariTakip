"""Cek vade takvimi ve alarm kartlari."""
from datetime import date

from nicegui import ui

from layout import create_layout, fmt_para, TARIH_SLOT, PARA_SLOT, normalize_search
from services.cek_service import list_cekler, get_vade_uyarilari


@ui.page('/cek-takvim')
def cek_takvim_page():
    if not create_layout(active_path='/cek-takvim', page_title='Cek Takvimi'):
        return
    all_rows = list_cekler()
    alerts = get_vade_uyarilari()

    def _filter(rows, q):
        q = normalize_search(q)
        if not q:
            return rows
        return [
            r for r in rows
            if q in normalize_search(r.get('cek_no', ''))
            or q in normalize_search(r.get('firma_ad', ''))
            or q in normalize_search(r.get('durum', ''))
            or q in normalize_search(r.get('vade_tarih', ''))
        ]

    with ui.column().classes('w-full q-pa-sm gap-2'):
        with ui.grid(columns='repeat(4, 1fr)').classes('w-full gap-2'):
            cards = [
                ('Vadesi Gecmis', alerts['gecmis'], 'negative'),
                ('Bugun Vadeli', alerts['bugun'], 'negative'),
                ('3 Gun Icinde', alerts['uc_gun'], 'warning'),
                ('7 Gun Icinde', alerts['yedi_gun'], 'amber-8'),
            ]
            for title, items, color in cards:
                with ui.card().classes('q-pa-sm'):
                    ui.label(title).classes(f'text-caption text-{color}')
                    ui.label(str(len(items))).classes('text-h6 text-weight-bold')

        with ui.card().classes('w-full q-pa-sm'):
            with ui.row().classes('w-full items-center q-mb-xs'):
                ui.input(
                    placeholder='Ara (cek no, firma, durum, vade)...',
                    on_change=lambda e: (setattr(tbl, 'rows', _filter(all_rows, e.value)), tbl.update()),
                ).props('outlined dense clearable').classes('w-96')
                ui.space()
                ui.label(f"Bugun: {date.today().strftime('%d.%m.%Y')}").classes('text-caption text-grey-7')

            columns = [
                {'name': 'cek_no', 'label': 'Cek No', 'field': 'cek_no', 'align': 'left', 'sortable': True},
                {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left', 'sortable': True},
                {'name': 'vade_tarih', 'label': 'Vade', 'field': 'vade_tarih', 'align': 'center', 'sortable': True},
                {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right', 'sortable': True},
                {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center', 'sortable': True},
            ]
            tbl = ui.table(
                columns=columns,
                rows=all_rows,
                row_key='id',
                pagination={'rowsPerPage': 50, 'sortBy': 'vade_tarih', 'descending': False},
            ).classes('w-full')
            tbl.props('flat bordered dense')
            tbl.add_slot('body-cell-vade_tarih', TARIH_SLOT)
            tbl.add_slot('body-cell-tutar', PARA_SLOT)
            today_iso = date.today().isoformat()
            tbl.add_slot('body-cell-durum', f'''
                <q-td :props="props">
                    <q-chip dense text-color="white" size="sm"
                        :color="props.row.vade_tarih < '{today_iso}' ? 'negative' :
                                props.row.vade_tarih === '{today_iso}' ? 'orange' : 'blue'">
                        {{{{ props.value }}}}
                    </q-chip>
                </q-td>
            ''')
