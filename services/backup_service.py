"""Veritabani yedekleme servisi."""
import os
import subprocess
import glob
from datetime import datetime
from db import BASE_DIR, DB_CONFIG

BACKUP_DIR = os.path.join(BASE_DIR, 'backups')


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup():
    """pg_dump ile yedek al, gzip ile sikistir."""
    ensure_backup_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"cari_takip_{ts}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)

    env = os.environ.copy()
    env['PGPASSWORD'] = DB_CONFIG['password']

    cmd = [
        'pg_dump',
        '-h', DB_CONFIG['host'],
        '-p', str(DB_CONFIG['port']),
        '-U', DB_CONFIG['user'],
        '-d', DB_CONFIG['database'],
        '-f', filepath,
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump hatasi: {result.stderr}')

    # gzip
    import gzip
    gz_path = filepath + '.gz'
    with open(filepath, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
        f_out.writelines(f_in)
    os.remove(filepath)

    _cleanup_old_backups()
    return gz_path


def _cleanup_old_backups(keep=7):
    """En eski yedekleri sil, sadece son N tanesini tut."""
    ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, 'cari_takip_*.sql.gz')))
    while len(files) > keep:
        os.remove(files.pop(0))


def list_backups():
    """Mevcut yedek dosyalarini listele."""
    ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, 'cari_takip_*.sql.gz')), reverse=True)
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
