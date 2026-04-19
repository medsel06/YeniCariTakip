"""Sistem loglari sayfasi."""
import json
from nicegui import ui

from layout import create_layout, normalize_search, donem_secici
from services.audit_service import list_logs, list_logs_filtered


@ui.page('/loglar')
def loglar_page():
    if not create_layout(active_path='/loglar', page_title='Loglar'):
        return

    # State for filters
    filter_state = {'action': None, 'entity_type': None, 'date_from': None, 'date_to': None}

    def _load_data():
        return list_logs_filtered(
            limit=1000,
            action=filter_state['action'] or None,
            entity_type=filter_state['entity_type'] or None,
            date_from=filter_state['date_from'] or None,
            date_to=filter_state['date_to'] or None,
        )

    rows = _load_data()

    def _filter(items, query):
        q = normalize_search(query)
        if not q:
            return items
        return [
            r for r in items
            if q in normalize_search(r.get('actor_username', ''))
            or q in normalize_search(r.get('action', ''))
            or q in normalize_search(r.get('entity_type', ''))
            or q in normalize_search(r.get('detail', ''))
        ]

    def _reload_table():
        nonlocal rows
        rows = _load_data()
        table.rows = rows
        search_input_value = search_input.value if search_input.value else ''
        if search_input_value:
            table.rows = _filter(rows, search_input_value)
        table.update()

    def _on_action_change(e):
        filter_state['action'] = e.value if e.value else None
        _reload_table()

    def _on_entity_change(e):
        filter_state['entity_type'] = e.value if e.value else None
        _reload_table()

    def _on_date_from_change(e):
        filter_state['date_from'] = e.value if e.value else None
        _reload_table()

    def _on_date_to_change(e):
        filter_state['date_to'] = e.value if e.value else None
        _reload_table()

    def _show_detail(row):
        """Log detay dialogu: old_data ve new_data goster."""
        with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:500px; max-width:700px'):
            ui.label('Log Detayi').classes('text-h6 q-mb-sm')
            with ui.column().classes('w-full gap-1'):
                ui.label(f"Tarih: {row.get('created_at', '')}").classes('text-caption')
                ui.label(f"Kim: {row.get('actor_username', '')}").classes('text-caption')
                ui.label(f"Islem: {row.get('action', '')}").classes('text-caption')
                ui.label(f"Varlik: {row.get('entity_type', '')} / {row.get('entity_id', '')}").classes('text-caption')
                ui.label(f"Detay: {row.get('detail', '')}").classes('text-caption')

                ui.separator().classes('q-my-sm')

                old_raw = row.get('old_data', '')
                new_raw = row.get('new_data', '')

                if old_raw:
                    ui.label('Eski Veri:').classes('text-subtitle2 text-weight-bold')
                    try:
                        old_formatted = json.dumps(json.loads(old_raw), indent=2, ensure_ascii=False)
                    except Exception:
                        old_formatted = str(old_raw)
                    ui.html(f'<pre style="background:#f5f5f5;padding:8px;border-radius:4px;overflow-x:auto;font-size:12px;max-height:250px;overflow-y:auto">{old_formatted}</pre>')

                if new_raw:
                    ui.label('Yeni Veri:').classes('text-subtitle2 text-weight-bold')
                    try:
                        new_formatted = json.dumps(json.loads(new_raw), indent=2, ensure_ascii=False)
                    except Exception:
                        new_formatted = str(new_raw)
                    ui.html(f'<pre style="background:#e8f5e9;padding:8px;border-radius:4px;overflow-x:auto;font-size:12px;max-height:250px;overflow-y:auto">{new_formatted}</pre>')

                if not old_raw and not new_raw:
                    ui.label('Eski/yeni veri kaydedilmemis.').classes('text-grey-6 text-italic')

            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('Kapat', on_click=dlg.close).props('flat color=grey')
        dlg.open()

    with ui.column().classes('w-full q-pa-sm'):
        # Filter controls
        with ui.row().classes('w-full items-end gap-2 q-mb-sm'):
            ui.select(
                options={'': 'Tumu', 'CREATE': 'CREATE', 'UPDATE': 'UPDATE', 'DELETE': 'DELETE'},
                value='',
                label='Islem',
                on_change=_on_action_change,
            ).props('outlined dense').classes('w-36')

            ui.select(
                options={
                    '': 'Tumu',
                    'firmalar': 'Firmalar',
                    'hareketler': 'Hareketler',
                    'kasa': 'Kasa',
                    'cekler': 'Cekler',
                    'gelir_gider': 'Gelir/Gider',
                    'personel': 'Personel',
                    'urunler': 'Urunler',
                },
                value='',
                label='Varlik Tipi',
                on_change=_on_entity_change,
            ).props('outlined dense').classes('w-40')

            with ui.input('Baslangic Tarih', on_change=_on_date_from_change).props('outlined dense').classes('w-40') as date_from_input:
                with date_from_input.add_slot('append'):
                    ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_from:
                    ui.date(on_change=lambda e: (date_from_input.set_value(e.value), menu_from.close()))

            with ui.input('Bitis Tarih', on_change=_on_date_to_change).props('outlined dense').classes('w-40') as date_to_input:
                with date_to_input.add_slot('append'):
                    ui.icon('event').classes('cursor-pointer')
                with ui.menu() as menu_to:
                    ui.date(on_change=lambda e: (date_to_input.set_value(e.value), menu_to.close()))

        # Search input
        with ui.row().classes('w-full items-center q-mb-xs'):
            search_input = ui.input(
                placeholder='Ara (kim, islem, varlik, detay)...',
                on_change=lambda e: (setattr(table, 'rows', _filter(rows, e.value)), table.update()),
            ).props('outlined dense clearable').classes('w-96')

        cols = [
            {'name': 'created_at', 'label': 'Tarih', 'field': 'created_at', 'align': 'center', 'sortable': True},
            {'name': 'actor_username', 'label': 'Kim', 'field': 'actor_username', 'align': 'left', 'sortable': True},
            {'name': 'action', 'label': 'Islem', 'field': 'action', 'align': 'left', 'sortable': True},
            {'name': 'entity_type', 'label': 'Varlik', 'field': 'entity_type', 'align': 'left', 'sortable': True},
            {'name': 'entity_id', 'label': 'Kayit No', 'field': 'entity_id', 'align': 'left', 'sortable': True},
            {'name': 'detail', 'label': 'Detay', 'field': 'detail', 'align': 'left', 'sortable': False},
        ]
        table = ui.table(
            columns=cols,
            rows=rows,
            row_key='id',
            pagination={'rowsPerPage': 50, 'sortBy': 'created_at', 'descending': True},
        ).classes('w-full')
        table.props('flat bordered dense')

        table.add_slot('body-cell-created_at', r'''
            <q-td :props="props">
                {{ props.value || '' }}
            </q-td>
        ''')

        table.on('row-click', lambda e: _show_detail(e.args[1]))
