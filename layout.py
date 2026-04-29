"""
Cari Takip - Ortak Layout
Header, navigation drawer, format yardimcilari
"""
import unicodedata
from nicegui import ui, app
from db import set_tenant_schema


MENU_GROUPS = [
    ('Operasyon', 'business_center', [
        ('/', 'dashboard', 'Bilgi Ekranı'),
        ('/hareketler', 'swap_horiz', 'Stok Hareketler'),
        ('/cari', 'people', 'Cari Hesaplar'),
        ('/firma-master', 'apartment', 'Firmalar'),
        ('/stok', 'inventory_2', 'Stok'),
        ('/kasa', 'account_balance_wallet', 'Kasa'),
        ('/gelir-gider', 'payments', 'Gelir / Gider'),
        ('/personel', 'badge', 'Personel'),
        ('/cekler', 'receipt_long', 'Çek / Senet'),
        ('/uretim', 'precision_manufacturing', 'Üretim'),
    ]),
    ('Finans Analiz', 'insights', [
        ('/cek-takvim', 'event_note', 'Çek Takvimi'),
        ('/mutabakat', 'fact_check', 'Mutabakat'),
        ('/tahsilat-oneri', 'tips_and_updates', 'Tahsilat Öneri'),
        ('/karlilik', 'query_stats', 'Karlılık'),
        ('/raporlar', 'assessment', 'Raporlar'),
    ]),
    ('Yönetim', 'admin_panel_settings', [
        ('/ayarlar', 'settings', 'Ayarlar'),
        ('/loglar', 'history', 'Loglar'),
    ]),
]

