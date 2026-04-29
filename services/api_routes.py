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
    """Cari ekstresi: {donem_label, devir, satirlar, donem_borc, donem_alacak, kapanis_bakiye}."""
    return _json(cari_service.get_cari_ekstre(kod, yil=yil, ay=ay, with_meta=True))


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
async def api_dashboard_kpi(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    """Bilgi Ekranı için toplulaştırılmış KPI'lar.
    yil/ay query param destekli: ?yil=2026&ay=4 (aylik) veya ?yil=2026 (yillik)."""
    cariler = cari_service.get_cari_bakiye_list(yil=yil, ay=ay)
    toplam_alacak = sum(max(0, float(c.get('bakiye') or 0)) for c in cariler)
    toplam_borc = abs(sum(min(0, float(c.get('bakiye') or 0)) for c in cariler))
    aktif_cari = sum(1 for c in cariler if (c.get('aktif') or c.get('durum') in ('AKTIF', 'active')))

    # Bu ay tahsilat: yil/ay belirtilmediyse mevcut ay (dashboard widget için)
    today = date.today()
    bu_ay_y = yil or today.year
    bu_ay_a = ay or today.month
    kasa_bakiye = kasa_service.get_kasa_bakiye(yil=bu_ay_y, ay=bu_ay_a)
    # NOT: kasa_service.get_kasa_bakiye() 'giris' key'i ile döner (toplam_giris değil)
    bu_ay_tahsilat = float(kasa_bakiye.get('giris') or 0) if isinstance(kasa_bakiye, dict) else 0

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


@app.get('/api/orphan-dates')
@api_auth
async def api_orphan_dates(request: Request):
    """Bos/NULL tarihli kayitlar — mali doneme dahil edilmeyen, duzeltilmesi gereken kayitlar."""
    return _json({
        'counts': cari_service.get_orphan_date_count(),
        'records': cari_service.get_orphan_date_records(),
    })


@app.get('/api/orphan-dates/count')
@api_auth
async def api_orphan_dates_count(request: Request):
    """Sadece sayilar (dashboard widget icin hizli)."""
    return _json(cari_service.get_orphan_date_count())


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
    """V3 KasaModal cek/ciro alanlarini destekler:
    - cek_turu='FIRMA' + odeme_sekli='Çek' -> yeni cek + kasa kaydi (cek_id ile)
    - cek_turu='CIRO' + ciro_cek_id -> sadece change_durum (CIRO_EDILDI), kasa yok
    - Diger: normal kasa kaydi
    """
    data = await request.json()

    # Tur normalize (V3 'GELIR'/'GIDER' beklenir, eger 'gelir'/'gider' geldiyse uppercase)
    if 'tur' in data and isinstance(data['tur'], str):
        data['tur'] = data['tur'].upper()

    odeme_sekli = data.get('odeme_sekli', '')
    cek_turu = data.get('cek_turu', '')

    # CIRO senaryosu: kasa kaydi olusmaz, sadece change_durum
    if cek_turu == 'CIRO' and data.get('ciro_cek_id'):
        ok, msg = cek_service.change_durum(
            int(data['ciro_cek_id']), 'CIRO_EDILDI',
            aciklama=data.get('aciklama', ''),
            ciro_firma_kod=data.get('firma_kod', ''),
            ciro_firma_ad=data.get('firma_ad', ''),
        )
        if not ok:
            return _json({'error': 'cek_ciro_failed', 'message': msg}, status=400)
        return _json({'ok': True, 'mode': 'ciro'})

    # Firma çeki senaryosu: yeni cek olustur, kasa kaydı bağla
    if cek_turu == 'FIRMA' and (odeme_sekli == 'Çek' or odeme_sekli == 'CEK'):
        cek_turu_db = 'ALINAN' if data.get('tur') == 'GELIR' else 'VERILEN'
        cek_id = cek_service.add_cek({
            'cek_no': data.get('cek_no', ''),
            'firma_kod': data.get('firma_kod', ''),
            'firma_ad': data.get('firma_ad', ''),
            'kesim_tarih': data.get('tarih', ''),
            'vade_tarih': data.get('cek_vade_tarih', ''),
            'tutar': data.get('tutar', 0),
            'cek_turu': cek_turu_db,
            'notlar': data.get('aciklama', ''),
            'tur': cek_turu_db,
            'evrak_tipi': data.get('evrak_tipi', 'CEK'),
        })
        data['cek_id'] = cek_id

    # Normal/cek_id'li kasa kaydı
    new_id = kasa_service.add_kasa({
        'tarih': data.get('tarih'),
        'firma_kod': data.get('firma_kod', ''),
        'firma_ad': data.get('firma_ad', ''),
        'tur': data.get('tur', 'GELIR'),
        'tutar': data.get('tutar', 0),
        'odeme_sekli': odeme_sekli,
        'aciklama': data.get('aciklama', ''),
        'cek_id': data.get('cek_id'),
    })
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
    """V3 'gelir'/'gider' lowercase gondereceginden tur ve odeme_durumu normalize edilir.
    Odendi durumunda otomatik kasa kaydi gelir_gider_service icinde olusturulur."""
    data = await request.json()
    if 'tur' in data and isinstance(data['tur'], str):
        data['tur'] = data['tur'].upper()
    if 'odeme_durumu' in data and isinstance(data['odeme_durumu'], str):
        data['odeme_durumu'] = data['odeme_durumu'].upper()
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


# ============= PUT (UPDATE) =============

@app.put('/api/cariler/{kod}')
@api_auth
async def api_cari_update(request: Request, kod: str):
    data = await request.json()
    cari_service.update_firma(kod, data)
    return _json({'ok': True})


@app.put('/api/stok/urunler/{kod}')
@api_auth
async def api_urun_update(request: Request, kod: str):
    data = await request.json()
    stok_service.update_urun(kod, data)
    return _json({'ok': True})


@app.put('/api/hareketler/{rec_id}')
@api_auth
async def api_hareket_update(request: Request, rec_id: int):
    data = await request.json()
    kasa_service.update_hareket(rec_id, data)
    return _json({'ok': True})


@app.put('/api/kasa/{rec_id}')
@api_auth
async def api_kasa_update(request: Request, rec_id: int):
    data = await request.json()
    kasa_service.update_kasa(rec_id, data)
    return _json({'ok': True})


@app.put('/api/cekler/{cek_id}')
@api_auth
async def api_cek_update(request: Request, cek_id: int):
    data = await request.json()
    cek_service.update_cek(cek_id, data)
    return _json({'ok': True})


@app.put('/api/cekler/{cek_id}/durum')
@api_auth
async def api_cek_durum(request: Request, cek_id: int):
    data = await request.json()
    cek_service.change_durum(
        cek_id, data.get('durum'),
        aciklama=data.get('aciklama', ''),
        ciro_firma_kod=data.get('ciro_firma_kod', ''),
        ciro_firma_ad=data.get('ciro_firma_ad', ''),
    )
    return _json({'ok': True})


@app.put('/api/gelir-gider/{rec_id}')
@api_auth
async def api_gg_update(request: Request, rec_id: int):
    data = await request.json()
    gelir_gider_service.update_gelir_gider(rec_id, data)
    return _json({'ok': True})


@app.put('/api/personel/{pid}')
@api_auth
async def api_personel_update(request: Request, pid: int):
    data = await request.json()
    personel_service.update_personel(pid, data)
    return _json({'ok': True})


@app.put('/api/settings')
@api_auth
async def api_settings_update(request: Request):
    data = await request.json()
    return _json({'ok': True, 'data': settings_service.update_company_settings(data)})


# ============= DELETE =============

@app.delete('/api/cariler/{kod}')
@api_auth
async def api_cari_delete(request: Request, kod: str):
    """Soft-delete: hareket varsa pasife al, yoksa sil. Mode: 'pasif' / 'silindi'."""
    sonuc = cari_service.delete_firma(kod)
    return _json({'ok': True, **(sonuc or {})})


@app.put('/api/cariler/{kod}/reactivate')
@api_auth
async def api_cari_reactivate(request: Request, kod: str):
    """Pasife alinmis firmayi tekrar aktif et."""
    cari_service.reactivate_firma(kod)
    return _json({'ok': True})


@app.delete('/api/stok/urunler/{kod}')
@api_auth
async def api_urun_delete(request: Request, kod: str):
    """Soft-delete: hareket varsa pasife al, yoksa sil."""
    sonuc = stok_service.delete_urun(kod)
    return _json({'ok': True, **(sonuc or {})})


@app.put('/api/stok/urunler/{kod}/reactivate')
@api_auth
async def api_urun_reactivate(request: Request, kod: str):
    stok_service.reactivate_urun(kod)
    return _json({'ok': True})


@app.delete('/api/hareketler/{rec_id}')
@api_auth
async def api_hareket_delete(request: Request, rec_id: int):
    kasa_service.delete_hareket(rec_id)
    return _json({'ok': True})


@app.delete('/api/kasa/{rec_id}')
@api_auth
async def api_kasa_delete(request: Request, rec_id: int):
    kasa_service.delete_kasa(rec_id)
    return _json({'ok': True})


@app.delete('/api/cekler/{cek_id}')
@api_auth
async def api_cek_delete(request: Request, cek_id: int):
    cek_service.delete_cek(cek_id)
    return _json({'ok': True})


@app.delete('/api/gelir-gider/{rec_id}')
@api_auth
async def api_gg_delete(request: Request, rec_id: int):
    gelir_gider_service.delete_gelir_gider(rec_id)
    return _json({'ok': True})


@app.delete('/api/personel/{pid}')
@api_auth
async def api_personel_delete(request: Request, pid: int):
    personel_service.delete_personel(pid)
    return _json({'ok': True})


# ============= PERSONEL MESAİ =============

@app.post('/api/personel/mesai')
@api_auth
async def api_personel_mesai_create(request: Request):
    data = await request.json()
    new_id = personel_service.add_hareket(data)
    return _json({'ok': True, 'id': new_id})


@app.delete('/api/personel/mesai/{hid}')
@api_auth
async def api_personel_mesai_delete(request: Request, hid: int):
    personel_service.delete_hareket(hid)
    return _json({'ok': True})


@app.get('/api/personel/{pid}/mesai')
@api_auth
async def api_personel_mesai_list(request: Request, pid: int, yil: int, ay: int, hafta: int = 0):
    return _json(personel_service.get_hareketler(pid, yil, ay, hafta))


# ============= ÇEK GET BY ID =============

@app.get('/api/cekler/{cek_id}/detay')
@api_auth
async def api_cek_detay(request: Request, cek_id: int):
    return _json(cek_service.get_cek_by_id(cek_id))


@app.get('/api/cekler/{cek_id}/hareketler')
@api_auth
async def api_cek_hareketler(request: Request, cek_id: int):
    return _json(cek_service.get_cek_hareketleri(cek_id))


# ============= KASA HAREKET BY ID =============

@app.get('/api/kasa/{rec_id}/detay')
@api_auth
async def api_kasa_detay(request: Request, rec_id: int):
    return _json(kasa_service.get_kasa_by_id(rec_id))


@app.get('/api/hareketler/{rec_id}/detay')
@api_auth
async def api_hareket_detay(request: Request, rec_id: int):
    return _json(kasa_service.get_hareket_by_id(rec_id))


# ============= USERS (Ayarlar) =============

@app.get('/api/users')
@api_auth
async def api_users(request: Request):
    from services import auth_service
    return _json(auth_service.list_users())


@app.post('/api/users')
@api_auth
async def api_user_create(request: Request):
    from services import auth_service
    data = await request.json()
    new_id = auth_service.add_user(data)
    return _json({'ok': True, 'id': new_id})


@app.put('/api/users/{uid}')
@api_auth
async def api_user_update(request: Request, uid: int):
    from services import auth_service
    data = await request.json()
    auth_service.update_user(uid, data)
    return _json({'ok': True})


@app.put('/api/users/{uid}/password')
@api_auth
async def api_user_password(request: Request, uid: int):
    from services import auth_service
    data = await request.json()
    auth_service.set_user_password(uid, data.get('password', ''))
    return _json({'ok': True})


@app.delete('/api/users/{uid}')
@api_auth
async def api_user_delete(request: Request, uid: int):
    from services import auth_service
    auth_service.delete_user(uid)
    return _json({'ok': True})


# ============= BACKUP =============

@app.get('/api/backups')
@api_auth
async def api_backups(request: Request):
    from services import backup_service
    return _json(backup_service.list_backups())


@app.post('/api/backups')
@api_auth
async def api_backup_create(request: Request):
    from services import backup_service
    path = backup_service.create_backup()
    return _json({'ok': True, 'path': str(path)})


# ============= LOGOUT =============

@app.post('/api/logout')
async def api_logout(request: Request):
    try:
        app.storage.user.clear()
    except Exception:
        pass
    return _json({'ok': True})


# ============= PDF EXPORT (V3 frontend) =============

@app.get('/api/export/cari-ekstre/{kod}')
@api_auth
async def api_export_cari_ekstre(request: Request, kod: str, yil: Optional[int] = None, ay: Optional[int] = None):
    """Cari ekstre PDF indirme. WeasyPrint varsa modern v3, yoksa reportlab."""
    from fastapi.responses import Response
    from services.pdf_service import generate_cari_ekstre_pdf

    firma = cari_service.get_firma(kod)
    if not firma:
        return _json({'error': 'not_found'}, status=404)
    firma_ad = firma.get('ad') or firma.get('firma_adi') or kod

    ekstre = cari_service.get_cari_ekstre(kod, yil=yil, ay=ay, with_meta=True)
    pdf_bytes = generate_cari_ekstre_pdf(firma_ad, ekstre, firma=firma)

    filename = f"cari_ekstre_{kod}.pdf"
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@app.get('/api/export/stok-raporu')
@api_auth
async def api_export_stok_raporu(request: Request):
    """Stok durum raporu PDF."""
    from fastapi.responses import Response
    from services.pdf_service import generate_stok_raporu_pdf

    stok_data = stok_service.get_stok_list()
    pdf_bytes = generate_stok_raporu_pdf(stok_data)

    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="stok_raporu.pdf"'},
    )


