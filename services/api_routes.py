"""
v3 (Trend) frontend için JSON API endpoint'leri.
NiceGUI'nin altındaki FastAPI üzerine eklenmiş REST API.

Kullanım: main.py içinde `import services.api_routes` ile register edilir.

Auth: NiceGUI `app.storage.user` session cookie'si ile.
Tenant: Her request başında `set_tenant_schema()` ile tenant context ayarlanır.
"""
from datetime import datetime, date
from decimal import Decimal
from functools import wraps
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from nicegui import app

from db import set_tenant_schema, get_tenant_schema
from services import (
    cari_service,
    stok_service,
    kasa_service,
    cek_service,
    gelir_gider_service,
    personel_service,
    mutabakat_service,
    oneri_service,
    settings_service,
    fx_service,
    audit_service,
)


# ============= JSON SERIALIZE HELPER =============

def _to_json_safe(obj):
    """datetime/date/Decimal -> JSON serializable."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _json(data, status=200):
    return JSONResponse(_to_json_safe(data), status_code=status)


# ============= AUTH + TENANT DECORATOR =============

def _get_user_and_tenant(request: Request):
    """NiceGUI session'dan user + tenant_schema çek.
    Önce app.storage.user'i dene, çalışmazsa cookie'den oku.
    """
    try:
        user = app.storage.user.get('auth_user')
        tenant = app.storage.user.get('tenant_schema')
        if user and tenant:
            return user, tenant
    except Exception:
        pass
    return None, None


def api_auth(handler):
    """Login zorunlu + tenant context ayarla."""
    @wraps(handler)
    async def wrapper(request: Request, *args, **kwargs):
        user, tenant = _get_user_and_tenant(request)
        if not user or not tenant:
            return _json({'error': 'unauthorized', 'message': 'Giriş yapılmamış'}, status=401)
        set_tenant_schema(tenant)
        try:
            return await handler(request, *args, **kwargs)
        except Exception as e:
            return _json({'error': 'server_error', 'message': str(e)}, status=500)
        finally:
            set_tenant_schema(None)
    return wrapper


# ============= ME / SESSION =============

@app.get('/api/me')
async def api_me(request: Request):
    """Aktif oturum bilgisi. Login yoksa 401."""
    user, tenant = _get_user_and_tenant(request)
    if not user:
        return _json({'authenticated': False}, status=401)
    return _json({
        'authenticated': True,
        'user': {
            'id': user.get('id'),
            'username': user.get('username'),
            'full_name': user.get('full_name'),
            'role': user.get('role'),
        },
        'tenant': {
            'schema': tenant,
            'name': app.storage.user.get('tenant_name'),
        }
    })


# ============= CARILER =============

@app.get('/api/cariler')
@api_auth
async def api_cariler(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    """Cari hesap listesi (devir/alış/satış/ödeme/tahsilat/bakiye sütunları)."""
    return _json(cari_service.get_cari_bakiye_list(yil=yil, ay=ay))


@app.get('/api/cariler/master')
@api_auth
async def api_cariler_master(request: Request):
    """Detaylı firma master listesi (NACE, iş alanı, risk limiti dahil)."""
    return _json(cari_service.get_firma_master_list())


@app.get('/api/cariler/{kod}')
@api_auth
async def api_cari_detay(request: Request, kod: str):
    """Tek cari detayı."""
    firma = cari_service.get_firma(kod)
    if not firma:
        return _json({'error': 'not_found'}, status=404)
    return _json(firma)


@app.get('/api/cariler/{kod}/ekstre')
@api_auth
async def api_cari_ekstre(request: Request, kod: str, yil: Optional[int] = None, ay: Optional[int] = None):
    """Cari ekstresi (tarih, tip, tutar, bakiye)."""
    return _json(cari_service.get_cari_ekstre(kod, yil=yil, ay=ay))


@app.get('/api/cariler/{kod}/hareketler')
@api_auth
async def api_cari_hareketler(request: Request, kod: str):
    """Cari için alış/satış hareketleri."""
    return _json(cari_service.get_firma_hareketler(kod))


@app.get('/api/cariler/{kod}/kasa')
@api_auth
async def api_cari_kasa(request: Request, kod: str):
    """Cari için kasa hareketleri."""
    return _json(cari_service.get_firma_kasa(kod))


@app.get('/api/cariler/{kod}/cekler')
@api_auth
async def api_cari_cekler(request: Request, kod: str):
    """Cari için çek/senet."""
    return _json(cari_service.get_firma_cekler(kod))


@app.get('/api/cariler/{kod}/risk')
@api_auth
async def api_cari_risk(request: Request, kod: str):
    """Cari risk durumu (limit kullanımı)."""
    return _json(cari_service.get_firma_risk_durumu(kod))


# ============= HAREKETLER (Alış/Satış) =============

@app.get('/api/hareketler')
@api_auth
async def api_hareketler(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    """Stok hareketleri (alış/satış kayıtları)."""
    return _json(kasa_service.get_hareketler(yil=yil, ay=ay))


# ============= STOK =============

@app.get('/api/stok')
@api_auth
async def api_stok(request: Request):
    """Stok listesi (alış/satış/üretim girdi/çıktı/net)."""
    return _json(stok_service.get_stok_list())


@app.get('/api/stok/urunler')
@api_auth
async def api_urun_list(request: Request):
    """Sade ürün listesi (kod, ad, kategori, birim, desi)."""
    return _json(stok_service.get_urun_list())


@app.get('/api/stok/kategoriler')
@api_auth
async def api_kategoriler(request: Request):
    return _json(stok_service.get_kategori_list())


@app.get('/api/stok/{kod}')
@api_auth
async def api_stok_detay(request: Request, kod: str):
    """Tek ürün stok durumu."""
    return _json(stok_service.get_urun_stok(kod))


@app.get('/api/stok/{kod}/hareketler')
@api_auth
async def api_stok_hareketler(request: Request, kod: str):
    return _json(stok_service.get_urun_hareketleri(kod))


@app.get('/api/stok/{kod}/uretim-hareketler')
@api_auth
async def api_stok_uretim_hareketler(request: Request, kod: str):
    return _json(stok_service.get_urun_uretim_hareketleri(kod))


# ============= KASA =============

@app.get('/api/kasa')
@api_auth
async def api_kasa(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    return _json(kasa_service.get_kasa_list(yil=yil, ay=ay))


@app.get('/api/kasa/bakiye')
@api_auth
async def api_kasa_bakiye(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    return _json(kasa_service.get_kasa_bakiye(yil=yil, ay=ay))


# ============= ÇEKLER =============

@app.get('/api/cekler')
@api_auth
async def api_cekler(request: Request, tur: Optional[str] = None):
    """Çek listesi. tur=ALINAN | VERILEN | None (hepsi)."""
    return _json(cek_service.list_cekler(cek_turu=tur))


@app.get('/api/cekler/portfoyde')
@api_auth
async def api_cekler_portfoyde(request: Request):
    """Portföydeki çekler (ciro için)."""
    return _json(cek_service.list_cekler_portfoyde())


@app.get('/api/cekler/vade-uyarilari')
@api_auth
async def api_cekler_vade(request: Request):
    """Çek takvimi: vadesi yaklaşan/geçmiş çekler."""
    return _json(cek_service.get_vade_uyarilari())


# ============= GELIR/GIDER =============

@app.get('/api/gelir-gider')
@api_auth
async def api_gelir_gider(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    return _json(gelir_gider_service.get_gelir_gider_list(yil=yil, ay=ay))


@app.get('/api/gelir-gider/ozet')
@api_auth
async def api_gelir_gider_ozet(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    return _json(gelir_gider_service.get_gelir_gider_ozet(yil=yil, ay=ay))


# ============= PERSONEL =============

@app.get('/api/personel')
@api_auth
async def api_personel(request: Request):
    return _json(personel_service.get_personel_list())


@app.get('/api/personel/dashboard')
@api_auth
async def api_personel_dashboard(request: Request):
    return _json(personel_service.get_personel_dashboard_ozet())


@app.get('/api/personel/aylik')
@api_auth
async def api_personel_aylik(request: Request, yil: int, ay: int):
    return _json(personel_service.get_aylik_ozet(yil, ay))


# ============= MUTABAKAT / TAHSILAT / KARLILIK =============

@app.get('/api/mutabakat')
@api_auth
async def api_mutabakat(request: Request):
    return _json(mutabakat_service.list_mutabakat())


@app.get('/api/tahsilat-onerileri')
@api_auth
async def api_tahsilat_onerileri(request: Request):
    return _json(oneri_service.get_tahsilat_onerileri())


@app.get('/api/karlilik')
@api_auth
async def api_karlilik(request: Request):
    return _json(oneri_service.get_urun_karlilik_ozeti())


# ============= DASHBOARD KPI =============

@app.get('/api/dashboard/kpi')
@api_auth
async def api_dashboard_kpi(request: Request):
    """Bilgi Ekranı için toplulaştırılmış KPI'lar."""
    today = date.today()
    yil, ay = today.year, today.month

    cariler = cari_service.get_cari_bakiye_list()
    toplam_alacak = sum(max(0, float(c.get('bakiye') or 0)) for c in cariler)
    toplam_borc = abs(sum(min(0, float(c.get('bakiye') or 0)) for c in cariler))
    aktif_cari = sum(1 for c in cariler if (c.get('aktif') or c.get('durum') in ('AKTIF', 'active')))

    kasa_bakiye = kasa_service.get_kasa_bakiye(yil=yil, ay=ay)
    bu_ay_tahsilat = float(kasa_bakiye.get('toplam_giris') or 0) if isinstance(kasa_bakiye, dict) else 0

    # Risk uyarıları
    risk = cari_service.get_risk_uyarilari()

    return _json({
        'toplam_alacak': toplam_alacak,
        'toplam_borc': toplam_borc,
        'aktif_cari': aktif_cari,
        'pasif_cari': len(cariler) - aktif_cari,
        'bu_ay_tahsilat': bu_ay_tahsilat,
        'risk_sayisi': len(risk),
        'risk_uyarilari': risk[:10],
    })


