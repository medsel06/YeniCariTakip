"""Kolay Muhasebe — public tanıtım (landing) sayfası."""
from nicegui import ui

FEATURES = [
    ('groups', 'Cari Hesaplar',
     'Müşteri/tedarikçi bakiyeleri, ekstre ve tek tıkla WhatsApp’tan hesap özeti.'),
    ('inventory_2', 'Stok & Ürün',
     'Ürün bazlı alış/satış takibi, ortalama fiyat ve kâr marjı raporu.'),
    ('account_balance', 'Kasa & Banka',
     'Nakit ve banka hareketleri, tahsilat/ödeme, anlık kasa bakiyesi.'),
    ('description', 'Çek / Senet',
     'Portföy görünümü, vade takvimi ve yaklaşan vade uyarıları.'),
    ('receipt_long', 'Gelir / Gider',
     'Kategori bazlı gider takibi ve gün/ay/yıl filtreli PDF raporlar.'),
    ('query_stats', 'Raporlar & Analiz',
     'Karlılık, mutabakat, tahsilat önerisi ve çek takvimi tek ekranda.'),
]

_LANDING_CSS = '''
<style>
  .km-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
  @media (max-width:900px){ .km-grid{ grid-template-columns:repeat(2,1fr); } }
  @media (max-width:600px){ .km-grid{ grid-template-columns:1fr; } .km-hero-h{ font-size:30px !important; } }
  .km-feat { background:#fff; border:1px solid #ede9fe; border-radius:16px; padding:20px;
             box-shadow:0 4px 14px rgba(124,58,237,.06); transition:transform .2s, box-shadow .2s; }
  .km-feat:hover { transform:translateY(-4px); box-shadow:0 12px 28px rgba(124,58,237,.12); }
</style>
'''


def render_landing():
    ui.query('body').style('margin:0;background:#faf7ff')
    ui.add_head_html(_LANDING_CSS)

    # --- Hero (mor gradient) ---
    with ui.column().classes('w-full items-center').style(
            'background:linear-gradient(135deg,#4c1d95 0%,#6d28d9 55%,#7c3aed 100%);gap:0'):
        # ust bar
        with ui.row().classes('w-full items-center justify-between no-wrap').style(
                'max-width:1100px;padding:18px 24px'):
            with ui.row().classes('items-center no-wrap').style('gap:10px'):
                ui.icon('ads_click').style(
                    'font-size:24px;color:#fff;background:rgba(255,255,255,.16);padding:7px;border-radius:11px')
                with ui.row().classes('items-baseline no-wrap').style('gap:3px'):
                    ui.label('Kolay').style('font-size:21px;font-weight:800;color:#fff')
                    ui.label('Muhasebe').style('font-size:21px;font-weight:800;color:#c4b5fd')
            ui.button('Giriş Yap', icon='login', on_click=lambda: ui.navigate.to('/login'),
                      color=None).props('no-caps unelevated').style(
                'background:#fff;color:#6d28d9;font-weight:700;border-radius:10px')

        # hero icerik
        with ui.column().classes('items-center').style(
                'max-width:840px;padding:44px 24px 72px;gap:16px'):
            ui.label('İşletmenizin tüm hesabı tek panelde').classes('km-hero-h').style(
                'font-size:42px;font-weight:800;color:#fff;line-height:1.14;letter-spacing:-1px;text-align:center')
            ui.label('Cari, stok, kasa, banka, çek/senet, gelir-gider ve raporlar — '
                     'hepsini tek ekrandan, kolayca yönetin.').style(
                'font-size:16px;color:#ede9fe;max-width:620px;text-align:center;line-height:1.6')
            ui.button('Hemen Giriş Yap', icon='arrow_forward',
                      on_click=lambda: ui.navigate.to('/login'), color=None).props('no-caps unelevated').style(
                'background:#fff;color:#6d28d9;font-weight:700;height:48px;padding:0 26px;'
                'border-radius:12px;margin-top:6px;box-shadow:0 10px 30px rgba(0,0,0,.18)')
            ui.label('Cari • Stok • Kasa • Çek • Gelir/Gider • Raporlar').style(
                'font-size:12px;color:#c4b5fd;letter-spacing:.6px;margin-top:2px')

    # --- Ozellikler ---
    with ui.column().classes('w-full items-center').style('padding:56px 24px'):
        ui.label('Neler yapabilirsiniz?').style(
            'font-size:25px;font-weight:800;color:#1e1b4b;text-align:center')
        ui.label('Günlük muhasebe işlerinizi hızlandıran araçlar').style(
            'font-size:14px;color:#6b7280;margin-bottom:26px;text-align:center')
        with ui.element('div').classes('km-grid').style('max-width:1050px;width:100%'):
            for ikon, baslik, aciklama in FEATURES:
                with ui.element('div').classes('km-feat'):
                    ui.icon(ikon).style(
                        'font-size:26px;color:#7c3aed;background:#f3e8ff;padding:10px;border-radius:12px')
                    ui.label(baslik).style('font-size:15px;font-weight:700;color:#1e1b4b;margin-top:12px')
                    ui.label(aciklama).style('font-size:13px;color:#6b7280;line-height:1.55;margin-top:4px')

    # --- Alt CTA seridi ---
    with ui.column().classes('w-full items-center').style(
            'background:linear-gradient(135deg,#6d28d9,#7c3aed);padding:44px 24px;gap:14px'):
        ui.label('Hesabınıza giriş yapın').style('font-size:22px;font-weight:800;color:#fff;text-align:center')
        ui.button('Giriş Yap', icon='login', on_click=lambda: ui.navigate.to('/login'),
                  color=None).props('no-caps unelevated').style(
            'background:#fff;color:#6d28d9;font-weight:700;height:46px;padding:0 26px;border-radius:12px')

    # --- Footer ---
    with ui.column().classes('w-full items-center').style('background:#1e1b4b;padding:24px'):
        ui.label('© 2026 Kolay Muhasebe · Tüm hakları saklıdır').style('color:#c4b5fd;font-size:12.5px')


@ui.page('/tanitim')
def tanitim_page():
    render_landing()
