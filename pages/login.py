"""Giris sayfasi."""
from nicegui import ui, app

from services.auth_service import authenticate


@ui.page('/login')
def login_page():
    if app.storage.user.get('auth_user') and app.storage.user.get('tenant_schema'):
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full items-center justify-center').style('min-height: 100vh;'):
        with ui.card().classes('q-pa-lg').style('width: 380px; max-width: 90vw'):
            ui.label('Cari Takip').classes('text-h5 text-weight-bold text-center w-full')
            ui.label('Sistem Girisi').classes('text-subtitle2 text-grey-7 text-center w-full q-mb-md')

            inp_user = ui.input('Kullanici Adi').props('outlined dense').classes('w-full')
            inp_pass = ui.input('Sifre', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')
            ui.label('Ilk kurulum: admin / admin123').classes('text-caption text-grey-7 q-mt-xs')

            def _login():
                try:
                    username = (inp_user.value or '').strip()
                    password = inp_pass.value or ''
                    if not username or not password:
                        ui.notify('Kullanici adi ve sifre zorunlu', type='negative')
                        return
                    user = authenticate(username, password)
                    if not user:
                        ui.notify('Kullanici adi veya sifre hatali', type='negative')
                        return
                    app.storage.user['auth_user'] = user
                    app.storage.user['tenant_schema'] = user['tenant_schema']
                    app.storage.user['tenant_name'] = user['tenant_name']
                    ui.notify(f'Giris basarili', type='positive')
                    ui.navigate.to('/')
                except Exception as e:
                    ui.notify(f'Giris hatasi: {e}', type='negative')

            ui.button('Giris Yap', icon='login', color='primary', on_click=_login).classes('w-full q-mt-sm')
