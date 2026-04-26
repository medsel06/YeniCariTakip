"""ALSE Plastik Hammadde - Muhasebe Takip Sistemi"""
import os
import sys
import json
import subprocess
import shutil
import threading
import time
import urllib.request
import socket
from nicegui import ui, app
import nicegui.run as nicegui_run
from db import init_db, get_db, BASE_DIR
from services.auth_service import ensure_default_admin
from services.pdf_service import get_pdf_preview_dir

# Sayfa modullerini import et (bu @ui.page decorator'larini register eder)
import pages.dashboard  # / -> eski Quasar dashboard
import pages.cari
import pages.firma_master
import pages.cari_detay
import pages.hareketler
import pages.stok
import pages.stok_detay
import pages.kasa
import pages.cekler
import pages.uretim
import pages.raporlar
import pages.ayarlar
import pages.login
import pages.loglar
import pages.mutabakat
import pages.cek_takvim
import pages.tahsilat_oneri
import pages.karlilik
import pages.gelir_gider
import pages.personel
import pages.haftalik_bilanco

# v3 (Trend) frontend için JSON API endpoint'leri
import services.api_routes  # noqa: F401


_orig_run_setup = nicegui_run.setup


def _safe_run_setup():
    try:
        _orig_run_setup()
    except PermissionError:
        # Sandbox ortamlarda ProcessPool olusturma yetkisi engellenebiliyor.
        # CPU-bound pool yoksa uygulama yine calisir.
        nicegui_run.process_pool = None


nicegui_run.setup = _safe_run_setup


class _NullStream:
    """Console olmayan modda uvicorn logging'in bekledigi stream arabirimi."""
    def write(self, *_args, **_kwargs):
        return 0

    def flush(self):
        return None

    def isatty(self):
        return False


