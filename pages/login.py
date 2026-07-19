"""Giris sayfasi — Kolay Muhasebe (kurumsal/modern)."""
from nicegui import ui, app

from services.auth_service import authenticate


@ui.page('/login')
def login_page():
    if app.storage.user.get('auth_user') and app.storage.user.get('tenant_schema'):
        ui.navigate.to('/')
        return

    ui.query('body').style(
        'background:linear-gradient(135deg,#faf5ff 0%,#eef2ff 55%,#eff6ff 100%);')

    with ui.column().classes('w-full items-center justify-center').style('min-height:100vh; gap:14px'):
        with ui.card().classes('q-pa-none').style(
                'width:410px;max-width:92vw;border-radius:22px;overflow:hidden;'
                'box-shadow:0 24px 70px rgba(99,102,241,.20);border:1px solid #ede9fe'):

            # --- Marka basligi ---
            with ui.column().classes('w-full items-center').style('padding:30px 26px 20px;gap:12px'):
                with ui.row().classes('items-center no-wrap').style('gap:12px'):
                    ui.icon('ads_click').style(
                        'font-size:30px;color:#7c3aed;background:#f5f3ff;border-radius:14px;'
                        'padding:8px;box-shadow:0 4px 14px rgba(124,58,237,.18)')
                    with ui.row().classes('items-baseline no-wrap').style('gap:4px'):
                        ui.label('Kolay').style('font-size:27px;font-weight:800;color:#1e1b4b;letter-spacing:-.6px')
                        ui.label('Muhasebe').style('font-size:27px;font-weight:800;color:#7c3aed;letter-spacing:-.6px')
                ui.label('Cari • Stok • Kasa • Çek — hepsi tek panelde').style(
                    'font-size:12px;color:#6b7280')

            # --- Form ---
            with ui.column().classes('w-full').style('padding:6px 28px 26px;gap:14px'):
                ui.label('Sisteme Giriş').style('font-size:14px;font-weight:700;color:#374151')

                _saved = app.storage.user.get('login_remember') or {}
                inp_user = ui.input('Kullanıcı Adı', value=_saved.get('u', '')).props(
                    'outlined dense').classes('w-full')
                inp_pass = ui.input('Şifre', value=_saved.get('p', ''),
                                    password=True, password_toggle_button=True).props(
                    'outlined dense').classes('w-full')
                chk_remember = ui.checkbox('Beni hatırla', value=bool(_saved.get('u'))).props(
                    'dense color=deep-purple').classes('text-grey-7')

                def _login():
                    try:
                        username = (inp_user.value or '').strip()
                        password = inp_pass.value or ''
                        if not username or not password:
                            ui.notify('Kullanıcı adı ve şifre zorunlu', type='negative')
                            return
                        user = authenticate(username, password)
                        if not user:
                            ui.notify('Kullanıcı adı veya şifre hatalı', type='negative')
                            return
                        # Beni hatirla: sifreli oturum cerezinde sakla / temizle
                        app.storage.user['login_remember'] = (
                            {'u': username, 'p': password} if chk_remember.value else {})
                        app.storage.user['auth_user'] = user
                        app.storage.user['tenant_schema'] = user['tenant_schema']
                        app.storage.user['tenant_name'] = user['tenant_name']
                        ui.notify('Giriş başarılı', type='positive')
                        ui.navigate.to('/')
                    except Exception as e:
                        ui.notify(f'Giriş hatası: {e}', type='negative')

                inp_pass.on('keydown.enter', lambda _: _login())

                ui.button('Giriş Yap', icon='login', on_click=_login, color=None).classes('w-full').style(
                    'background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff;font-weight:700;'
                    'height:44px;border-radius:12px;box-shadow:0 6px 18px rgba(124,58,237,.30)')

        ui.label('© 2026 Kolay Muhasebe · Güvenli giriş').style('font-size:11px;color:#9ca3af')
