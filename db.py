"""
Cari Takip - Veritabani Katmani (PostgreSQL, Multi-Tenant Schema)
Her firma icin ayri PostgreSQL schema kullanilir.
public schema: tenants + users (ortak)
t_X schema: firmalar, hareketler, kasa vb. (firma bazli)
"""
import os
import sys
import contextvars
from contextlib import contextmanager
from datetime import datetime

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env dosyasindan oku (varsa)
_env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'cari_takip'),
    'user': os.environ.get('DB_USER', 'cari_takip'),
    'password': os.environ.get('DB_PASSWORD', 'CariTakip2026!'),
}

# --- CONNECTION POOL ---
_pool = None


def _get_pool():
    """Lazy-init connection pool. Thread-safe."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2, maxconn=20, **DB_CONFIG
        )
    return _pool


# --- TENANT CONTEXT (contextvars) ---
_current_tenant_schema = contextvars.ContextVar('tenant_schema', default=None)


def set_tenant_schema(schema):
    """Mevcut request/thread icin tenant schema'sini ayarla."""
    _current_tenant_schema.set(schema)


def get_tenant_schema():
    """Mevcut tenant schema adini dondur."""
    return _current_tenant_schema.get()


# --- ROW / CURSOR / CONN WRAPPER ---

class _DictRow(dict):
    """sqlite3.Row uyumlu dict - hem key hem index erisimi destekler.
    PostgreSQL Decimal -> float otomatik donusumu yapar.
    """
    def __init__(self, d):
        from decimal import Decimal
        converted = {}
        for k, v in d.items():
            converted[k] = float(v) if isinstance(v, Decimal) else v
        super().__init__(converted)
        self._values = list(converted.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _PgCursor:
    """psycopg2 cursor wrapper."""
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return _DictRow(row) if row else None

    def fetchall(self):
        return [_DictRow(r) for r in self._cur.fetchall()]

    def close(self):
        self._cur.close()

    @property
    def description(self):
        return self._cur.description

    @property
    def rowcount(self):
        return self._cur.rowcount


class _PgConn:
    """sqlite3 uyumlu conn wrapper.
    ? -> %s otomatik, _DictRow ile row['col'] ve row[0] erisimi.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        sql = sql.replace('?', '%s')
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        return _PgCursor(cur)

    def executemany(self, sql, params_list):
        sql = sql.replace('?', '%s')
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        cur.executemany(sql, params_list)
        return _PgCursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return _PgCursor(self._conn.cursor(cursor_factory=RealDictCursor))


# --- CONNECTION ---

def _resolve_tenant_schema():
    """Tenant schema'sini bul. Oncelik: NiceGUI session > contextvars > None.
    NiceGUI session her zaman dogru kullanicinin tenant'ini verir.
    Contextvars startup/script'lerde kullanilir.
    """
    # 1) NiceGUI session (kullaniciya ozel, her zaman dogru)
    try:
        from nicegui import app as _app
        schema = _app.storage.user.get('tenant_schema')
        if schema:
            return schema
    except Exception:
        pass
    # 2) Contextvars (startup, script, test icin)
    schema = _current_tenant_schema.get()
    if schema:
        return schema
    return None


@contextmanager
def get_db():
    """Veritabani baglantisi ac (pool'dan). Tenant schema otomatik belirlenir."""
    pool = _get_pool()
    raw_conn = pool.getconn()
    try:
        schema = _resolve_tenant_schema()
        if schema:
            cur = raw_conn.cursor()
            cur.execute("SET search_path TO %s, public", (schema,))
            cur.close()
            raw_conn.commit()
        conn = _PgConn(raw_conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        # search_path'i sifirla ve pool'a geri ver
        try:
            raw_conn.cursor().execute("SET search_path TO public")
            raw_conn.commit()
        except Exception:
            pass
        pool.putconn(raw_conn)


@contextmanager
def get_public_db():
    """Public schema icin baglanti (tenants, users tablolari)."""
    pool = _get_pool()
    raw_conn = pool.getconn()
    try:
        cur = raw_conn.cursor()
        cur.execute("SET search_path TO public")
        cur.close()
        raw_conn.commit()
        conn = _PgConn(raw_conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        pool.putconn(raw_conn)


# --- HELPERS ---

def _col_exists(conn, table, column):
    cur = conn.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column)
    )
    result = cur.fetchone()
    cur.close()
    return result is not None


# --- TENANT YONETIMI ---

def get_all_tenants():
    """Tum tenant listesi (login dropdown icin)."""
    with get_public_db() as conn:
        rows = conn.execute("SELECT * FROM tenants WHERE is_active=1 ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def create_tenant(name):
    """Yeni tenant olustur: tenants tablosuna kayit + schema + tablolar.
    Returns: tenant dict.
    """
    with get_public_db() as conn:
        # Schema adi: t_1, t_2, ... (id bazli)
        cur = conn.execute(
            "INSERT INTO tenants (name, schema_name, is_active, created_at) "
            "VALUES (%s, '', 1, %s) RETURNING id",
            (name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        tenant_id = cur.fetchone()['id']
        schema_name = f"t_{tenant_id}"
        conn.execute("UPDATE tenants SET schema_name=%s WHERE id=%s", (schema_name, tenant_id))

    # Schema olustur ve tabloları kur
    init_tenant_schema(schema_name)

    return {'id': tenant_id, 'name': name, 'schema_name': schema_name}


def init_tenant_schema(schema_name):
    """Belirtilen schema'yi olustur ve icine tum business tablolari kur."""
    raw_conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = raw_conn.cursor()
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        cur.execute("SET search_path TO %s, public", (schema_name,))
        cur.close()
        raw_conn.commit()

        conn = _PgConn(raw_conn)
        _create_business_tables(conn)
        conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


# --- INIT ---

def init_db():
    """Public schema tablolarini olustur (tenants + users).
    Her startup'ta cagirilir.
    """
    with get_public_db() as conn:
        # Tenants tablosu
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                schema_name TEXT NOT NULL DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT ''
            )
        ''')
        # Users tablosu (tenant_id ile)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                tenant_id INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT DEFAULT '',
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                UNIQUE(tenant_id, username)
            )
        ''')
        # tenant_id kolonu eski DB'de yoksa ekle
        if not _col_exists(conn, 'users', 'tenant_id'):
            conn.execute("ALTER TABLE users ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1")
        # username unique kaldır, (tenant_id, username) unique yap
        # Not: IF NOT EXISTS index zaten idempotent
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_tenant_username ON users(tenant_id, username)")


def _create_business_tables(conn):
    """Tenant schema icinde business tablolarini olustur.
    conn zaten SET search_path ile dogru schema'ya ayarlanmis olmali.
    """
    conn.execute('''
        CREATE TABLE IF NOT EXISTS urunler (
            kod TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            kategori TEXT DEFAULT '',
            birim TEXT DEFAULT 'KG',
            desi_degeri NUMERIC(10,2) DEFAULT 0,
            aktif INTEGER DEFAULT 1
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS firmalar (
            kod TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            tel TEXT DEFAULT '',
            adres TEXT DEFAULT '',
            vkn_tckn TEXT DEFAULT '',
            nace TEXT DEFAULT '',
            is_alani TEXT DEFAULT '',
            email TEXT DEFAULT '',
            risk_limiti NUMERIC(15,2) DEFAULT 0,
            aktif INTEGER DEFAULT 1
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS hareketler (
            id SERIAL PRIMARY KEY,
            tarih TEXT,
            firma_kod TEXT,
            firma_ad TEXT,
            tur TEXT,
            urun_kod TEXT,
            urun_ad TEXT,
            miktar NUMERIC(15,4) DEFAULT 0,
            birim_fiyat NUMERIC(15,4) DEFAULT 0,
            toplam NUMERIC(15,2) DEFAULT 0,
            kdv_orani NUMERIC(5,2) DEFAULT 0,
            kdv_tutar NUMERIC(15,2) DEFAULT 0,
            kdvli_toplam NUMERIC(15,2) DEFAULT 0,
            tevkifat_orani TEXT DEFAULT '0',
            tevkifat_tutar NUMERIC(15,2) DEFAULT 0,
            tevkifatsiz_kdv NUMERIC(15,2) DEFAULT 0,
            aciklama TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS kasa (
            id SERIAL PRIMARY KEY,
            tarih TEXT,
            firma_kod TEXT,
            firma_ad TEXT,
            tur TEXT,
            tutar NUMERIC(15,2) DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            cek_id INTEGER,
            gelir_gider_id INTEGER,
            banka TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cekler (
            id SERIAL PRIMARY KEY,
            cek_no TEXT,
            firma_kod TEXT,
            firma_ad TEXT,
            kesim_tarih TEXT,
            vade_tarih TEXT,
            tutar NUMERIC(15,2) DEFAULT 0,
            tur TEXT DEFAULT '',
            durum TEXT DEFAULT 'PORTFOYDE',
            cek_turu TEXT DEFAULT 'ALINAN',
            kesideci TEXT DEFAULT '',
            lehtar TEXT DEFAULT '',
            ciro_firma_kod TEXT DEFAULT '',
            ciro_firma_ad TEXT DEFAULT '',
            tahsil_tarih TEXT,
            notlar TEXT DEFAULT '',
            evrak_tipi TEXT DEFAULT 'CEK'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS uretim (
            id SERIAL PRIMARY KEY,
            tarih TEXT,
            aciklama TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS uretim_girdi (
            id SERIAL PRIMARY KEY,
            uretim_id INTEGER,
            urun_kod TEXT,
            urun_ad TEXT,
            miktar NUMERIC(15,4) DEFAULT 0,
            FOREIGN KEY (uretim_id) REFERENCES uretim(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS uretim_cikti (
            id SERIAL PRIMARY KEY,
            uretim_id INTEGER,
            urun_kod TEXT,
            urun_ad TEXT,
            miktar NUMERIC(15,4) DEFAULT 0,
            FOREIGN KEY (uretim_id) REFERENCES uretim(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings_company (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            firma_adi TEXT DEFAULT '',
            vkn_tckn TEXT DEFAULT '',
            vergi_dairesi TEXT DEFAULT '',
            adres TEXT DEFAULT '',
            nace TEXT DEFAULT '',
            is_alani TEXT DEFAULT '',
            telefon TEXT DEFAULT '',
            email TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            ucret_periyodu TEXT DEFAULT 'AYLIK',
            uretim_takibi INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            actor_user_id INTEGER,
            actor_username TEXT DEFAULT '',
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT DEFAULT '',
            old_data TEXT DEFAULT '',
            new_data TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            n_type TEXT NOT NULL,
            title TEXT DEFAULT '',
            message TEXT DEFAULT '',
            ref_type TEXT DEFAULT '',
            ref_id TEXT DEFAULT '',
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cari_mutabakat (
            id SERIAL PRIMARY KEY,
            firma_kod TEXT NOT NULL,
            firma_ad TEXT DEFAULT '',
            mutabakat_tarih TEXT NOT NULL,
            sistem_bakiye NUMERIC(15,2) DEFAULT 0,
            firma_bakiye NUMERIC(15,2) DEFAULT 0,
            fark NUMERIC(15,2) DEFAULT 0,
            durum TEXT DEFAULT 'ACIK',
            notlar TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cek_hareketleri (
            id SERIAL PRIMARY KEY,
            cek_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            eski_durum TEXT,
            yeni_durum TEXT NOT NULL,
            aciklama TEXT DEFAULT '',
            FOREIGN KEY (cek_id) REFERENCES cekler(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS hareket_log (
            id SERIAL PRIMARY KEY,
            hareket_id INTEGER,
            islem TEXT NOT NULL,
            tarih TEXT NOT NULL,
            detay TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS gelir_gider (
            id SERIAL PRIMARY KEY,
            tarih TEXT,
            tur TEXT NOT NULL,
            kategori TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            tutar NUMERIC(15,2) DEFAULT 0,
            kdv_orani NUMERIC(5,2) DEFAULT 0,
            kdv_tutar NUMERIC(15,2) DEFAULT 0,
            toplam NUMERIC(15,2) DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            firma_kod TEXT DEFAULT '',
            firma_ad TEXT DEFAULT '',
            odeme_durumu TEXT DEFAULT 'ODENDI',
            vade_tarih TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS personel (
            id SERIAL PRIMARY KEY,
            ad TEXT NOT NULL,
            maas NUMERIC(15,2) DEFAULT 0,
            ucret_tipi TEXT DEFAULT 'NET',
            durum TEXT DEFAULT 'AKTIF',
            giris_tarih TEXT,
            cikis_tarih TEXT,
            telefon TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS personel_maas_gecmis (
            id SERIAL PRIMARY KEY,
            personel_id INTEGER NOT NULL,
            eski_maas NUMERIC(15,2) DEFAULT 0,
            yeni_maas NUMERIC(15,2) DEFAULT 0,
            gecerlilik_tarih TEXT,
            aciklama TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            FOREIGN KEY (personel_id) REFERENCES personel(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS personel_aylik (
            id SERIAL PRIMARY KEY,
            personel_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            ay INTEGER NOT NULL,
            hafta INTEGER DEFAULT 0,
            maas NUMERIC(15,2) DEFAULT 0,
            mesai_saat NUMERIC(10,2) DEFAULT 0,
            mesai_tutar NUMERIC(15,2) DEFAULT 0,
            avans_toplam NUMERIC(15,2) DEFAULT 0,
            hakedis NUMERIC(15,2) DEFAULT 0,
            odenen NUMERIC(15,2) DEFAULT 0,
            kalan NUMERIC(15,2) DEFAULT 0,
            kilitli INTEGER DEFAULT 0,
            FOREIGN KEY (personel_id) REFERENCES personel(id),
            UNIQUE(personel_id, yil, ay, hafta)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS personel_hareket (
            id SERIAL PRIMARY KEY,
            personel_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            ay INTEGER NOT NULL,
            hafta INTEGER DEFAULT 0,
            tur TEXT NOT NULL,
            tutar NUMERIC(15,2) DEFAULT 0,
            saat NUMERIC(10,2) DEFAULT 0,
            tarih TEXT,
            aciklama TEXT DEFAULT '',
            gelir_gider_id INTEGER,
            created_at TEXT DEFAULT '',
            FOREIGN KEY (personel_id) REFERENCES personel(id)
        )
    ''')

    # --- INDEKSLER ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hareketler_firma ON hareketler(firma_kod)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hareketler_urun ON hareketler(urun_kod)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hareketler_tarih ON hareketler(tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hareketler_firma_tarih ON hareketler(firma_kod, tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kasa_firma ON kasa(firma_kod)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kasa_tarih ON kasa(tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kasa_firma_tarih ON kasa(firma_kod, tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cekler_durum ON cekler(durum, vade_tarih)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cekler_firma ON cekler(firma_kod)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cekler_vade ON cekler(vade_tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uretim_tarih ON uretim(tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mutabakat_firma_tarih ON cari_mutabakat(firma_kod, mutabakat_tarih)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gelir_gider_tarih ON gelir_gider(tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gelir_gider_tur ON gelir_gider(tur)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gelir_gider_firma ON gelir_gider(firma_kod)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gelir_gider_firma_tarih ON gelir_gider(firma_kod, tarih, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_personel_durum ON personel(durum)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_personel_aylik_donem ON personel_aylik(yil, ay)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_personel_hareket_donem ON personel_hareket(personel_id, yil, ay)")

    # --- MIGRATION (eski schema'lar icin kolon ekleme) ---
    if not _col_exists(conn, 'settings_company', 'ucret_periyodu'):
        conn.execute("ALTER TABLE settings_company ADD COLUMN ucret_periyodu TEXT DEFAULT 'AYLIK'")
    if not _col_exists(conn, 'personel_aylik', 'hafta'):
        conn.execute("ALTER TABLE personel_aylik ADD COLUMN hafta INTEGER DEFAULT 0")
        # Eski UNIQUE constraint'i kaldirip hafta dahil yenisini ekle
        try:
            conn.execute("ALTER TABLE personel_aylik DROP CONSTRAINT IF EXISTS personel_aylik_personel_id_yil_ay_key")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_personel_aylik_donem ON personel_aylik(personel_id, yil, ay, hafta)")
        except Exception:
            pass
    if not _col_exists(conn, 'personel_hareket', 'hafta'):
        conn.execute("ALTER TABLE personel_hareket ADD COLUMN hafta INTEGER DEFAULT 0")
    # Senet destegi: cekler tablosuna evrak_tipi
    if not _col_exists(conn, 'cekler', 'evrak_tipi'):
        conn.execute("ALTER TABLE cekler ADD COLUMN evrak_tipi TEXT DEFAULT 'CEK'")
    # Uretim takibi ozelligi
    if not _col_exists(conn, 'settings_company', 'uretim_takibi'):
        conn.execute("ALTER TABLE settings_company ADD COLUMN uretim_takibi INTEGER DEFAULT 0")
    # Urun kartina desi alani
    if not _col_exists(conn, 'urunler', 'desi_degeri'):
        conn.execute("ALTER TABLE urunler ADD COLUMN desi_degeri NUMERIC(10,2) DEFAULT 0")
    # Irsaliye/Fatura numarasi
    if not _col_exists(conn, 'hareketler', 'belge_no'):
        conn.execute("ALTER TABLE hareketler ADD COLUMN belge_no TEXT DEFAULT ''")
    # Soft-delete (Paket 8): firma/urun pasife alma
    if not _col_exists(conn, 'firmalar', 'aktif'):
        conn.execute("ALTER TABLE firmalar ADD COLUMN aktif INTEGER DEFAULT 1")
    if not _col_exists(conn, 'urunler', 'aktif'):
        conn.execute("ALTER TABLE urunler ADD COLUMN aktif INTEGER DEFAULT 1")
    if not _col_exists(conn, 'kasa', 'kategori'):
        conn.execute("ALTER TABLE kasa ADD COLUMN kategori TEXT DEFAULT ''")

    # --- HAFTALIK BILANCO TABLOLARI ---
    conn.execute('''
        CREATE TABLE IF NOT EXISTS haftalik_bilanco (
            id SERIAL PRIMARY KEY,
            yil INTEGER NOT NULL,
            hafta INTEGER NOT NULL,
            papel_fiyat NUMERIC(10,2) DEFAULT 0,
            tutkal_fiyat NUMERIC(10,2) DEFAULT 0,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            UNIQUE(yil, hafta)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS haftalik_bilanco_kalem (
            id SERIAL PRIMARY KEY,
            bilanco_id INTEGER NOT NULL,
            urun_kod TEXT,
            urun_ad TEXT,
            desi NUMERIC(10,2) DEFAULT 0,
            adet NUMERIC(10,0) DEFAULT 0,
            papel_fiyat NUMERIC(10,2) DEFAULT 0,
            tutkal NUMERIC(10,2) DEFAULT 0,
            satis_fiyat NUMERIC(10,2) DEFAULT 0,
            papel_ham_fiyat NUMERIC(15,2) DEFAULT 0,
            ham_maliyet NUMERIC(15,2) DEFAULT 0,
            fark NUMERIC(15,2) DEFAULT 0,
            kazanc NUMERIC(15,2) DEFAULT 0,
            haftalik_hammadde NUMERIC(15,2) DEFAULT 0,
            haftalik_satis NUMERIC(15,2) DEFAULT 0,
            FOREIGN KEY (bilanco_id) REFERENCES haftalik_bilanco(id)
        )
    ''')

    # --- BASLANGIC VERILERI ---
    conn.execute("INSERT INTO settings_company (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    conn.execute("INSERT INTO app_meta (key, value) VALUES ('db_version', '5') ON CONFLICT (key) DO NOTHING")
