"""Sistem audit log islemleri."""
import json
from datetime import datetime

from nicegui import app

from db import get_db


def _actor():
    user = app.storage.user.get('auth_user', {}) if hasattr(app.storage, 'user') else {}
    return user.get('id'), user.get('username', '')


def _insert_log(conn, action, entity_type, entity_id='', old_data=None, new_data=None, detail=''):
    actor_user_id, actor_username = _actor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        '''
        INSERT INTO audit_log
        (actor_user_id, actor_username, action, entity_type, entity_id, old_data, new_data, detail, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        ''',
        (
            actor_user_id,
            actor_username,
            action,
            entity_type,
            str(entity_id or ''),
            json.dumps(old_data, ensure_ascii=False, default=str) if old_data is not None else '',
            json.dumps(new_data, ensure_ascii=False, default=str) if new_data is not None else '',
            detail,
            now,
        ),
    )


def log_action_conn(conn, action, entity_type, entity_id='', old_data=None, new_data=None, detail=''):
    _insert_log(conn, action, entity_type, entity_id, old_data, new_data, detail)


def log_action(action, entity_type, entity_id='', old_data=None, new_data=None, detail=''):
    with get_db() as conn:
        _insert_log(conn, action, entity_type, entity_id, old_data, new_data, detail)


def list_logs(limit=500):
    with get_db() as conn:
        rows = conn.execute(
            '''
            SELECT id, actor_username, action, entity_type, entity_id, detail, created_at
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_logs_filtered(limit=500, action=None, entity_type=None, date_from=None, date_to=None):
    """Filtreleme destekli log listesi."""
    with get_db() as conn:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if action:
            sql += " AND action = ?"
            params.append(action)
        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)
        if date_from:
            sql += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND created_at <= ?"
            params.append(date_to + ' 23:59:59')
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
