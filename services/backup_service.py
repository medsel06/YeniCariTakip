"""Veritabani yedekleme servisi (firma bazli).

ONEMLI: Yedek DOSYASI firmaya aittir. Eskiden pg_dump tum veritabanini
(t_1, t_2, t_3, t_6 + public.users) tek dosyaya dokuyordu; yani bir firmanin
aldigi yedek diger firmalarin tum muhasebe verisini iceriyordu. Artik sadece
o firmanin schema'si yedeklenir ve listede sadece kendi dosyalari gorunur.
Eski karisik dosyalar (cari_takip_<tarih>.sql.gz) yeni desene uymadigi icin
listelenmez ve temizlige de girmez - diskte durmaya devam eder.
"""
import os
import re
import subprocess
import glob
import gzip
from datetime import datetime
from db import BASE_DIR, DB_CONFIG, get_tenant_schema

BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
_SCHEMA_DESEN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _aktif_schema(schema=None):
    """Yedeklenecek firma schema'si. Verilmezse oturumdan alinir."""
    sch = schema or get_tenant_schema()
    if not sch:
        raise PermissionError('Firma (schema) belirlenemedi - yedek alinamaz')
    if not _SCHEMA_DESEN.match(sch):
        raise ValueError(f'Gecersiz schema adi: {sch}')
    return sch


def create_backup(schema=None):
    """Aktif firmanin schema'sini pg_dump ile yedekle, gzip ile sikistir."""
    sch = _aktif_schema(schema)
    ensure_backup_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"cari_takip_{sch}_{ts}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)

    env = os.environ.copy()
    env['PGPASSWORD'] = DB_CONFIG['password']

    cmd = [
        'pg_dump',
        '-h', DB_CONFIG['host'],
        '-p', str(DB_CONFIG['port']),
        '-U', DB_CONFIG['user'],
        '-d', DB_CONFIG['database'],
        '--schema', sch,          # SADECE bu firmanin tablolari
        '-f', filepath,
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump hatasi: {result.stderr}')

    gz_path = filepath + '.gz'
    with open(filepath, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
        f_out.writelines(f_in)
    os.remove(filepath)

    _cleanup_old_backups(sch)
    return gz_path


def _tenant_glob(schema):
    return os.path.join(BACKUP_DIR, f'cari_takip_{schema}_*.sql.gz')


def _cleanup_old_backups(schema, keep=8):
    """Sadece BU firmanin en eski yedeklerini sil (haftalik yedekle ~2 ay)."""
    ensure_backup_dir()
    files = sorted(glob.glob(_tenant_glob(schema)))
    while len(files) > keep:
        try:
            os.remove(files.pop(0))
        except OSError:
            break


def list_backups(schema=None):
    """Aktif firmanin yedek dosyalari (en yeni ustte)."""
    ensure_backup_dir()
    try:
        sch = _aktif_schema(schema)
    except PermissionError:
        return []
    files = sorted(glob.glob(_tenant_glob(sch)), reverse=True)
    result = []
    for f in files:
        stat = os.stat(f)
        result.append({
            'filename': os.path.basename(f),
            'path': f,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return result
