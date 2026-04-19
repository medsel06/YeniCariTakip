"""ALSE Plastik Hammadde - Raporlar Sayfası"""
from nicegui import ui
from layout import create_layout, notify_ok, notify_err
from services.cari_service import get_firma_list, get_cari_ekstre, get_alacak_yaslandirma
from services.stok_service import get_stok_list
from services.kasa_service import get_kasa_list, get_kasa_bakiye
from services.cek_service import list_cekler
from services.pdf_service import (
    generate_cari_ekstre_pdf, generate_stok_raporu_pdf,
    generate_kasa_raporu_pdf, generate_cek_raporu_pdf, save_pdf_preview
)


@ui.page('/raporlar')
def raporlar_page():
    if not create_layout(active_path='/raporlar', page_title='Raporlar'):
        return

    def _open_pdf(pdf_bytes, filename: str):
        preview_url = save_pdf_preview(pdf_bytes, filename)
        ui.run_javascript(f"window.open('{preview_url}', '_blank')")

    with ui.column().classes('w-full q-pa-sm'):
        with ui.grid(columns='repeat(2, 1fr)').classes('w-full gap-2'):

            # --- 1. Cari Ekstre PDF ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('people').classes('text-blue-7').style('font-size: 2rem')
                    ui.label('Cari Ekstre Raporu').classes('text-h6 q-ml-sm')

                ui.label('Firma seçip cari ekstre PDF indirin.').classes('text-body2 text-grey-7 q-mb-md')

                firmalar = get_firma_list()
                firma_options = {f['kod']: f"{f['kod']} - {f['ad']}" for f in firmalar}
                firma_select = ui.select(
                    options=firma_options, label='Firma Seçin', with_input=True
                ).classes('w-full q-mb-md').props('outlined dense')

                async def download_cari_ekstre():
                    if not firma_select.value:
                        notify_err('Lütfen bir firma seçin')
                        return
                    ui.notify('PDF hazirlanıyor...', type='info', position='top', timeout=2000)
                    try:
                        firma_kod = firma_select.value
                        firma = next((f for f in firmalar if f['kod'] == firma_kod), None)
                        firma_ad = firma['ad'] if firma else firma_kod
                        ekstre = get_cari_ekstre(firma_kod)
                        if not ekstre:
                            notify_err('Bu firmaya ait ekstre bulunamadı')
                            return
                        pdf_bytes = generate_cari_ekstre_pdf(firma_ad, ekstre)
                        _open_pdf(pdf_bytes, f'cari_ekstre_{firma_kod}.pdf')
                        notify_ok('PDF indiriliyor')
                    except Exception as e:
                        notify_err(f'PDF olusturma hatasi: {e}')

                ui.button('PDF İndir', icon='download', color='primary',
                          on_click=download_cari_ekstre).classes('w-full')

            # --- 2. Stok Raporu PDF ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('inventory_2').classes('text-green-7').style('font-size: 2rem')
                    ui.label('Stok Raporu').classes('text-h6 q-ml-sm')

                ui.label('Tüm ürünlerin stok durumunu PDF olarak indirin.').classes(
                    'text-body2 text-grey-7 q-mb-md')

                async def download_stok():
                    ui.notify('PDF hazirlanıyor...', type='info', position='top', timeout=2000)
                    try:
                        data = get_stok_list()
                        if not data:
                            notify_err('Stok verisi bulunamadı')
                            return
                        pdf_bytes = generate_stok_raporu_pdf(data)
                        _open_pdf(pdf_bytes, 'stok_raporu.pdf')
                        notify_ok('PDF indiriliyor')
                    except Exception as e:
                        notify_err(f'PDF olusturma hatasi: {e}')

                ui.button('PDF İndir', icon='download', color='primary',
                          on_click=download_stok).classes('w-full')

            # --- 3. Kasa Raporu PDF ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('account_balance_wallet').classes('text-teal-7').style('font-size: 2rem')
                    ui.label('Kasa Raporu').classes('text-h6 q-ml-sm')

                ui.label('Kasa hareketleri ve bakiye raporunu PDF olarak indirin.').classes(
                    'text-body2 text-grey-7 q-mb-md')

                async def download_kasa():
                    ui.notify('PDF hazirlanıyor...', type='info', position='top', timeout=2000)
                    try:
                        kasa_data = get_kasa_list()
                        bakiye_info = get_kasa_bakiye()
                        if not kasa_data:
                            notify_err('Kasa verisi bulunamadı')
                            return
                        pdf_bytes = generate_kasa_raporu_pdf(kasa_data, bakiye_info)
                        _open_pdf(pdf_bytes, 'kasa_raporu.pdf')
                        notify_ok('PDF indiriliyor')
                    except Exception as e:
                        notify_err(f'PDF olusturma hatasi: {e}')

                ui.button('PDF İndir', icon='download', color='primary',
                          on_click=download_kasa).classes('w-full')

            # --- 4. Cek Portfoy Raporu PDF ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('receipt_long').classes('text-orange-7').style('font-size: 2rem')
                    ui.label('Çek Portföy Raporu').classes('text-h6 q-ml-sm')

                ui.label('Tüm çeklerin portföy raporunu PDF olarak indirin.').classes(
                    'text-body2 text-grey-7 q-mb-md')

                async def download_cek():
                    ui.notify('PDF hazirlanıyor...', type='info', position='top', timeout=2000)
                    try:
                        cek_data = list_cekler()
                        if not cek_data:
                            notify_err('Çek verisi bulunamadı')
                            return
                        pdf_bytes = generate_cek_raporu_pdf(cek_data)
                        _open_pdf(pdf_bytes, 'cek_portfoy_raporu.pdf')
                        notify_ok('PDF indiriliyor')
                    except Exception as e:
                        notify_err(f'PDF olusturma hatasi: {e}')

                ui.button('PDF İndir', icon='download', color='primary',
                          on_click=download_cek).classes('w-full')

            # --- 5. Alacak Yaslandirma Raporu ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('schedule').classes('text-red-7').style('font-size: 2rem')
                    ui.label('Alacak Yaşlandırma').classes('text-h6 q-ml-sm')

                ui.label('Firma bazlı 30/60/90 gün alacak yaşlandırma raporu.').classes(
                    'text-body2 text-grey-7 q-mb-md')

                async def download_yaslandirma():
                    ui.notify('PDF hazirlanıyor...', type='info', position='top', timeout=2000)
                    try:
                        data = get_alacak_yaslandirma()
                        if not data:
                            notify_err('Alacak verisi bulunamadı')
                            return
                        from services.pdf_service import generate_table_pdf
                        headers = ['Firma', '0-30 Gün', '31-60 Gün', '61-90 Gün', '90+ Gün', 'Toplam', 'Risk %']
                        pdf_rows = []
                        for r in data:
                            pdf_rows.append([
                                r['ad'],
                                r['b_0_30'], r['b_31_60'], r['b_61_90'], r['b_90_plus'],
                                r['toplam'],
                                f"%{r['risk_yuzdesi']}" if r['risk_yuzdesi'] > 0 else '-',
                            ])
                        pdf_bytes = generate_table_pdf('Alacak Yaşlandırma Raporu', headers, pdf_rows)
                        _open_pdf(pdf_bytes, 'alacak_yaslandirma.pdf')
                        notify_ok('PDF indiriliyor')
                    except Exception as e:
                        notify_err(f'PDF olusturma hatasi: {e}')

                async def show_yaslandirma_table():
                    data = get_alacak_yaslandirma()
                    if not data:
                        notify_err('Alacak verisi bulunamadı')
                        return
                    with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 95vw; max-width: 900px'):
                        with ui.element('div').classes('alse-dialog-header'):
                            ui.icon('schedule')
                            ui.label('Alacak Yaşlandırma').classes('dialog-title')
                        with ui.column().classes('w-full q-pa-sm'):
                            from layout import fmt_para, PARA_SLOT
                            toplam = sum(r['toplam'] for r in data)
                            vadesi_gecmis = sum(r['b_31_60'] + r['b_61_90'] + r['b_90_plus'] for r in data)
                            with ui.row().classes('w-full gap-2 q-mb-sm'):
                                with ui.element('q-chip').props('dense color="blue-1" text-color="blue-10"'):
                                    ui.label(f'Toplam Alacak: {fmt_para(toplam)} TL')
                                with ui.element('q-chip').props('dense color="red-1" text-color="red-10"'):
                                    ui.label(f'Vadesi Geçmiş (30+): {fmt_para(vadesi_gecmis)} TL')

                            yas_cols = [
                                {'name': 'ad', 'label': 'Firma', 'field': 'ad', 'align': 'left', 'sortable': True},
                                {'name': 'b_0_30', 'label': '0-30 Gün', 'field': 'b_0_30', 'align': 'right', 'sortable': True},
                                {'name': 'b_31_60', 'label': '31-60 Gün', 'field': 'b_31_60', 'align': 'right', 'sortable': True},
                                {'name': 'b_61_90', 'label': '61-90 Gün', 'field': 'b_61_90', 'align': 'right', 'sortable': True},
                                {'name': 'b_90_plus', 'label': '90+ Gün', 'field': 'b_90_plus', 'align': 'right', 'sortable': True},
                                {'name': 'toplam', 'label': 'Toplam', 'field': 'toplam', 'align': 'right', 'sortable': True},
                                {'name': 'risk_yuzdesi', 'label': 'Risk %', 'field': 'risk_yuzdesi', 'align': 'center', 'sortable': True},
                            ]
                            yt = ui.table(columns=yas_cols, rows=data, row_key='kod',
                                         pagination={'rowsPerPage': 50, 'sortBy': 'toplam', 'descending': True}).classes('w-full')
                            yt.props('flat bordered dense')
                            for col in ['b_0_30', 'b_31_60', 'b_61_90', 'b_90_plus', 'toplam']:
                                yt.add_slot(f'body-cell-{col}', PARA_SLOT)
                            yt.add_slot('body-cell-risk_yuzdesi', r'''
                                <q-td :props="props">
                                    <q-badge dense text-color="white"
                                        :color="props.value > 100 ? 'red-7' : props.value >= 80 ? 'orange-7' : props.value > 0 ? 'green-7' : 'grey-5'">
                                        {{ props.value > 0 ? props.value.toFixed(1) + '%' : '-' }}
                                    </q-badge>
                                </q-td>
                            ''')
                        with ui.row().classes('w-full justify-end q-pa-sm'):
                            ui.button('Kapat', on_click=dlg.close).props('flat color=grey')
                    dlg.open()

                with ui.row().classes('w-full gap-2'):
                    ui.button('Görüntüle', icon='visibility', color='secondary',
                              on_click=show_yaslandirma_table).classes('flex-1')
                    ui.button('PDF İndir', icon='download', color='primary',
                              on_click=download_yaslandirma).classes('flex-1')

            # --- 6. KDV Beyanname Özeti ---
            with ui.card().classes('q-pa-md'):
                with ui.row().classes('items-center q-mb-md'):
                    ui.icon('receipt').classes('text-purple-7').style('font-size: 2rem')
                    ui.label('KDV Beyanname Özeti').classes('text-h6 q-ml-sm')
                ui.label('Aylık KDV hesaplama özeti.').classes('text-body2 text-grey-7 q-mb-sm')

                # Month/year selector
                from datetime import datetime as _dt
                _now = _dt.now()
                _ay_opts = {m: name for m, name in [(1,'Ocak'),(2,'Şubat'),(3,'Mart'),(4,'Nisan'),(5,'Mayıs'),(6,'Haziran'),(7,'Temmuz'),(8,'Ağustos'),(9,'Eylül'),(10,'Ekim'),(11,'Kasım'),(12,'Aralık')]}
                kdv_ay = ui.select(options=_ay_opts, value=_now.month, label='Ay').props('outlined dense').classes('w-32')
                kdv_yil = ui.select(options={y: str(y) for y in range(_now.year-2, _now.year+2)}, value=_now.year, label='Yıl').props('outlined dense').classes('w-28')

                async def show_kdv():
                    from services.kdv_service import get_kdv_ozet
                    from layout import fmt_para
                    data = get_kdv_ozet(kdv_yil.value, kdv_ay.value)
                    with ui.dialog() as dlg, ui.card().classes('alse-dialog').style('width: 90vw; max-width: 500px'):
                        with ui.element('div').classes('alse-dialog-header').style('background: linear-gradient(135deg, #6A1B9A 0%, #8E24AA 100%)'):
                            ui.icon('receipt')
                            ui.label('KDV Beyanname Özeti').classes('dialog-title')
                        with ui.column().classes('w-full q-pa-md gap-sm'):
                            for label, val, color in [
                                ('Satış Matrahı', data['satis_matrah'], 'blue-7'),
                                ('Hesaplanan KDV', data['satis_kdv'], 'blue-9'),
                                ('Alış Matrahı', data['alis_matrah'], 'green-7'),
                                ('İndirilecek KDV', data['alis_kdv'], 'green-9'),
                                ('Tevkifat', data['tevkifat'], 'orange-7'),
                            ]:
                                with ui.row().classes('w-full items-center justify-between'):
                                    ui.label(label).classes(f'text-{color} text-weight-medium')
                                    ui.label(f'{fmt_para(val)} TL').classes('text-weight-bold')
                            ui.separator()
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label('Ödenecek KDV').classes('text-h6 text-weight-bold')
                                color = 'text-negative' if data['odenecek_kdv'] > 0 else 'text-positive'
                                ui.label(f'{fmt_para(data["odenecek_kdv"])} TL').classes(f'text-h6 text-weight-bold {color}')
                        with ui.row().classes('w-full justify-end q-pa-sm'):
                            ui.button('Kapat', on_click=dlg.close).props('flat color=grey')
                    dlg.open()

                ui.button('Hesapla', icon='calculate', color='purple-7', on_click=show_kdv).classes('w-full q-mt-sm')