BRAND_CSS = '''
.alse-root { font-family: "Bahnschrift", "Segoe UI Variable", sans-serif; }
.alse-header {
  background: linear-gradient(120deg, #0f2232 0%, #1c4461 48%, #2a6b8f 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}
/* ---- MOBILE RESPONSIVE ---- */
@media (max-width: 768px) {
  .alse-header { min-height: 52px !important; }
  .alse-header-brand { display: none !important; }
  .alse-header .text-subtitle1 { font-size: 13px !important; }
  .q-drawer { width: 260px !important; }
  .q-page-container { padding-left: 0 !important; }
  .q-pa-sm { padding: 6px !important; }
  .q-pa-md { padding: 8px !important; }
  /* Kart gridi tek sutun */
  .dash-cards { grid-template-columns: 1fr 1fr !important; gap: 6px !important; }
  /* Dialog full-width */
  .q-dialog .q-card { width: 96vw !important; max-width: 96vw !important; margin: 8px !important; max-height: 90vh !important; overflow-y: auto !important; }
  /* Tablo font kuculme */
  .q-table { font-size: 11px !important; }
  .q-table thead tr th { padding: 4px 6px !important; font-size: 10px !important; }
  .q-table tbody td { padding: 3px 6px !important; }
  /* Kucuk butonlar */
  .q-btn--dense { min-height: 28px !important; padding: 2px 8px !important; font-size: 11px !important; }
  /* Input kucultme */
  .q-field--dense .q-field__control { min-height: 32px !important; }
  /* Chip kucultme */
  .q-chip { font-size: 11px !important; padding: 2px 6px !important; }
  /* Row wrap */
  .q-row-mobile-wrap { flex-wrap: wrap !important; }
}
@media (max-width: 480px) {
  .dash-cards { grid-template-columns: 1fr !important; }
  .q-table { font-size: 10px !important; }
  .q-table thead tr th { font-size: 9px !important; padding: 3px 4px !important; }
  .q-table tbody td { padding: 2px 4px !important; }
  .q-dialog .q-card { width: 100vw !important; max-width: 100vw !important; margin: 0 !important; border-radius: 0 !important; }
}
/* ---- DIALOG / MODAL STYLING ---- */
.alse-dialog {
  border-radius: 16px !important;
  overflow: hidden;
}
.alse-dialog-header {
  background: linear-gradient(135deg, #1c4461 0%, #2a6b8f 100%);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.alse-dialog-header .q-icon { color: rgba(255,255,255,0.95); font-size: 26px; }
.alse-dialog-header .dialog-title { color: #fff; font-size: 17px; font-weight: 700; letter-spacing: 0.3px; }
.alse-dialog-body { padding: 20px; }
.alse-dialog-footer { padding: 12px 20px; display: flex; justify-content: flex-end; gap: 8px; border-top: 1px solid #e8edf2; }
/* Dialog acilis animasyonu */
.q-dialog__inner { transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important; }
.q-dialog .q-card {
  box-shadow: 0 12px 40px rgba(0,0,0,0.18), 0 4px 12px rgba(0,0,0,0.1) !important;
  border-radius: 14px !important;
  border: 1px solid rgba(0,0,0,0.06);
}
/* Input focus glow */
.q-field--outlined .q-field__control:focus-within {
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
  border-color: #1976D2 !important;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
/* Buton hover efekti */
.q-btn--unelevated { transition: all 0.2s ease; }
.q-btn--unelevated:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
/* Confirm dialog ozel */
.alse-confirm-danger { border-left: 4px solid #C10015; }
.alse-drawer-brand {
  height: 86px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #c8d8e8;
  margin: 0 0 6px 0;
}
.alse-drawer-brand-logo {
  width: 170px;
  height: 64px;
  object-fit: contain;
}
.alse-logo {
  width: 52px;
  height: 52px;
  object-fit: contain;
  display: block;
}
.alse-drawer {
  background:
    radial-gradient(circle at 8% 8%, rgba(255,255,255,0.35) 0, transparent 28%),
    linear-gradient(180deg, #eef4fb 0%, #dce6f0 100%) !important;
}
.alse-drawer .q-drawer__content,
.alse-drawer .scroll {
  background:
    radial-gradient(circle at 8% 8%, rgba(255,255,255,0.35) 0, transparent 28%),
    linear-gradient(180deg, #eef4fb 0%, #dce6f0 100%) !important;
}
.alse-drawer .q-drawer__content {
  overflow-y: auto !important;
  overflow-x: hidden !important;
}
.alse-nav-item {
  border-radius: 8px;
  transition: all .2s ease;
  padding: 8px 10px !important;
  margin: 1px 8px;
  min-height: 36px;
}
.alse-nav-item:hover {
  background: rgba(26, 92, 140, 0.08);
}
.alse-nav-item.bg-blue-2 {
  background: rgba(25, 118, 210, 0.12) !important;
  border-left: 3px solid #1976D2;
  padding-left: 7px !important;
}
.alse-group {
  background: transparent;
  border: none;
  border-radius: 0;
  margin: 0 !important;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
.alse-drawer .q-expansion-item {
  margin: 0 !important;
  padding: 0 !important;
}
.alse-drawer .q-expansion-item + .q-expansion-item {
  margin-top: 0 !important;
}
.alse-group .q-expansion-item__container {
  margin: 0 !important;
  padding: 0 !important;
}
.alse-group .q-expansion-item__container > .q-item {
  min-height: 42px;
  height: 42px;
  margin: 0 !important;
  padding-left: 16px;
  padding-right: 12px;
  border-bottom: 1px solid rgba(140, 164, 186, 0.15);
}
.alse-group .q-expansion-item__content {
  padding-top: 2px !important;
  padding-bottom: 6px !important;
}
.alse-group .q-item__section--avatar {
  min-width: 18px;
}
.alse-group .q-item__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Global table look */
.q-table {
  font-family: "Trebuchet MS", "Segoe UI Variable", sans-serif;
  font-size: 13px;
}
.q-table thead tr th {
  background: linear-gradient(180deg, #2b4f6d 0%, #243f57 100%);
  color: #f5fbff;
  font-weight: 700;
  letter-spacing: 0.2px;
  border-bottom: 1px solid #183046;
  padding-top: 6px !important;
  padding-bottom: 6px !important;
  line-height: 1.15;
}
.q-table tbody tr:nth-child(odd) {
  background: #f8fbff;
}
.q-table tbody tr:nth-child(even) {
  background: #edf4fb;
}
.q-table tbody tr {
  transition: transform .16s ease, box-shadow .16s ease, background-color .16s ease;
}
.q-table tbody td {
  padding-top: 5px !important;
  padding-bottom: 5px !important;
}
.q-table tbody tr:hover {
  background: #d8e9f8 !important;
  transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px #9cc2e3;
}

/* Global adaptive table container:
   - header sabit (sticky)
   - scroll tablonun icinde
   - tablo yuksekligi viewport'a gore dengeli */
.nicegui-table {
  width: 100%;
}
.q-table__middle {
  min-height: 220px;
  max-height: calc(clamp(320px, calc(100vh - 320px), 680px) + (var(--table-extra-rows, 0) * 42px));
  overflow: auto;
  overscroll-behavior: contain;
}
.q-table thead tr th {
  position: sticky;
  top: 0;
  z-index: 3;
}
.q-table__middle::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
.q-table__middle::-webkit-scrollbar-thumb {
  background: #9fb8cf;
  border-radius: 8px;
  border: 2px solid #e9f1f8;
}
.q-table__middle::-webkit-scrollbar-track {
  background: #e9f1f8;
  border-radius: 8px;
}
@media (max-width: 1200px) {
  .q-table__middle {
    min-height: 180px;
    max-height: calc(clamp(250px, calc(100vh - 255px), 500px) + (var(--table-extra-rows, 0) * 38px));
  }
  .alse-group {
    margin: 0 6px !important;
    width: calc(100% - 12px);
  }
  .alse-drawer .q-expansion-item + .q-expansion-item {
    margin-top: 0 !important;
    border-top: 1px solid rgba(140, 164, 186, 0.45);
  }
  .alse-group .q-expansion-item__container > .q-item {
    min-height: 30px;
    height: 30px;
    padding-left: 6px;
    padding-right: 6px;
  }
}
@media (max-width: 900px) {
  .q-table__middle {
    min-height: 180px;
    max-height: calc(clamp(240px, calc(100vh - 260px), 520px) + (var(--table-extra-rows, 0) * 34px));
  }
}
'''


