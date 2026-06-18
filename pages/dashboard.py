"""ALSE Plastik Hammadde - Dashboard Sayfasi"""
from datetime import datetime
from nicegui import app, ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, donem_secici
from db import get_db
from services.cek_service import get_vade_uyarilari
from services.cari_service import get_risk_uyarilari, get_orphan_date_count
from services.kasa_service import get_kasa_bakiye
from services.gelir_gider_service import get_gelir_gider_ozet
from services.personel_service import get_personel_dashboard_ozet
from services.fx_service import get_usd_eur_rates
from services.odeme_takibi_service import list_odeme_takibi, get_vadeli_cari, get_cek_vadeleri


def _odeme_yaklasanlar(limit=5, gun=7):
    """Vadesi yaklasan (bugunden itibaren <= `gun` gun) acik odeme/tahsilat kayitlari.
    Gecmis vadeli acik kayitlar da dahil (en acil ustte). Vadeye gore artan sirali."""
    from datetime import timedelta
    bugun = datetime.now().date()
    son = (bugun + timedelta(days=gun)).isoformat()
    bugun_s = bugun.isoformat()
    rows = []
    for r in list_odeme_takibi():
        ad = (r.get('firma_ad') or '').strip() or (r.get('aciklama') or '').strip() or (r.get('kaynak') or '')
        rows.append({'tip': r['tip'], 'firma_ad': ad,
                     'kalan': float(r['tutar'] or 0) - float(r['odenen'] or 0),
                     'vade_tarih': r.get('vade_tarih', '') or '', 'durum': r['durum']})
    for r in get_vadeli_cari():
        rows.append({'tip': r['tip'], 'firma_ad': r.get('firma_ad', '') or '',
                     'kalan': float(r.get('kalan', 0) or 0),
                     'vade_tarih': r.get('vade_tarih', '') or '', 'durum': r.get('durum', 'ACIK')})
    for r in get_cek_vadeleri():
        rows.append({'tip': r['tip'], 'firma_ad': r.get('firma_ad', '') or '',
                     'kalan': float(r.get('kalan', 0) or 0),
                     'vade_tarih': r.get('vade_tarih', '') or '', 'durum': r.get('durum', 'ACIK')})
    out = [r for r in rows
           if r['durum'] != 'ODENDI' and r['kalan'] > 0.01 and r['vade_tarih'] and r['vade_tarih'] <= son]
    out.sort(key=lambda r: r['vade_tarih'])
    for r in out:
        try:
            d = (datetime.strptime(r['vade_tarih'][:10], '%Y-%m-%d').date() - bugun).days
        except Exception:
            d = None
        r['_gun'] = d
    return out[:limit]


def _load_dashboard_summary(yil=None, ay=None):
    date_filter = ''
    params = []
    if yil and ay:
        date_filter = " AND tarih LIKE ?"
        params = [f"{yil}-{ay:02d}%"]
    with get_db() as conn:
        toplam_alis = conn.execute(
            f"SELECT COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE tur='ALIS'{date_filter}", params
        ).fetchone()[0]
        toplam_satis = conn.execute(
            f"SELECT COALESCE(SUM(kdvli_toplam),0) FROM hareketler WHERE tur='SATIS'{date_filter}", params
        ).fetchone()[0]
        # Bekleyen cek vade bazli, donem filtresi uygulanmaz
        bekleyen_cek = conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM cekler WHERE durum IN ('PORTFOYDE','TAHSILE_VERILDI','KESILDI')"
        ).fetchone()[0]
    kasa = get_kasa_bakiye(yil, ay)
    return {
        'toplam_alis': toplam_alis,
        'toplam_satis': toplam_satis,
        'kasa_bakiye': kasa['bakiye'],
        'bekleyen_cek': bekleyen_cek,
    }


