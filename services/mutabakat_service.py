"""Cari mutabakat islemleri."""
from datetime import datetime

from db import get_db


def list_mutabakat():
    with get_db() as conn:
        rows = conn.execute(
            '''
            SELECT * FROM cari_mutabakat
            ORDER BY mutabakat_tarih DESC, id DESC
            '''
        ).fetchall()
        return [dict(r) for r in rows]


def add_mutabakat(data):
    with get_db() as conn:
        cur = conn.execute(
            '''
            INSERT INTO cari_mutabakat
            (firma_kod, firma_ad, mutabakat_tarih, sistem_bakiye, firma_bakiye, fark, durum, notlar, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            RETURNING id
            ''',
            (
                data['firma_kod'],
                data.get('firma_ad', ''),
                data['mutabakat_tarih'],
                float(data.get('sistem_bakiye', 0) or 0),
                float(data.get('firma_bakiye', 0) or 0),
                float(data.get('fark', 0) or 0),
                data.get('durum', 'ACIK'),
                data.get('notlar', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ),
        )
        return cur.fetchone()['id']