def create_layout(active_path='/', page_title=''):
    if active_path != '/login':
        auth_user = app.storage.user.get('auth_user')
        tenant_schema = app.storage.user.get('tenant_schema')
        # Auth veya tenant yoksa login'e yonlendir
        if not auth_user or not tenant_schema:
            app.storage.user.clear()
            ui.navigate.to('/login')
            return None
        # Multi-tenant: mevcut kullanicinin tenant schema'sini set et
        set_tenant_schema(tenant_schema)

    ui.add_css(BRAND_CSS)
    ui.colors(primary='#37474F', secondary='#1976D2', positive='#21BA45',
              negative='#C10015', warning='#F2C037')
    # PWA + Mobile meta
    ui.add_head_html('''
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#1c4461">
        <link rel="manifest" href="/assets/manifest.json">
    ''', shared=True)
    ui.add_body_html('''
        <script>
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.register('/assets/sw.js').catch(()=>{});
        }
        </script>
    ''', shared=True)

    # Firma adini ayarlardan al (tenant bazli)
    _header_firma = 'CARİ TAKİP'
    try:
        from services.settings_service import get_company_settings
        _cs = get_company_settings()
        _header_firma = _cs.get('firma_adi', '') or 'CARİ TAKİP'
    except Exception:
        pass
    # Firma adini iki parcaya bol (ilk kelime kalin, gerisi ince)
    _firma_parts = _header_firma.strip().split(' ', 1)
    _firma_p1 = _firma_parts[0]
    _firma_p2 = _firma_parts[1] if len(_firma_parts) > 1 else ''

    with ui.header().classes('items-center alse-header alse-root').style('padding: 0; min-height: 68px;'):
        # Logo alani - sidebar genisliginde sabit, firma adina gore dinamik (mobilde gizli)
        with ui.element('div').classes('alse-header-brand').style(
            'width: 258px; min-width: 258px; height: 68px; display: flex; '
            'align-items: center; justify-content: center; '
            'border-right: 1px solid rgba(255,255,255,0.15); padding: 0 16px; box-sizing: border-box;'
        ):
            ui.html(
                f'<a href="/" style="text-decoration: none; display: flex; align-items: baseline; gap: 8px;">'
                f'<span style="font-size: 22px; font-weight: 800; color: #ffffff; '
                f'letter-spacing: 2px; font-family: Bahnschrift, Segoe UI, sans-serif;">{_firma_p1}</span>'
                f'<span style="font-size: 22px; font-weight: 300; color: rgba(255,255,255,0.8); '
                f'letter-spacing: 1px; font-family: Bahnschrift, Segoe UI, sans-serif;">{_firma_p2}</span>'
                f'</a>'
            )
        # Icerik alani - hamburger, baslik, kullanici bilgileri
        with ui.row().classes('items-center q-px-md').style('flex: 1; height: 68px;'):
            ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat color=white round')
            ui.label(page_title).classes('text-subtitle1 text-weight-medium text-white q-ml-sm')
            ui.space()

            # Vade uyari bildirimi (zil ikonu + dropdown)
            toplam_uyari = 0
            uyari_list = []
            try:
                from services.cek_service import get_vade_uyarilari
                uyarilar = get_vade_uyarilari()
                for label, key, renk in [('GEÇMİŞ', 'gecmis', '#C10015'), ('BUGÜN', 'bugun', '#E53935'), ('3 GÜN', 'uc_gun', '#FF8F00')]:
                    for item in uyarilar.get(key, []):
                        evrak = 'Senet' if item.get('evrak_tipi') == 'SENET' else 'Çek'
                        yon = 'Alınan' if item.get('cek_turu') == 'ALINAN' else 'Verilen'
                        uyari_list.append({'text': f"[{label}] {yon} {evrak} {item.get('cek_no','')} - {item.get('firma_ad','')} - {fmt_para(item.get('tutar',0))} TL", 'color': renk})
                toplam_uyari = len(uyari_list)
            except Exception:
                pass
            btn_bell = ui.button(icon='notifications' if toplam_uyari > 0 else 'notifications_none').props('flat color=white round dense')
            if toplam_uyari > 0:
                with btn_bell:
                    ui.badge(str(toplam_uyari), color='red').props('floating')
                with ui.menu().props('anchor="bottom right" self="top right"') as bell_menu:
                    with ui.column().classes('q-pa-sm').style('min-width: 320px; max-height: 400px; overflow-y: auto'):
                        ui.label('Vade Uyarıları').classes('text-subtitle2 text-weight-bold q-mb-xs')
                        if uyari_list:
                            for u in uyari_list:
                                with ui.row().classes('items-center no-wrap q-py-xs').style(f'border-left: 3px solid {u["color"]}; padding-left: 8px'):
                                    ui.label(u['text']).classes('text-caption')
                        else:
                            ui.label('Uyarı yok').classes('text-caption text-grey')
                btn_bell.on('click', bell_menu.open)

            auth_user = app.storage.user.get('auth_user', {})
            if auth_user:
                ui.label(auth_user.get('full_name') or auth_user.get('username', '')).classes('text-white text-caption q-mr-sm')
                ui.button(
                    icon='logout',
                    on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')),
                ).props('flat color=white round dense')

    drawer = ui.left_drawer(value=True, bordered=True).classes('alse-drawer alse-root').props('width=258 breakpoint=768')
    with drawer:
        ui.element('div').style('height: 6px')
        active_group_index = 0
        for i, (_, _, items) in enumerate(MENU_GROUPS):
            if any(path == active_path for path, _, _ in items):
                active_group_index = i
                break

        # Uretim takibi aciksa haftalik bilanco menusunu ekle
        _uretim_aktif = False
        try:
            _uretim_aktif = bool(_cs.get('uretim_takibi'))
        except Exception:
            pass

        # Dinamik menu olustur
        menu_groups = []
        for group_title, group_icon, items in MENU_GROUPS:
            dyn_items = list(items)
            if group_title == 'Operasyon' and _uretim_aktif:
                # Stok Hareketler'in altina ekle
                idx = next((j for j, (p, _, _) in enumerate(dyn_items) if p == '/hareketler'), 1)
                dyn_items.insert(idx + 1, ('/haftalik-bilanco', 'table_chart', 'Haftalık Bilanço'))
            menu_groups.append((group_title, group_icon, dyn_items))

        for i, (group_title, group_icon, items) in enumerate(menu_groups):
            with ui.expansion(group_title, icon=group_icon, value=(i == active_group_index)).classes('alse-group').props('group=navgrp dense'):
                for path, icon, text in items:
                    is_active = active_path == path
                    bg = 'bg-blue-2' if is_active else ''
                    tc = 'text-primary text-weight-bold' if is_active else 'text-grey-9'
                    ic = 'text-primary' if is_active else 'text-grey-7'
                    with ui.row().classes(
                        f'w-full items-center no-wrap cursor-pointer {bg} alse-nav-item'
                    ).on('click', lambda p=path: ui.navigate.to(p)):
                        ui.icon(icon, size='20px').classes(ic)
                        ui.label(text).classes(f'q-ml-sm {tc}').style('font-size: 13.5px')

    return drawer


