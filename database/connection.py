"""
EcoLogix AI - Database Connection Manager
Hỗ trợ SQLite cho Demo thực tế, thiết kế sẵn sàng mở rộng sang PostgreSQL.
"""
import sqlite3
import os
from contextlib import contextmanager

DB_FILE = os.path.join(os.path.dirname(__file__), "ecologix.db")

def get_db_path():
    return DB_FILE

def get_connection():
    """Tạo kết nối SQLite có hỗ trợ Row dict và foreign keys"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(query: str, params: tuple = ()):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

def execute_insert(query: str, params: tuple = ()):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.lastrowid

def execute_update(query: str, params: tuple = ()):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount


def rows_to_dicts(rows) -> list:
    """Chuyển danh sách sqlite3.Row sang list[dict] chuẩn JSON."""
    return [dict(r) for r in rows] if rows else []