@ui.page('/')
def dashboard_page():
    if not create_layout(active_path='/', page_title='Bilgi Ekranı'):
        return

    # Add modern font and premium CSS styles specifically for the dashboard page
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            .dash-container {
                font-family: 'Plus Jakarta Sans', sans-serif !important;
            }
            .dash-container *:not(.q-icon):not(.material-icons) {
                font-family: 'Plus Jakarta Sans', sans-serif !important;
            }
            /* Modern Card design */
            .modern-card {
                border-radius: 16px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
                background-color: #ffffff !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .modern-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08), 0 8px 8px -5px rgba(0, 0, 0, 0.04) !important;
            }
            
            /* Gradient Card Net Profit (Positive) */
            .gradient-card-profit {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
                color: white !important;
                border-radius: 16px !important;
                box-shadow: 0 10px 20px -5px rgba(16, 185, 129, 0.3) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .gradient-card-profit:hover {
                transform: translateY(-4px);
                box-shadow: 0 16px 28px -5px rgba(16, 185, 129, 0.45) !important;
            }

            /* Gradient Card Net Loss (Negative) */
            .gradient-card-loss {
                background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%) !important;
                color: white !important;
                border-radius: 16px !important;
                box-shadow: 0 10px 20px -5px rgba(244, 63, 94, 0.3) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .gradient-card-loss:hover {
                transform: translateY(-4px);
                box-shadow: 0 16px 28px -5px rgba(244, 63, 94, 0.45) !important;
            }

            /* Gradient Card Kasa (Liquidity) */
            .gradient-card-kasa {
                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
                color: white !important;
                border-radius: 16px !important;
                box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.3) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .gradient-card-kasa:hover {
                transform: translateY(-4px);
                box-shadow: 0 16px 28px -5px rgba(59, 130, 246, 0.45) !important;
            }
            
            /* Custom Table Look inside Dashboard */
            .dash-table thead tr th {
                background: #f8fafc !important;
                color: #64748b !important;
                font-weight: 700 !important;
                font-size: 11px !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
                border-bottom: 2px solid #e2e8f0 !important;
            }
            .dash-table tbody tr {
                background: transparent !important;
                transition: background 0.2s ease;
            }
            .dash-table tbody tr:hover {
                background: #f8fafc !important;
                transform: none !important;
                box-shadow: none !important;
            }
            .dash-table tbody td {
                border-bottom: 1px solid #edf2f7 !important;
                color: #1e293b !important;
            }

            /* Responsive Grid layout adjustments */
            .primary-kpis-grid {
                display: grid;
                grid-template-columns: 1fr 1fr 3fr;
            }
            .secondary-kpis-grid {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
            }
            @media (max-width: 960px) {
                .primary-kpis-grid {
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)) !important;
                }
                .secondary-kpis-grid {
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
                }
            }
            @media (max-width: 640px) {
                .primary-kpis-grid {
                    grid-template-columns: 1fr !important;
                }
                .secondary-kpis-grid {
                    grid-template-columns: 1fr 1fr !important;
                }
            }
        </style>
    ''')

    now = datetime.now()
    # Default: yil=mevcut, ay=None (Tumu) — UI ile sync (donem_secici default_ay=0=Tumu)
    state = {'yil': now.year, 'ay': None}
    fx = get_usd_eur_rates() or {}

    # Toggle View Mode handler
    def toggle_view():
        current = app.storage.user.get('dashboard_view', 'modern')
        new_mode = 'classic' if current == 'modern' else 'modern'
        app.storage.user['dashboard_view'] = new_mode
        ui.run_javascript('window.location.reload()')

    # --- Refreshable icerik blogu ---
    @ui.refreshable
    def dash_content():
        view_mode = 'modern'
        yil = state['yil']
        ay = state['ay']
        summary = _load_dashboard_summary(yil, ay)
        uyarilar = get_vade_uyarilari()
        gg_ozet = get_gelir_gider_ozet(yil, ay)
        p_ozet = get_personel_dashboard_ozet()

        net_kar = gg_ozet['net']
        is_profit = net_kar >= 0

        if view_mode == 'classic':
            # --- OLD CLASSIC CARD GRID ---
            cards_data = [
                ('Toplam Alış', summary['toplam_alis'], 'shopping_cart', 'blue-7'),
                ('Toplam Satış', summary['toplam_satis'], 'point_of_sale', 'green-7'),
                ('Kasa Bakiyesi', summary['kasa_bakiye'], 'account_balance_wallet', 'teal-7'),
                ('Bekleyen Çek', summary['bekleyen_cek'], 'receipt_long', 'orange-7'),
                ('Gelir', gg_ozet['gelir'], 'trending_up', 'green-9'),
                ('Gider', gg_ozet['gider'], 'trending_down', 'red-7'),
                ('Net Kar/Zarar', gg_ozet['net'], 'account_balance', 'purple-7'),
                ('Aktif Personel', p_ozet['aktif_sayi'], 'badge', 'indigo-7'),
                ('Aylık Maaş', p_ozet['aylik_maas'], 'payments', 'pink-7'),
            ]

            with ui.grid(columns='repeat(5, 1fr)').classes('w-full gap-1 dash-cards'):
                for label, value, icon, color in cards_data:
                    with ui.card().classes('q-pa-xs').style('min-height: 50px;'):
                        with ui.row().classes('items-center no-wrap gap-1'):
                            ui.icon(icon, color=color).style('font-size: 20px')
                            with ui.column().classes('gap-0').style('line-height:1'):
                                ui.label(label).classes('text-grey-7').style('font-size: 10px; line-height: 12px')
                                ui.label(f'{fmt_para(value)} TL').classes('text-weight-bold').style('font-size: 13px; line-height: 15px')
        else:
            # --- NEW MODERN CARDS & COMPARISON ---
            with ui.element('div').classes('w-full gap-4 q-mt-lg q-mb-md primary-kpis-grid'):
                # Net Kar / Zarar Card
                card_class = 'gradient-card-profit' if is_profit else 'gradient-card-loss'
                with ui.card().classes(f'q-pa-sm {card_class} justify-between').style('height: 78px; border-radius: 12px; overflow: hidden;'):
                    with ui.row().classes('w-full justify-between items-start no-wrap'):
                        ui.label('Net Kar / Zarar').classes('text-weight-medium').style('font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; opacity: 0.9;')
                        with ui.element('div').style('background: rgba(255,255,255,0.2); border-radius: 7px; display: flex; align-items: center; justify-content: center; width: 26px; height: 26px;'):
                            ui.icon('trending_up' if is_profit else 'trending_down', color='white', size='17px')
                    ui.label(f'{fmt_para(net_kar)} TL').classes('text-weight-bolder').style('font-size: 19px; font-weight: 800; letter-spacing: -0.5px;')

                # Kasa Bakiyesi Card
                kasa_bakiye = summary['kasa_bakiye']
                with ui.card().classes('q-pa-sm gradient-card-kasa justify-between').style('height: 78px; border-radius: 12px; overflow: hidden;'):
                    with ui.row().classes('w-full justify-between items-start no-wrap'):
                        ui.label('Kasa Bakiyesi').classes('text-weight-medium').style('font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; opacity: 0.9;')
                        with ui.element('div').style('background: rgba(255,255,255,0.2); border-radius: 7px; display: flex; align-items: center; justify-content: center; width: 26px; height: 26px;'):
                            ui.icon('account_balance_wallet', color='white', size='17px')
                    ui.label(f'{fmt_para(kasa_bakiye)} TL').classes('text-weight-bolder').style('font-size: 19px; font-weight: 800; letter-spacing: -0.5px;')

                # Satış ve Alış Karşılaştırma Kartı
                satis = summary['toplam_satis']
                alis = summary['toplam_alis']
                toplam_hacim = satis + alis
                satis_pct = (satis / toplam_hacim * 100) if toplam_hacim > 0 else 50.0
                alis_pct = (alis / toplam_hacim * 100) if toplam_hacim > 0 else 50.0

                if toplam_hacim >= 1_000_000:
                    hacim_txt = f"{toplam_hacim / 1_000_000:.1f} M TL"
                elif toplam_hacim >= 1_000:
                    hacim_txt = f"{toplam_hacim / 1_000:.1f} K TL"
                else:
                    hacim_txt = f"{int(toplam_hacim)} TL"

                with ui.card().classes('q-pa-sm modern-card justify-between').style('height: 78px; border-radius: 12px; overflow: hidden;'):
                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                        ui.label('SATIŞ / ALIŞ').classes('text-weight-bold').style('font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; color: #64748b;')
                        ui.label(f'HACİM: {hacim_txt}').style('background:#eff6ff;color:#2563eb;border-radius:20px;font-size:10px;font-weight:700;padding:1px 8px;')
                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                        ui.label(f'{fmt_para(satis)} TL').classes('text-weight-bold text-green-6').style('font-size: 14px;')
                        ui.label(f'{fmt_para(alis)} TL').classes('text-weight-bold text-red-6').style('font-size: 14px;')
                    with ui.row().classes('w-full no-wrap items-center').style('height: 5px; background: #e2e8f0; border-radius: 3px; overflow: hidden; gap: 0;'):
                        ui.element('div').style(f'width: {satis_pct}%; height: 100%; background: #10b981;')
                        ui.element('div').style(f'width: {alis_pct}%; height: 100%; background: #ef4444;')

            # --- Secondary KPIs Row ---
            cards_secondary = [
                ('Bekleyen Çek', summary['bekleyen_cek'], 'receipt_long', '#fff7ed', '#ea580c'),
                ('Gelir', gg_ozet['gelir'], 'trending_up', '#ecfdf5', '#10b981'),
                ('Gider', gg_ozet['gider'], 'trending_down', '#fff1f2', '#f43f5e'),
                ('Aktif Personel', p_ozet['aktif_sayi'], 'badge', '#eef2ff', '#4f46e5'),
                ('Aylık Maaş', p_ozet['aylik_maas'], 'payments', '#fdf2f8', '#db2777'),
            ]

            with ui.element('div').classes('w-full gap-4 q-mb-md secondary-kpis-grid'):
                for label, value, icon, bg_color, text_color in cards_secondary:
                    with ui.card().classes('q-pa-md modern-card').style('border-radius: 16px;'):
                        with ui.row().classes('items-center no-wrap gap-3'):
                            with ui.element('div').style(f'width: 44px; height: 44px; background: {bg_color}; color: {text_color}; border-radius: 12px; display: flex; align-items: center; justify-content: center;'):
                                ui.icon(icon, size='24px')
                            with ui.column().classes('gap-0'):
                                ui.label(label).classes('text-grey-6').style('font-size: 11px; font-weight: 500;')
                                val_txt = f'{int(value or 0)}' if label == 'Aktif Personel' else f'{fmt_para(value)} TL'
                                ui.label(val_txt).classes('text-weight-bold text-slate-800').style('font-size: 14px;')

        # --- Bos Tarih Uyarisi (Paket 3) ---
        orphan = get_orphan_date_count()
        if orphan:
            total = sum(orphan.values())
            if view_mode == 'classic':
                with ui.card().classes('w-full q-pa-xs q-mt-xs').style('background: #FFF3E0; border-left: 3px solid #FB8C00'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('event_busy', color='orange-9').style('font-size: 22px')
                        with ui.column().classes('gap-0'):
                            ui.label(f'TARIH BELIRSIZ: {total} kayit').classes('text-weight-bold text-orange-10')
                            detay = ', '.join(f"{k}: {v}" for k, v in orphan.items())
                            ui.label(f'Bu kayitlar donem raporlarina dahil edilmiyor. Detay: {detay}').classes('text-caption text-orange-9')
            else:
                with ui.card().classes('w-full q-pa-md q-mb-md').style('background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 12px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);'):
                    with ui.row().classes('items-center gap-3 no-wrap'):
                        ui.icon('event_busy', color='warning').style('font-size: 28px; color: #d97706 !important;')
                        with ui.column().classes('gap-0'):
                            ui.label(f'TARİH BELİRSİZ: {total} Kayıt Mevcut!').classes('text-weight-bold').style('color: #92400e; font-size: 13.5px;')
                            detay = ', '.join(f"{k}: {v}" for k, v in orphan.items())
                            ui.label(f'Bu kayıtlar tarihleri girilmediği için dönem raporlarına dahil edilmemektedir. Detay: {detay}').style('color: #b45309; font-size: 12px;')

        # --- Risk Limiti Uyarilari ---
        risk_list = get_risk_uyarilari()
        risk_uyari = [r for r in risk_list if r['limit_asimi'] or r['risk_yuzdesi'] >= 80]
        risk_rows = []
        for r in risk_uyari:
            durum = 'ASILDI' if r['limit_asimi'] else '>%80'
            kalan_limit = (r['risk_limiti'] or 0) - (r['bakiye'] or 0)
            risk_rows.append({
                'kod': r.get('kod', ''),
                'firma': r['ad'],
                'bakiye': r['bakiye'],
                'risk_limiti': r['risk_limiti'],
                'kalan_limit': kalan_limit,
                'kullanim': r['risk_yuzdesi'],
                'durum': durum,
            })

        # --- Cek/Senet Vade Uyarilari ---
        tum_uyarilar = []
        for row in uyarilar.get('gecmis', []):
            r = dict(row)
            r['aciliyet'] = 'GECMİS'
            tum_uyarilar.append(r)
        for row in uyarilar.get('bugun', []):
            r = dict(row)
            r['aciliyet'] = 'BUGUN'
            tum_uyarilar.append(r)
        for row in uyarilar.get('uc_gun', []):
            r = dict(row)
            r['aciliyet'] = '3_GUN'
            tum_uyarilar.append(r)
        for row in uyarilar.get('yedi_gun', []):
            r = dict(row)
            r['aciliyet'] = '7_GUN'
            tum_uyarilar.append(r)
        for row in uyarilar.get('otuz_gun', []):
            r = dict(row)
            r['aciliyet'] = '30_GUN'
            tum_uyarilar.append(r)
        for row in uyarilar.get('doksan_gun', []):
            r = dict(row)
            r['aciliyet'] = '90_GUN'
            tum_uyarilar.append(r)

        if view_mode == 'classic':
            # --- CLASSIC TABLES (STACKED) ---
            if risk_uyari:
                with ui.row().classes('items-center gap-1 q-mt-xs'):
                    ui.icon('warning', color='orange-8').style('font-size: 20px')
                    ui.label('Risk Limiti Uyarıları').classes('text-subtitle1 text-weight-bold')
                with ui.card().classes('w-full q-pa-xs'):
                    risk_columns = [
                        {'name': 'firma', 'label': 'Firma', 'field': 'firma', 'align': 'left', 'sortable': True},
                        {'name': 'bakiye', 'label': 'Bakiye', 'field': 'bakiye', 'align': 'right', 'sortable': True},
                        {'name': 'risk_limiti', 'label': 'Risk Limiti', 'field': 'risk_limiti', 'align': 'right'},
                        {'name': 'kullanim', 'label': 'Kullanım %', 'field': 'kullanim', 'align': 'center', 'sortable': True},
                        {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center'},
                    ]
                    rt = ui.table(
                        columns=risk_columns, rows=risk_rows, row_key='firma',
                        pagination={'rowsPerPage': 20},
                    ).classes('w-full').props('flat dense')
                    rt.add_slot('body-cell-bakiye', r'''
                        <q-td :props="props">
                            <span :class="props.row.durum === 'ASILDI' ? 'text-red-8 text-weight-bold' : 'text-orange-8 text-weight-bold'">
                                {{ Number(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) }} TL
                            </span>
                        </q-td>
                    ''')
                    rt.add_slot('body-cell-risk_limiti', r'''
                        <q-td :props="props">
                            {{ Number(props.value).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) }} TL
                        </q-td>
                    ''')
                    rt.add_slot('body-cell-kullanim', r'''
                        <q-td :props="props">
                            <span :class="props.value > 100 ? 'text-red-8 text-weight-bold' : 'text-orange-8 text-weight-bold'">
                                %{{ props.value }}
                            </span>
                        </q-td>
                    ''')
                    rt.add_slot('body-cell-durum', r'''
                        <q-td :props="props">
                            <q-badge dense text-color="white"
                                :color="props.value === 'ASILDI' ? 'red' : 'orange'">
                                {{ props.value === 'ASILDI' ? 'AŞILDI' : '>%80' }}
                            </q-badge>
                        </q-td>
                    ''')

            ui.label('Çek / Senet Vade Uyarıları').classes('text-subtitle1 text-weight-bold q-mt-xs')
            if not tum_uyarilar:
                with ui.card().classes('w-full q-pa-xs'):
                    ui.label('Yaklaşan vade uyarısı bulunmuyor.').classes('text-caption text-grey-7')
            else:
                with ui.card().classes('w-full q-pa-xs'):
                    vade_columns = [
                        {'name': 'aciliyet', 'label': 'Aciliyet', 'field': 'aciliyet', 'align': 'center', 'sortable': True},
                        {'name': 'evrak_tipi', 'label': 'Tip', 'field': 'evrak_tipi', 'align': 'center'},
                        {'name': 'cek_turu', 'label': 'Yön', 'field': 'cek_turu', 'align': 'center', 'sortable': True},
                        {'name': 'cek_no', 'label': 'No', 'field': 'cek_no', 'align': 'left'},
                        {'name': 'firma_ad', 'label': 'Firma', 'field': 'firma_ad', 'align': 'left'},
                        {'name': 'vade_tarih', 'label': 'Vade Tarih', 'field': 'vade_tarih', 'align': 'center'},
                        {'name': 'tutar', 'label': 'Tutar', 'field': 'tutar', 'align': 'right'},
                    ]
                    t = ui.table(
                        columns=vade_columns, rows=tum_uyarilar, row_key='id',
                        pagination={'rowsPerPage': 50},
                    ).classes('w-full').props('flat dense')
                    t.add_slot('body-cell-vade_tarih', TARIH_SLOT)
                    t.add_slot('body-cell-tutar', PARA_SLOT)
                    t.add_slot('body-cell-aciliyet', r'''
                        <q-td :props="props">
                            <q-badge dense text-color="white"
                                :color="props.value === 'GECMİS' ? 'red-4' :
                                        props.value === 'BUGUN' ? 'red-3' :
                                        props.value === '3_GUN' ? 'orange-4' :
                                        props.value === '7_GUN' ? 'amber-6' :
                                        props.value === '30_GUN' ? 'blue-4' : 'blue-grey-4'">
                                {{ props.value === 'GECMİS' ? 'Geçmiş' :
                                   props.value === 'BUGUN' ? 'Bugün' :
                                   props.value === '3_GUN' ? '3 Gün' :
                                   props.value === '7_GUN' ? '7 Gün' :
                                   props.value === '30_GUN' ? '1 Ay' : '3 Ay' }}
                            </q-badge>
                        </q-td>
                    ''')
                    t.add_slot('body-cell-evrak_tipi', r'''
                        <q-td :props="props">
                            <span :class="props.value === 'SENET' ? 'text-orange-8' : 'text-blue-7'"
                                  class="text-caption text-weight-medium">
                                {{ props.value === 'SENET' ? 'Senet' : 'Çek' }}
                            </span>
                        </q-td>
                    ''')
                    t.add_slot('body-cell-cek_turu', r'''
                        <q-td :props="props">
                            <span :class="props.value === 'ALINAN' ? 'text-green-8' : 'text-red-7'"
                                  class="text-caption text-weight-medium">
                                {{ props.value === 'ALINAN' ? 'Alınan' : 'Verilen' }}
                            </span>
                        </q-td>
                    ''')

        else:
            # --- MODERN SIDE-BY-SIDE GRID LAYOUT ---
            with ui.row().classes('w-full items-start no-wrap gap-4 q-row-mobile-wrap q-mt-md'):
                # Sol: Yaklaşan Ödeme / Tahsilat (7 gün) (flex-2)
                yaklasan = _odeme_yaklasanlar(5, 7)
                with ui.card().classes('modern-card q-pa-md').style('flex: 2; border-radius: 16px; min-width: 0;'):
                    with ui.row().classes('w-full justify-between items-center no-wrap q-mb-md'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('event', color='primary').style('font-size: 20px; color: #2563eb !important;')
                            ui.label('Yaklaşan Ödeme / Tahsilat').classes('text-subtitle1 text-weight-bold text-slate-800').style('font-size: 15px;')
                            ui.label('7 gün').style('font-size: 11px; color: #64748b;')
                        if yaklasan:
                            with ui.row().classes('items-center q-px-sm q-py-xs').style('background: #eff6ff; color: #2563eb; border-radius: 20px; font-size: 11px; font-weight: 600;'):
                                ui.label(f'{len(yaklasan)} kayıt')
                    if not yaklasan:
                        ui.label('Önümüzdeki 7 günde vadesi gelen açık kayıt yok.').classes('text-caption text-grey-6 q-pa-sm')
                    else:
                        def _gunlbl(g):
                            if g is None:
                                return ''
                            if g < 0:
                                return f'{abs(g)} gün geçti'
                            if g == 0:
                                return 'Bugün'
                            return f'{g} gün kaldı'
                        yk_rows = []
                        for i, item in enumerate(yaklasan):
                            vd = (item.get('vade_tarih') or '')[:10]
                            vd = '.'.join(reversed(vd.split('-'))) if vd else ''
                            yk_rows.append({
                                '_rid': i,
                                'vade': vd,
                                'tip': 'Borç' if item['tip'] == 'BORC' else 'Alacak',
                                'firma': item.get('firma_ad') or '—',
                                'durum': _gunlbl(item.get('_gun')),
                                'kalan': float(item['kalan'] or 0),
                                '_borc': item['tip'] == 'BORC',
                                '_gun': item.get('_gun') if item.get('_gun') is not None else 999,
                            })
                        yk_cols = [
                            {'name': 'vade', 'label': 'Vade', 'field': 'vade', 'align': 'left'},
                            {'name': 'tip', 'label': 'Tip', 'field': 'tip', 'align': 'center'},
                            {'name': 'firma', 'label': 'Firma', 'field': 'firma', 'align': 'left'},
                            {'name': 'durum', 'label': 'Durum', 'field': 'durum', 'align': 'center'},
                            {'name': 'kalan', 'label': 'Tutar', 'field': 'kalan', 'align': 'right'},
                        ]
                        ykt = ui.table(columns=yk_cols, rows=yk_rows, row_key='_rid',
                                       pagination={'rowsPerPage': 0}).classes('w-full dash-table').props('flat dense hide-bottom')
                        ykt.add_slot('body', r'''
                            <q-tr :props="props"
                                :style="props.row._gun === 0 ? 'background:#fef2f2 !important;' : ''"
                                :class="props.row._gun === 0 ? 'yk-bugun' : ''">
                                <q-td key="vade" :props="props"
                                    :style="props.row._gun === 0 ? 'border-left:4px solid #ef4444;' : (props.row._gun < 0 ? 'border-left:4px solid #f59e0b;' : '')">
                                    <span style="font-weight:700;font-size:11px;color:#334155;">{{ props.row.vade }}</span>
                                </q-td>
                                <q-td key="tip" :props="props" class="text-center">
                                    <span style="display:inline-block;padding:2px 10px;border-radius:999px;font-weight:700;font-size:11px;"
                                        :style="props.row._borc ? 'background:#ffe4e6;color:#be123c;' : 'background:#dcfce7;color:#15803d;'">{{ props.row.tip }}</span>
                                </q-td>
                                <q-td key="firma" :props="props">{{ props.row.firma }}</q-td>
                                <q-td key="durum" :props="props" class="text-center">
                                    <span v-if="props.row._gun === 0"
                                        style="display:inline-block;background:#ef4444;color:#fff;padding:2px 10px;border-radius:999px;font-weight:800;font-size:10.5px;letter-spacing:0.3px;">
                                        ● BUGÜN SON GÜN
                                    </span>
                                    <span v-else :style="props.row._gun < 0 ? 'color:#b91c1c;font-weight:700;' : (props.row._gun <= 3 ? 'color:#c2410c;font-weight:600;' : 'color:#64748b;')">{{ props.row.durum }}</span>
                                </q-td>
                                <q-td key="kalan" :props="props" class="text-right">
                                    <span :style="props.row._borc ? 'color:#ef4444;font-weight:700;' : 'color:#10b981;font-weight:700;'">{{ Number(props.row.kalan).toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2}) }} TL</span>
                                </q-td>
                            </q-tr>''')

                # Sağ: Vade Uyarıları (flex-1, Compact Liste)
                with ui.card().classes('modern-card q-pa-md').style('flex: 1; border-radius: 16px; min-width: 0;'):
                    with ui.row().classes('w-full justify-between items-center no-wrap q-mb-md'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('notification_important', color='primary').style('font-size: 20px; color: #2563eb !important;')
                            ui.label('Çek / Senet Vade Uyarıları').classes('text-subtitle1 text-weight-bold text-slate-800').style('font-size: 15px;')
                        if tum_uyarilar:
                            with ui.row().classes('items-center q-px-sm q-py-xs').style('background: #fee2e2; color: #b91c1c; border-radius: 20px; font-size: 11px; font-weight: 600;'):
                                ui.label(f'{len(tum_uyarilar)} Bildirim')
                    if not tum_uyarilar:
                        ui.label('Yaklaşan vade uyarısı bulunmuyor.').classes('text-caption text-grey-6 q-pa-sm')
                    else:
                        with ui.column().classes('w-full gap-2'):
                            for item in tum_uyarilar[:5]:
                                aciliyet = item.get('aciliyet', '90_GUN')
                                tip = 'Senet' if item.get('evrak_tipi') == 'SENET' else 'Çek'
                                yon = 'Alınan' if item.get('cek_turu') == 'ALINAN' else 'Verilen'
                                check_no = item.get('cek_no') or ''
                                firma = item.get('firma_ad') or ''
                                tutar = item.get('tutar') or 0
                                
                                border_color = '#ef4444' if aciliyet in ('GECMİS', 'BUGUN') else ('#f59e0b' if aciliyet in ('3_GUN', '7_GUN') else '#3b82f6')
                                bg_color = '#f8fafc'
                                
                                with ui.row().classes('w-full justify-between items-center q-pa-sm').style(f'border-left: 4px solid {border_color}; border-radius: 8px; background: {bg_color}; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0;'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'{yon} {tip} • No: {check_no}').classes('text-weight-bold text-slate-800').style('font-size: 12px; line-height: 1.25;')
                                        urgency_lbl = 'Vade Geçmiş' if aciliyet == 'GECMİS' else ('Bugün' if aciliyet == 'BUGUN' else f'{aciliyet.replace("_", " ")} Kaldı')
                                        ui.label(f'{firma} • {urgency_lbl}').classes('text-grey-5').style('font-size: 10px; margin-top: 2px;')
                                    ui.label(f'{fmt_para(tutar)} TL').classes('text-weight-bold').style(f'font-size: 12px; color: {border_color};')

    # --- Header Panel (non-refreshable / dynamic inside container) ---
    @ui.refreshable
    def header_container():
        view_mode = 'modern'
        
        if view_mode == 'classic':
            # --- CLASSIC HEADER ---
            with ui.card().classes('w-full q-pa-xs'):
                with ui.row().classes('w-full items-center gap-2 no-wrap'):
                    ui.space()
                    usd = (fx.get('USD') or {}).get('sell')
                    eur = (fx.get('EUR') or {}).get('sell')
                    usd_txt = f'USD: {usd:.4f}' if isinstance(usd, (int, float)) else 'USD: -'
                    eur_txt = f'EUR: {eur:.4f}' if isinstance(eur, (int, float)) else 'EUR: -'
                    with ui.element('q-chip').props('dense color="blue-1" text-color="blue-10" icon="attach_money"'):
                        ui.label(usd_txt).classes('text-caption text-weight-medium')
                    with ui.element('q-chip').props('dense color="amber-1" text-color="amber-10" icon="euro"'):
                        ui.label(eur_txt).classes('text-caption text-weight-medium')
                    
                    # Add view switcher button
                    ui.button(
                        'Modern Arayüz',
                        icon='space_dashboard',
                        on_click=toggle_view
                    ).props('outline dense size=sm no-caps color=primary').style('border-radius: 20px; padding: 2px 10px;')
                    
                    donem_secici(_on_donem, include_all=True)
        else:
            with ui.row().classes('w-full items-center justify-between no-wrap q-row-mobile-wrap gap-4 q-pt-none q-pb-none'):
                with ui.column().classes('gap-0'):
                    ui.label('Bilgi Ekranı').style('font-size: 19px; font-weight: 800; color: #0f172a; font-family: "Plus Jakarta Sans", sans-serif; line-height: 1.15;')
                    ui.label('Bugün işletmenizin durumu harika görünüyor!').style('font-size: 12px; color: #64748b; font-family: "Plus Jakarta Sans", sans-serif; line-height: 1.1;')
                
                with ui.row().classes('items-center gap-3 no-wrap'):
                    usd = (fx.get('USD') or {}).get('sell')
                    usd_txt = f'USD: {usd:.2f}' if isinstance(usd, (int, float)) else 'USD: -'
                    with ui.row().classes('items-center gap-1 q-px-md q-py-xs').style('background: #ffffff; color: #475569; border-radius: 20px; border: 1px solid #cbd5e1; font-size: 11px; font-weight: 700; height: 32px;'):
                        ui.icon('attach_money', size='14px', color='primary')
                        ui.label(usd_txt)
                    
                    eur = (fx.get('EUR') or {}).get('sell')
                    eur_txt = f'EUR: {eur:.2f}' if isinstance(eur, (int, float)) else 'EUR: -'
                    with ui.row().classes('items-center gap-1 q-px-md q-py-xs').style('background: #ffffff; color: #475569; border-radius: 20px; border: 1px solid #cbd5e1; font-size: 11px; font-weight: 700; height: 32px;'):
                        ui.icon('euro', size='14px', color='warning')
                        ui.label(eur_txt)
                        
                    donem_secici(_on_donem, include_all=True)

    # --- Donem degistiginde ---
    def _on_donem(yil, ay):
        state['yil'] = yil
        state['ay'] = ay
        dash_content.refresh()

    with ui.column().classes('w-full q-px-sm q-pt-xs q-pb-sm gap-2 dash-container').style('max-width: 1400px; margin: 0 auto;'):
        header_container()

        dash_content()
