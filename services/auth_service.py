"""Kullanici ve kimlik dogrulama islemleri (multi-tenant)."""
import base64
import hashlib
import hmac
import os
from datetime import datetime

from db import get_public_db, get_db, get_all_tenants, create_tenant


PBKDF2_ROUNDS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, rounds, salt_b64, hash_b64 = stored_hash.split('$', 3)
        if algo != 'pbkdf2_sha256':
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(rounds))
        return hmac.compare_digest(check, expected)
    except Exception:
        return False


def ensure_default_admin():
    """Varsayilan tenant ve admin kullaniciyi olustur (ilk kurulumda)."""
    with get_public_db() as conn:
        # Tenant var mi?
        tenant_count = conn.execute('SELECT COUNT(*) FROM tenants').fetchone()[0]
        if tenant_count == 0:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur = conn.execute(
                "INSERT INTO tenants (name, schema_name, is_active, created_at) "
                "VALUES (%s, '', 1, %s) RETURNING id",
                ('Varsayilan Firma', now)
            )
            tenant_id = cur.fetchone()['id']
            schema_name = f"t_{tenant_id}"
            conn.execute("UPDATE tenants SET schema_name=%s WHERE id=%s", (schema_name, tenant_id))
            # Commit yapilmali ki init_tenant_schema yeni connection'da gorebilsin
            conn.commit()

            # Tenant schema'sini olustur
            from db import init_tenant_schema
            init_tenant_schema(schema_name)

            # Admin kullaniciyi olustur
            with get_public_db() as conn2:
                conn2.execute(
                    "INSERT INTO users (username, full_name, password_hash, role, is_active, tenant_id, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, 1, %s, %s, %s)",
                    ('admin', 'Administrator', hash_password(os.environ.get('APP_ADMIN_PASSWORD', 'admin123')), 'admin', tenant_id, now, now)
                )
        else:
            # Users bos mu? (ilk kurulumda tenant var ama user yok olabilir)
            user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            if user_count == 0:
                tenant = conn.execute('SELECT id FROM tenants ORDER BY id LIMIT 1').fetchone()
                if tenant:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute(
                        "INSERT INTO users (username, full_name, password_hash, role, is_active, tenant_id, created_at, updated_at) "
                        "VALUES (%s, %s, %s, %s, 1, %s, %s, %s)",
                        ('admin', 'Administrator', hash_password(os.environ.get('APP_ADMIN_PASSWORD', 'admin123')), 'admin', tenant['id'], now, now)
                    )


# --- TENANT COZUMLEME (kullanici yonetimi izolasyonu) -------------------------
# public.users TUM firmalarin kullanicilarini tutar. Bu dosyadaki fonksiyonlar
# tenant filtresi olmadan calisirsa bir firmanin yoneticisi digerlerinin
# hesaplarini gorur, sifresini degistirir ve silebilir. Bu yuzden her kullanici
# islemi bir tenant_id'ye baglanir; cozulemezse islem YAPILMAZ (fail-safe).
# NOT: tenant.id ile schema adi ORTUSMEZ (orn. id=5 -> 't_3'), bu yuzden schema
# adindan id turetilmez, tenants tablosundan okunur.

def _tenant_id_from_schema(schema):
    if not schema:
        return None
    with get_public_db() as conn:
        row = conn.execute('SELECT id FROM tenants WHERE schema_name=%s', (schema,)).fetchone()
        return row['id'] if row else None


def current_tenant_id():
    """Aktif oturumun tenant_id'si. Sayfalarda NiceGUI session'dan, API/script
    baglaminda contextvar'daki schema uzerinden cozulur. Bulunamazsa None."""
    try:
        from nicegui import app as _app
        user = _app.storage.user.get('auth_user') or {}
        tid = user.get('tenant_id')
        if tid:
            return int(tid)
    except Exception:
        pass
    try:
        from db import get_tenant_schema
        return _tenant_id_from_schema(get_tenant_schema())
    except Exception:
        return None


def _zorunlu_tenant_id(tenant_id=None):
    tid = tenant_id if tenant_id else current_tenant_id()
    if not tid:
        raise PermissionError('Firma (tenant) belirlenemedi - kullanici islemi reddedildi')
    return int(tid)