@app.get('/api/export/gelir-gider')
@api_auth
async def api_export_gelir_gider(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    """Gelir/Gider rapor PDF."""
    from fastapi.responses import Response
    from services.pdf_service import generate_gelir_gider_pdf

    gg_data = gelir_gider_service.get_gelir_gider_list(yil=yil, ay=ay)
    # Dönem etiketi oluştur
    if yil and ay:
        import calendar
        ay_adi = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'][ay]
        donem_label = f'{ay_adi} {yil}'
    elif yil:
        donem_label = f'{yil} Yılı'
    else:
        donem_label = 'Tüm Zamanlar'

    pdf_bytes = generate_gelir_gider_pdf(gg_data, donem_label=donem_label)

    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="gelir_gider_raporu.pdf"'},
    )


@app.get('/api/export/kasa-raporu')
@api_auth
async def api_export_kasa_raporu(request: Request, yil: Optional[int] = None, ay: Optional[int] = None):
    """Kasa raporu PDF."""
    from fastapi.responses import Response
    from services.pdf_service import generate_kasa_raporu_pdf

    kasa_data = kasa_service.get_kasa_list(yil=yil, ay=ay)
    bakiye_info = kasa_service.get_kasa_bakiye(yil=yil, ay=ay)
    pdf_bytes = generate_kasa_raporu_pdf(kasa_data, bakiye_info)

    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="kasa_raporu.pdf"'},
    )


@app.get('/api/export/cek-raporu')
@api_auth
async def api_export_cek_raporu(request: Request, tur: Optional[str] = None):
    """Çek portföy raporu PDF."""
    from fastapi.responses import Response
    from services.pdf_service import generate_cek_raporu_pdf

    cek_data = cek_service.list_cekler(cek_turu=tur)
    pdf_bytes = generate_cek_raporu_pdf(cek_data)

    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename="cek_portfoy_raporu.pdf"'},
    )


print("[API] services.api_routes yüklendi - /api/* endpoint'leri aktif (GET+POST+PUT+DELETE+EXPORT)")
