"""ALSE Plastik Hammadde - Dashboard Sayfasi"""
from datetime import datetime
from nicegui import ui
from layout import create_layout, fmt_para, PARA_SLOT, TARIH_SLOT, donem_secici
from db import get_db
from services.cek_service import get_vade_uyarilari
from services.cari_service import get_risk_uyarilari
from services.kasa_service import get_kasa_bakiye
from services.gelir_gider_service import get_gelir_gider_ozet
from services.personel_service import get_personel_dashboard_ozet
from services.fx_service import get_usd_eur_rates


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

    now = datetime.now()
    state = {'yil': now.year, 'ay': now.month}
    fx = get_usd_eur_rates() or {}
    clock_label = {'el': None}

    # --- Refreshable icerik blogu ---
    @ui.refreshable
    def dash_content():
        yil = state['yil']
        ay = state['ay']
        summary = _load_dashboard_summary(yil, ay)
        uyarilar = get_vade_uyarilari()
        gg_ozet = get_gelir_gider_ozet(yil, ay)
        p_ozet = get_personel_dashboard_ozet()

        # --- Kompakt Kartlar (kucuk) ---
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

        # --- Risk Limiti Uyarilari ---
        risk_list = get_risk_uyarilari()
        # Sadece limit asimi veya %80 uzeri olanlari goster
        risk_uyari = [r for r in risk_list if r['limit_asimi'] or r['risk_yuzdesi'] >= 80]
        if risk_uyari:
            with ui.row().classes('items-center gap-1 q-mt-xs'):
                ui.icon('warning', color='orange-8').style('font-size: 20px')
                ui.label('Risk Limiti Uyarıları').classes('text-subtitle1 text-weight-bold')
            risk_rows = []
            for r in risk_uyari:
                durum = 'ASILDI' if r['limit_asimi'] else '>%80'
                risk_rows.append({
                    'firma': r['ad'],
                    'bakiye': r['bakiye'],
                    'risk_limiti': r['risk_limiti'],
                    'kullanim': r['risk_yuzdesi'],
                    'durum': durum,
                })
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

        # --- Cek/Senet Vade Uyarilari (tek tablo, aciliyet badge) ---
        ui.label('Çek / Senet Vade Uyarıları').classes('text-subtitle1 text-weight-bold q-mt-xs')

        # Tum uyarilari tek listeye birleştir, aciliyet badge ekle
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
                                    props.value === '3_GUN' ? 'orange-4' : 'amber-6'">
                            {{ props.value === 'GECMİS' ? 'Geçmiş' :
                               props.value === 'BUGUN' ? 'Bugün' :
                               props.value === '3_GUN' ? '3 Gün' : '7 Gün' }}
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

    # --- Donem degistiginde ---
    def _on_donem(yil, ay):
        state['yil'] = yil
        state['ay'] = ay
        dash_content.refresh()

    with ui.column().classes('w-full q-pa-xs gap-1').style('max-width: 1400px; margin: 0 auto'):
        with ui.card().classes('w-full q-pa-xs'):
            with ui.row().classes('w-full items-center gap-2'):
                now_txt = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                clock_label['el'] = ui.label(f'{now_txt}').classes('text-caption text-weight-medium')
                ui.space()
                usd = (fx.get('USD') or {}).get('sell')
                eur = (fx.get('EUR') or {}).get('sell')
                usd_txt = f'USD: {usd:.4f}' if isinstance(usd, (int, float)) else 'USD: -'
                eur_txt = f'EUR: {eur:.4f}' if isinstance(eur, (int, float)) else 'EUR: -'
                with ui.element('q-chip').props('dense color="blue-1" text-color="blue-10" icon="attach_money"'):
                    ui.label(usd_txt).classes('text-caption text-weight-medium')
                with ui.element('q-chip').props('dense color="amber-1" text-color="amber-10" icon="euro"'):
                    ui.label(eur_txt).classes('text-caption text-weight-medium')
                donem_secici(_on_donem, include_all=True)

        def _tick():
            if clock_label['el']:
                clock_label['el'].set_text(f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

        ui.timer(1.0, _tick)

        dash_content()