def fmt_para(value):
    if value is None:
        value = 0
    s = f"{abs(value):,.2f}"
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    prefix = '-' if value < 0 else ''
    return f"{prefix}{s}"


def fmt_miktar(value):
    if value is None:
        value = 0
    s = f"{value:,.2f}"
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s


def normalize_search(value):
    text = str(value or '').strip().casefold()
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    tr_map = str.maketrans({
        'ı': 'i',
        'ş': 's',
        'ç': 'c',
        'ö': 'o',
        'ü': 'u',
        'ğ': 'g',
    })
    return text.translate(tr_map)


PARA_JS = '''value => {
    if (value == null || value === 0) return "";
    let neg = value < 0 ? "-" : "";
    let abs = Math.abs(value);
    return neg + abs.toLocaleString("tr-TR", {minimumFractionDigits:2, maximumFractionDigits:2}) + " TL";
}'''

MIKTAR_JS = '''value => {
    if (value == null || value === 0) return "";
    return value.toLocaleString("tr-TR", {minimumFractionDigits:2, maximumFractionDigits:2});
}'''

TARIH_JS = '''value => {
    if (!value) return "";
    let parts = value.split("-");
    if (parts.length === 3) return parts[2] + "." + parts[1] + "." + parts[0];
    return value;
}'''