@app.get('/api/dashboard/fx')
@api_auth
async def api_fx(request: Request):
    """USD/EUR kurları."""
    try:
        return _json(fx_service.get_usd_eur_rates())
    except Exception:
        return _json({'usd': None, 'eur': None})


# ============= AYARLAR =============

@app.get('/api/settings')
@api_auth
async def api_settings(request: Request):
    return _json(settings_service.get_company_settings())


# ============= LOGLAR =============

@app.get('/api/logs')
@api_auth
async def api_logs(request: Request, action: Optional[str] = None, entity_type: Optional[str] = None, limit: int = 200):
    return _json(audit_service.list_logs_filtered(
        limit=limit,
        action=action,
        entity_type=entity_type,
    ))


# ============= POST: Yeni Kayıtlar =============

@app.post('/api/cariler')
@api_auth
async def api_cari_create(request: Request):
    data = await request.json()
    kod = cari_service.add_firma(data)
    return _json({'ok': True, 'kod': kod})


@app.post('/api/stok/urunler')
@api_auth
async def api_urun_create(request: Request):
    data = await request.json()
    kod = stok_service.add_urun(data)
    return _json({'ok': True, 'kod': kod})


@app.post('/api/hareketler')
@api_auth
async def api_hareket_create(request: Request):
    data = await request.json()
    new_id = kasa_service.add_hareket(data)
    return _json({'ok': True, 'id': new_id})


@app.post('/api/kasa')
@api_auth
async def api_kasa_create(request: Request):
    data = await request.json()
    new_id = kasa_service.add_kasa(data)
    return _json({'ok': True, 'id': new_id})


@app.post('/api/cekler')
@api_auth
async def api_cek_create(request: Request):
    data = await request.json()
    new_id = cek_service.add_cek(data)
    return _json({'ok': True, 'id': new_id})


@app.post('/api/gelir-gider')
@api_auth
async def api_gelir_gider_create(request: Request):
    data = await request.json()
    new_id = gelir_gider_service.add_gelir_gider(data)
    return _json({'ok': True, 'id': new_id})


@app.post('/api/personel')
@api_auth
async def api_personel_create(request: Request):
    data = await request.json()
    new_id = personel_service.add_personel(data)
    return _json({'ok': True, 'id': new_id})


@app.post('/api/mutabakat')
@api_auth
async def api_mutabakat_create(request: Request):
    data = await request.json()
    new_id = mutabakat_service.add_mutabakat(data)
    return _json({'ok': True, 'id': new_id})


print("[API] services.api_routes yüklendi - /api/* endpoint'leri aktif")
