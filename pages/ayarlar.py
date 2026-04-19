"""ALSE Plastik Hammadde - Ayarlar Sayfasi"""
import os
from nicegui import ui

from layout import create_layout, notify_ok, notify_err, confirm_dialog
from services.settings_service import get_company_settings, update_company_settings
from services.auth_service import list_users, add_user, update_user, set_user_password, delete_user
from services.audit_service import log_action
from services.backup_service import create_backup, list_backups


@ui.page('/ayarlar')
def ayarlar_page():
    if not create_layout(active_path='/ayarlar', page_title='Ayarlar'):
        return
    settings = get_company_settings()

    with ui.column().classes('w-full q-pa-sm gap-2'):
        with ui.card().classes('w-full q-pa-md'):
            ui.label('Firma Bilgileri (PDF Ust/Alt Bilgi)').classes('text-subtitle1 text-weight-bold q-mb-sm')
            inp_firma_adi = ui.input('Firma Adi', value=settings.get('firma_adi', '')).classes('w-full').props('outlined dense')
            inp_vkn = ui.input('VKN / TCKN', value=settings.get('vkn_tckn', '')).classes('w-full').props('outlined dense')
            inp_vergi = ui.input('Vergi Dairesi', value=settings.get('vergi_dairesi', '')).classes('w-full').props('outlined dense')
            inp_adres = ui.input('Adres', value=settings.get('adres', '')).classes('w-full').props('outlined dense')
            inp_tel = ui.input('Telefon', value=settings.get('telefon', '')).classes('w-full').props('outlined dense')
            inp_mail = ui.input('Mail', value=settings.get('email', '')).classes('w-full').props('outlined dense')
            inp_nace = ui.input('NACE', value=settings.get('nace', '')).classes('w-full').props('outlined dense')
            inp_is_alani = ui.input('Is Alani', value=settings.get('is_alani', '')).classes('w-full').props('outlined dense')
            inp_logo = ui.input('Logo Dosya Yolu', value=settings.get('logo_path', '')).classes('w-full').props('outlined dense')

            ui.separator().classes('q-my-sm')
            ui.label('Personel Ücret Periyodu').classes('text-subtitle2 text-weight-medium')
            inp_periyot = ui.radio(
                options={'AYLIK': 'Aylık (ay bazında maaş)', 'HAFTALIK': 'Haftalık (hafta bazında maaş)'},
                value=settings.get('ucret_periyodu', 'AYLIK') or 'AYLIK',
            ).props('inline')

            ui.separator().classes('q-my-sm')
            ui.label('Üretim Takibi (DESİ / Haftalık Bilanço)').classes('text-subtitle2 text-weight-medium')
            inp_uretim = ui.checkbox(
                'Üretim takibi aktif (DESİ hesaplama, haftalık bilanço, hammadde m³ takibi)',
                value=bool(settings.get('uretim_takibi', 0)),
            )

            with ui.row().classes('w-full justify-end q-mt-sm'):
                def _save_company():
                    try:
                        old_data = get_company_settings()
                        new_data = {
                            'firma_adi': inp_firma_adi.value or '',
                            'vkn_tckn': inp_vkn.value or '',
                            'vergi_dairesi': inp_vergi.value or '',
                            'adres': inp_adres.value or '',
                            'telefon': inp_tel.value or '',
                            'email': inp_mail.value or '',
                            'nace': inp_nace.value or '',
                            'is_alani': inp_is_alani.value or '',
                            'logo_path': inp_logo.value or '',
                            'ucret_periyodu': inp_periyot.value or 'AYLIK',
                            'uretim_takibi': inp_uretim.value,
                        }
                        update_company_settings(new_data)
                        log_action('UPDATE', 'settings_company', '1', old_data=old_data, new_data=new_data, detail='Firma ayarlari guncellendi')
                        notify_ok('Ayarlar kaydedildi')
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                ui.button('Kaydet', icon='save', color='primary', on_click=_save_company)

        with ui.card().classes('w-full q-pa-md'):
            ui.label('Kullanici Yonetimi').classes('text-subtitle1 text-weight-bold q-mb-sm')
            users = list_users()

            columns = [
                {'name': 'username', 'label': 'Kullanici', 'field': 'username', 'align': 'left', 'sortable': True},
                {'name': 'full_name', 'label': 'Ad Soyad', 'field': 'full_name', 'align': 'left', 'sortable': True},
                {'name': 'role', 'label': 'Rol', 'field': 'role', 'align': 'center', 'sortable': True},
                {'name': 'is_active', 'label': 'Durum', 'field': 'is_active', 'align': 'center', 'sortable': True},
                {'name': 'actions', 'label': 'Islemler', 'field': 'actions', 'align': 'center'},
            ]
            table = ui.table(
                columns=columns,
                rows=users,
                row_key='id',
                pagination={'rowsPerPage': 50, 'sortBy': 'username', 'descending': False},
            ).classes('w-full')
            table.props('flat bordered dense')
            table.add_slot('body-cell-is_active', r'''
                <q-td :props="props">
                    <q-chip dense :color="props.value ? 'positive' : 'negative'" text-color="white">
                        {{ props.value ? 'Aktif' : 'Pasif' }}
                    </q-chip>
                </q-td>
            ''')
            table.add_slot('body-cell-actions', r'''
                <q-td :props="props">
                    <q-btn flat round dense icon="edit" color="primary" size="sm"
                        @click.stop="$parent.$emit('edit_user', props.row)" />
                    <q-btn flat round dense icon="key" color="orange" size="sm"
                        @click.stop="$parent.$emit('password_user', props.row)" />
                    <q-btn flat round dense icon="delete" color="negative" size="sm"
                        @click.stop="$parent.$emit('delete_user', props.row)" />
                </q-td>
            ''')

            def _refresh_users():
                table.rows = list_users()
                table.update()

            def _open_add_user():
                with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:380px'):
                    ui.label('Yeni Kullanici').classes('text-h6')
                    inp_u = ui.input('Kullanici Adi').props('outlined dense').classes('w-full')
                    inp_n = ui.input('Ad Soyad').props('outlined dense').classes('w-full')
                    inp_p = ui.input('Sifre', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
                    inp_r = ui.select({'admin': 'Admin', 'user': 'User'}, value='user', label='Rol').props('outlined dense').classes('w-full')
                    inp_a = ui.switch('Aktif', value=True)
                    with ui.row().classes('w-full justify-end'):
                        ui.button('Iptal', on_click=dlg.close).props('flat')

                        def _save():
                            try:
                                if not inp_u.value or not inp_p.value:
                                    notify_err('Kullanici adi ve sifre zorunlu')
                                    return
                                if len(inp_p.value) < 6:
                                    notify_err('Sifre en az 6 karakter olmali')
                                    return
                                if not any(c.isdigit() for c in inp_p.value):
                                    notify_err('Sifre en az 1 rakam icermeli')
                                    return
                                new_id = add_user({
                                    'username': inp_u.value,
                                    'full_name': inp_n.value or '',
                                    'password': inp_p.value,
                                    'role': inp_r.value or 'user',
                                    'is_active': bool(inp_a.value),
                                })
                                log_action('CREATE', 'users', new_id, detail=f'Kullanici olusturuldu: {inp_u.value}')
                                notify_ok('Kullanici eklendi')
                                dlg.close()
                                _refresh_users()
                            except Exception as e:
                                notify_err(f'Hata: {e}')

                        ui.button('Kaydet', color='primary', on_click=_save)
                dlg.open()

            def _open_edit_user(row):
                with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:380px'):
                    ui.label('Kullanici Duzenle').classes('text-h6')
                    ui.input('Kullanici Adi', value=row.get('username', '')).props('outlined dense readonly').classes('w-full')
                    inp_n = ui.input('Ad Soyad', value=row.get('full_name', '')).props('outlined dense').classes('w-full')
                    inp_r = ui.select({'admin': 'Admin', 'user': 'User'}, value=row.get('role', 'user'), label='Rol').props('outlined dense').classes('w-full')
                    inp_a = ui.switch('Aktif', value=bool(row.get('is_active', 1)))
                    with ui.row().classes('w-full justify-end'):
                        ui.button('Iptal', on_click=dlg.close).props('flat')

                        def _save():
                            try:
                                update_user(row['id'], {
                                    'full_name': inp_n.value or '',
                                    'role': inp_r.value or 'user',
                                    'is_active': bool(inp_a.value),
                                })
                                log_action('UPDATE', 'users', row['id'], detail=f'Kullanici guncellendi: {row.get("username", "")}')
                                notify_ok('Kullanici guncellendi')
                                dlg.close()
                                _refresh_users()
                            except Exception as e:
                                notify_err(f'Hata: {e}')

                        ui.button('Kaydet', color='primary', on_click=_save)
                dlg.open()

            def _open_password_user(row):
                with ui.dialog() as dlg, ui.card().classes('q-pa-md').style('min-width:360px'):
                    ui.label('Sifre Yenile').classes('text-h6')
                    ui.label(row.get('username', '')).classes('text-caption text-grey-7')
                    inp_p = ui.input('Yeni Sifre', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
                    with ui.row().classes('w-full justify-end'):
                        ui.button('Iptal', on_click=dlg.close).props('flat')

                        def _save():
                            try:
                                if not inp_p.value:
                                    notify_err('Sifre bos olamaz')
                                    return
                                if len(inp_p.value) < 6:
                                    notify_err('Sifre en az 6 karakter olmali')
                                    return
                                if not any(c.isdigit() for c in inp_p.value):
                                    notify_err('Sifre en az 1 rakam icermeli')
                                    return
                                set_user_password(row['id'], inp_p.value)
                                log_action('UPDATE_PASSWORD', 'users', row['id'], detail=f'Sifre yenilendi: {row.get("username", "")}')
                                notify_ok('Sifre guncellendi')
                                dlg.close()
                            except Exception as e:
                                notify_err(f'Hata: {e}')

                        ui.button('Kaydet', color='primary', on_click=_save)
                dlg.open()

            def _delete_user(row):
                def _confirmed():
                    try:
                        delete_user(row['id'])
                        log_action('DELETE', 'users', row['id'], detail=f'Kullanici silindi: {row.get("username", "")}')
                        notify_ok('Kullanici silindi')
                        _refresh_users()
                    except Exception as e:
                        notify_err(f'Hata: {e}')

                confirm_dialog(f"{row.get('username', '')} kullanicisini silmek istediginize emin misiniz?", _confirmed)

            table.on('edit_user', lambda e: _open_edit_user(e.args))
            table.on('password_user', lambda e: _open_password_user(e.args))
            table.on('delete_user', lambda e: _delete_user(e.args))

            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('Yeni Kullanici', icon='person_add', color='primary', on_click=_open_add_user)

        # --- Yedekleme Bolumu ---
        with ui.card().classes('w-full q-pa-md'):
            with ui.row().classes('items-center q-mb-sm'):
                ui.icon('storage').classes('text-blue-7').style('font-size: 1.8rem')
                ui.label('Veritabani Yedekleme').classes('text-subtitle1 text-weight-bold q-ml-sm')

            backup_rows = list_backups()
            backup_cols = [
                {'name': 'filename', 'label': 'Dosya', 'field': 'filename', 'align': 'left', 'sortable': True},
                {'name': 'size_mb', 'label': 'Boyut (MB)', 'field': 'size_mb', 'align': 'right', 'sortable': True},
                {'name': 'created', 'label': 'Tarih', 'field': 'created', 'align': 'center', 'sortable': True},
            ]
            backup_table = ui.table(
                columns=backup_cols,
                rows=backup_rows,
                row_key='filename',
                pagination={'rowsPerPage': 10, 'sortBy': 'created', 'descending': True},
            ).classes('w-full')
            backup_table.props('flat bordered dense')

            def _refresh_backups():
                backup_table.rows = list_backups()
                backup_table.update()

            def _take_backup():
                try:
                    gz_path = create_backup()
                    notify_ok(f'Yedek alindi: {os.path.basename(gz_path)}')
                    _refresh_backups()
                except Exception as e:
                    notify_err(f'Yedekleme hatasi: {e}')

            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('Yedek Al', icon='backup', color='primary', on_click=_take_backup)