# --- Slot Template'leri (NiceGUI table body-cell slotlari icin) ---
PARA_SLOT = r'''
    <q-td :props="props">
        {{ props.value != null && props.value !== 0
            ? (props.value < 0 ? '-' : '') + Math.abs(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' TL'
            : '' }}
    </q-td>
'''

MIKTAR_SLOT = r'''
    <q-td :props="props">
        {{ props.value != null && props.value !== 0 ? props.value.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) : '' }}
    </q-td>
'''

TARIH_SLOT = r'''
    <q-td :props="props">
        {{ props.value ? props.value.split('-').reverse().join('.') : '' }}
    </q-td>
'''


AY_ISIMLERI = {
    0: 'Tümü', 1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
    7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık',
}


def donem_secici(on_change, include_all=True):
    """Ay/Yil secici widget olusturur. on_change(yil, ay) callback ile cagirilir.
    ay=0 ise tum zamanlar demek.
    """
    from datetime import datetime
    now = datetime.now()
    ay_opts = {}
    if include_all:
        ay_opts[0] = 'Tümü'
    for m in range(1, 13):
        ay_opts[m] = AY_ISIMLERI[m]
    yil_opts = {y: str(y) for y in range(now.year - 3, now.year + 2)}

    default_ay = 0 if include_all else now.month
    sel_ay = ui.select(options=ay_opts, value=default_ay, label='Ay').props('outlined dense').style('min-width: 100px')
    sel_yil = ui.select(options=yil_opts, value=now.year, label='Yıl').props('outlined dense').style('min-width: 80px')

    def _changed(_=None):
        y = sel_yil.value
        a = sel_ay.value
        # Ay=0 (Tümü) seçilse bile yıl korunur — yıl-only filtreleme için
        on_change(y, a if a != 0 else None)

    sel_ay.on_value_change(_changed)
    sel_yil.on_value_change(_changed)
    return sel_ay, sel_yil


def notify_ok(msg):
    ui.notify(msg, type='positive', position='top')


def notify_err(msg):
    ui.notify(msg, type='negative', position='top')


def confirm_dialog(message, on_confirm):
    with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 440px'):
        with ui.element('div').classes('alse-dialog-header').style(
            'background: linear-gradient(135deg, #b71c1c 0%, #d32f2f 100%)'
        ):
            ui.icon('warning_amber').style('color: rgba(255,255,255,0.95); font-size: 28px')
            ui.label('Silme Onayı').classes('dialog-title')
        with ui.element('div').classes('alse-dialog-body'):
            ui.label(message).classes('text-subtitle1').style('color: #37474F; line-height: 1.5')
        with ui.element('div').classes('alse-dialog-footer'):
            ui.button('İptal', on_click=dlg.close).props('flat color=grey-7')
            ui.button('Evet, Sil', color='negative', on_click=lambda: (on_confirm(), dlg.close())).props('unelevated')
    dlg.open()