def startup():
    """Uygulama baslarken calis"""
    init_db()
    ensure_default_admin()

    # Varsayilan tenant schema'sini set et (SADECE data.json yukleme icin)
    from db import get_all_tenants, set_tenant_schema, init_tenant_schema
    tenants = get_all_tenants()
    if not tenants:
        return
    ilk_tenant = tenants[0]
    set_tenant_schema(ilk_tenant['schema_name'])

    # DB bossa ve data.json varsa otomatik yukle (sadece ilk tenant'a)
    with get_db() as conn:
        count = conn.execute('SELECT COUNT(*) FROM urunler').fetchone()[0]
        if count == 0:
            data_file = os.path.join(BASE_DIR, 'data.json')
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if d.get('products'):
                    for p in d['products']:
                        conn.execute(
                            'INSERT INTO urunler (kod,ad,kategori,birim) VALUES(?,?,?,?) ON CONFLICT (kod) DO NOTHING',
                            (p['kod'], p['ad'], p.get('kategori', ''), p.get('birim', 'KG'))
                        )
                if d.get('firms'):
                    for firm in d['firms']:
                        conn.execute(
                            'INSERT INTO firmalar (kod,ad,tel,adres) VALUES(?,?,?,?) ON CONFLICT (kod) DO NOTHING',
                            (firm['kod'], firm['ad'], firm.get('tel', ''), firm.get('adres', ''))
                        )
                if d.get('transactions'):
                    for t in d['transactions']:
                        conn.execute(
                            '''INSERT INTO hareketler
                                (tarih,firma_kod,firma_ad,tur,urun_kod,urun_ad,miktar,birim_fiyat,toplam,kdv_orani,kdv_tutar,kdvli_toplam)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (t.get('tarih'), t['firmaKod'], t['firmaAd'], t['tur'],
                             t['urunKod'], t['urunAd'], t['miktar'], t['birimFiyat'],
                             t['toplam'], t.get('kdvOrani', 0), t.get('kdvTutar', 0),
                             t.get('kdvliToplam', t['toplam']))
                        )
                if d.get('kasa'):
                    for k in d['kasa']:
                        conn.execute(
                            'INSERT INTO kasa (tarih,firma_kod,firma_ad,tur,tutar,odeme_sekli,aciklama) VALUES(?,?,?,?,?,?,?)',
                            (k.get('tarih'), k['firmaKod'], k['firmaAd'], k['tur'],
                             k['tutar'], k.get('odemeSekli', ''), k.get('aciklama', ''))
                        )
                if d.get('cekler'):
                    for c in d['cekler']:
                        conn.execute(
                            'INSERT INTO cekler (cek_no,firma_kod,firma_ad,kesim_tarih,vade_tarih,tutar,tur,durum) VALUES(?,?,?,?,?,?,?,?)',
                            (c.get('no', ''), c.get('firmaKod', ''), c['firmaAd'],
                             c.get('kesimTarih'), c.get('vadeTarih'), c['tutar'],
                             c.get('tur', ''), c.get('durum', 'PORTFOYDE'))
                        )
                print("[CariTakip] Mevcut veriler yuklendi")

    # Startup bittikten sonra contextvars temizle
    # (browser session'lari kendi tenant'ini kullanmali)
    set_tenant_schema(None)


# startup() main blokta dogrudan cagirilir, on_startup gereksiz
pdf_preview_dir = str(get_pdf_preview_dir())
app.add_static_files('/pdf-preview', pdf_preview_dir)
assets_dir = os.path.join(BASE_DIR, 'assets')
if os.path.isdir(assets_dir):
    app.add_static_files('/assets', assets_dir)
    ui.add_head_html('<link rel="icon" type="image/x-icon" href="/assets/logo/favicon.ico?v=2">', shared=True)

# Yeni v3 (Trend) tasarimi - statik HTML olarak servis edilir
# Erisim: http://<host>:8080/v3/  veya http://<host>:8080/v3/Cari%20Takip%20v3%20(Trend).html
yeni_tasarim_dir = os.path.join(BASE_DIR, 'yeni-tasarim')
if os.path.isdir(yeni_tasarim_dir):
    app.add_static_files('/v3', yeni_tasarim_dir)


# /yeni: v3 (Trend) tasarımına yönlendir
# / -> eski Quasar dashboard (geriye uyumluluk)
# /yeni -> yeni v3 tasarımı
@ui.page('/yeni')
def yeni_redirect():
    if not app.storage.user.get('auth_user') or not app.storage.user.get('tenant_schema'):
        ui.navigate.to('/login')
        return
    ui.add_body_html('<script>window.location.href="/v3/Cari%20Takip%20v3%20(Trend).html";</script>')
    ui.label('Yönlendiriliyor...')


def _launch_chrome_app_mode():
    """Windows'ta Chrome'u app mode ile ac (sekmesiz, adres cubugu olmadan)."""
    if os.name != 'nt':
        return
    candidates = [
        os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LocalAppData', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
    ]
    chrome_exe = next((p for p in candidates if p and os.path.exists(p)), None)
    if not chrome_exe:
        chrome_exe = shutil.which('chrome.exe') or shutil.which('chrome')
    if not chrome_exe:
        return

    try:
        subprocess.Popen(
            [
                chrome_exe,
                '--app=http://localhost:8080',
                '--new-window',
                '--start-maximized',
                '--disable-extensions',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _is_server_alive(timeout: float = 0.5) -> bool:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/login', timeout=timeout) as resp:
            return 200 <= getattr(resp, 'status', 0) < 500
    except Exception:
        return False


def _wait_server(max_wait_sec: float = 20.0) -> bool:
    end = time.time() + max_wait_sec
    while time.time() < end:
        if _is_server_alive(0.5):
            return True
        time.sleep(0.25)
    return False


def _can_bind_port_8080() -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', 8080))
        return True
    except OSError:
        return False
    finally:
        s.close()


if __name__ in {"__main__", "__mp_main__"}:
    app_mode = os.getenv('ALSE_CHROME_APP_MODE', '0') == '1' or bool(getattr(sys, 'frozen', False))
    if getattr(sys, 'frozen', False):
        if sys.stdout is None:
            sys.stdout = _NullStream()
        if sys.stderr is None:
            sys.stderr = _NullStream()

    # Baska bir instance zaten calisiyorsa:
    # Yeni server baslatmak yerine sadece pencereyi yeniden acip cik.
    if app_mode and (not _can_bind_port_8080() or _is_server_alive(0.25)):
        _wait_server(8.0)
        _launch_chrome_app_mode()
        sys.exit(0)

    print("[ALSE] Muhasebe Takip Sistemi baslatiliyor...")
    print("[ALSE] Tarayici aciliyor: http://localhost:8080")

    # DB'yi server baslamadan ONCE garanti olarak kur
    # (on_startup event'i --noconsole EXE'de sessizce hata verebiliyor)
    try:
        startup()
    except Exception as _e:
        try:
            log_file = os.path.join(BASE_DIR, 'startup_error.log')
            with open(log_file, 'a', encoding='utf-8') as lf:
                import traceback
                lf.write(f'\n[{time.strftime("%Y-%m-%d %H:%M:%S")}] STARTUP ERROR:\n')
                lf.write(traceback.format_exc())
        except Exception:
            pass

    if app_mode:
        def _open_when_ready():
            _wait_server(25.0)
            _launch_chrome_app_mode()
        threading.Thread(target=_open_when_ready, daemon=True).start()
    ui.run(
        title='Cari Takip',
        port=int(os.environ.get('APP_PORT', '8080')),
        reload=False,
        show=not app_mode,
        log_config=None if getattr(sys, 'frozen', False) else None,
        storage_secret='cari_takip_storage_secret_2026',
    )