def list_users(tenant_id=None):
    """Kullanici listesi - SADECE aktif firmanin kullanicilari.
    tenant_id verilmezse oturumdan cozulur; cozulemezse bos liste doner."""
    tid = tenant_id if tenant_id else current_tenant_id()
    if not tid:
        return []
    with get_public_db() as conn:
        rows = conn.execute(
            "SELECT id, username, full_name, role, is_active, tenant_id, created_at, updated_at, last_login_at "
            "FROM users WHERE tenant_id=%s ORDER BY username",
            (tid,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_user(data):
    """Yeni kullanici ekle. Firma oturumdan alinir (data['tenant_id'] ile ezilebilir).
    Eskiden varsayilan 1 idi: Ayarlar sayfasi tenant_id gondermedigi icin her yeni
    kullanici 'Varsayilan Firma'ya yaziliyor ve kendi firmasina giris yapamiyordu."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tenant_id = _zorunlu_tenant_id(data.get('tenant_id'))
    with get_public_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, full_name, password_hash, role, is_active, tenant_id, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                data['username'].strip(),
                data.get('full_name', '').strip(),
                hash_password(data['password']),
                data.get('role', 'user'),
                1 if data.get('is_active', True) else 0,
                tenant_id,
                now,
                now,
            ),
        )
        return cur.fetchone()['id']


def update_user(user_id, data, tenant_id=None):
    """Kullanici guncelle - sadece AYNI firmanin kullanicisi."""
    tid = _zorunlu_tenant_id(tenant_id)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_public_db() as conn:
        cur = conn.execute(
            "UPDATE users SET full_name=%s, role=%s, is_active=%s, updated_at=%s "
            "WHERE id=%s AND tenant_id=%s",
            (
                data.get('full_name', '').strip(),
                data.get('role', 'user'),
                1 if data.get('is_active', True) else 0,
                now,
                user_id,
                tid,
            ),
        )
        if cur.rowcount == 0:
            raise PermissionError('Kullanici bulunamadi veya baska bir firmaya ait')


def set_user_password(user_id, new_password, tenant_id=None):
    """Sifre degistir - sadece AYNI firmanin kullanicisi.
    (Tenant kontrolu olmadan bir firma yoneticisi baska firmanin hesabinin
    sifresini degistirip o hesapla giris yapabiliyordu.)"""
    tid = _zorunlu_tenant_id(tenant_id)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_public_db() as conn:
        cur = conn.execute(
            'UPDATE users SET password_hash=%s, updated_at=%s WHERE id=%s AND tenant_id=%s',
            (hash_password(new_password), now, user_id, tid),
        )
        if cur.rowcount == 0:
            raise PermissionError('Kullanici bulunamadi veya baska bir firmaya ait')


def delete_user(user_id, tenant_id=None):
    """Kullanici sil - sadece AYNI firmanin kullanicisi."""
    tid = _zorunlu_tenant_id(tenant_id)
    with get_public_db() as conn:
        cur = conn.execute('DELETE FROM users WHERE id=%s AND tenant_id=%s', (user_id, tid))
        if cur.rowcount == 0:
            raise PermissionError('Kullanici bulunamadi veya baska bir firmaya ait')


def authenticate(username: str, password: str, tenant_id: int = None):
    """Kullanici dogrulama. tenant_id verilirse o tenant icinde arar.
    Returns: { id, username, full_name, role, tenant_id, tenant_schema, tenant_name } veya None.
    """
    with get_public_db() as conn:
        if tenant_id:
            row = conn.execute(
                'SELECT * FROM users WHERE username=%s AND tenant_id=%s',
                (username.strip(), tenant_id)
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT * FROM users WHERE username=%s',
                (username.strip(),)
            ).fetchone()
        if not row:
            return None
        if not row['is_active']:
            return None
        if not verify_password(password, row['password_hash']):
            return None

        # Tenant bilgisini al
        tenant = conn.execute(
            'SELECT * FROM tenants WHERE id=%s', (row['tenant_id'],)
        ).fetchone()
        if not tenant or not tenant['is_active']:
            return None

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('UPDATE users SET last_login_at=%s WHERE id=%s', (now, row['id']))

        return {
            'id': row['id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'role': row['role'],
            'tenant_id': row['tenant_id'],
            'tenant_schema': tenant['schema_name'],
            'tenant_name': tenant['name'],
        }
