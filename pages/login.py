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
            with ui.column().classes('items-center w-full q-mb-md gap-2'):
                # Logo: emerald ikon rozeti + iki tonlu logotype
                with ui.row().classes('items-center justify-center no-wrap gap-2'):
                    ui.icon('account_balance_wallet').style(
                        'font-size:30px;color:#fff;background:linear-gradient(135deg,#0f766e,#059669);'
                        'padding:9px;border-radius:12px;box-shadow:0 4px 12px rgba(5,150,105,.35)')
                    with ui.row().classes('items-baseline no-wrap').style('gap:3px'):
                        ui.label('Kolay').style('font-size:25px;font-weight:800;color:#0f172a;letter-spacing:-.5px')
                        ui.label('Muhasebe').style('font-size:25px;font-weight:800;color:#0f766e;letter-spacing:-.5px')
                ui.label('Sistem Girişi').classes('text-subtitle2 text-grey-6 text-center')

            inp_user = ui.input('Kullanici Adi').props('outlined dense').classes('w-full')
            inp_pass = ui.input('Sifre', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')

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
