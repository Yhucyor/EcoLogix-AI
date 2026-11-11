"""
EcoLogix AI - Database Connection Manager
Hỗ trợ song song TiDB Cloud Serverless (MySQL wire protocol via PyMySQL + TLS) và SQLite cục bộ.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
import re
import sqlite3
import threading
from urllib.parse import unquote, urlparse

try:
    import certifi
except ImportError:
    certifi = None

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

DEFAULT_DB_FILE = os.path.join(os.path.dirname(__file__), "ecologix.db")
_ENV_LOADED = False
_TIDB_INIT_LOCK = threading.Lock()
_TIDB_READY_KEYS = set()
_THREAD_LOCAL = threading.local()


def _ensure_dotenv_loaded():
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        pass


_ensure_dotenv_loaded()


class CompatRow(dict):
    """Tương thích cả `row['col']` (dict) lẫn `row[0]` (tuple/sqlite3.Row)."""

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return list(self.values())[key]
        return super().__getitem__(key)


def _normalize_db_value(val):
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, timedelta):
        return str(val)
    return val


def _normalize_row(raw_row) -> CompatRow:
    if isinstance(raw_row, dict):
        return CompatRow({k: _normalize_db_value(v) for k, v in raw_row.items()})
    return CompatRow({str(i): _normalize_db_value(v) for i, v in enumerate(raw_row)})


def get_db_path() -> str:
    return os.environ.get("ECOLOGIX_DB_PATH") or DEFAULT_DB_FILE


def get_db_dialect() -> str:
    """Trả về 'mysql' khi cấu hình TiDB Cloud, hoặc 'sqlite' cho DB local / unit tests."""
    _ensure_dotenv_loaded()
    if os.environ.get("ECOLOGIX_DB_PATH"):
        return "sqlite"
    if os.environ.get("TIDB_HOST", "").strip():
        return "mysql"
    db_url = os.environ.get("DATABASE_URL", "").strip().lower()
    if db_url.startswith("mysql"):
        return "mysql"
    return "sqlite"


def is_tidb_enabled() -> bool:
    return get_db_dialect() == "mysql"


def _get_tidb_config() -> dict:
    _ensure_dotenv_loaded()
    host = os.environ.get("TIDB_HOST", "").strip()
    port = int(os.environ.get("TIDB_PORT", "4000") or "4000")
    user = os.environ.get("TIDB_USER", "").strip()
    password = os.environ.get("TIDB_PASSWORD", "")
    database = os.environ.get("TIDB_DATABASE", "ecologix").strip() or "ecologix"
    ssl_ca = os.environ.get("TIDB_SSL_CA", "").strip()

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url.lower().startswith("mysql") and not host:
        parsed = urlparse(db_url)
        host = parsed.hostname or host
        port = int(parsed.port or port)
        if parsed.username:
            user = unquote(parsed.username)
        if parsed.password:
            password = unquote(parsed.password)
        if parsed.path and parsed.path.strip("/"):
            database = parsed.path.strip("/")

    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        database = "ecologix"

    ssl_opts = None
    if ssl_ca and os.path.isfile(ssl_ca):
        ssl_opts = {"ca": ssl_ca}
    elif certifi is not None:
        ssl_opts = {"ca": certifi.where()}
    elif host.endswith("tidbcloud.com"):
        ssl_opts = {"ssl": True}

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "ssl": ssl_opts,
    }


def _qmark_to_pyformat(sql: str, has_params: bool = False) -> str:
    """Chuyển placeholder `?` (SQLite) -> `%s` (PyMySQL) an toàn ngoài chuỗi/comment."""
    out = []
    n = len(sql)
    i = 0
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False

    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            out.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if not (in_single or in_double or in_backtick):
            if ch == "-" and nxt == "-":
                in_line_comment = True
                out.append("--")
                i += 2
                continue
            if ch == "'":
                in_single = True
                out.append(ch)
                i += 1
                continue
            if ch == '"':
                in_double = True
                out.append(ch)
                i += 1
                continue
            if ch == "`":
                in_backtick = True
                out.append(ch)
                i += 1
                continue
            if ch == "?":
                out.append("%s")
                i += 1
                continue
            if ch == "%" and has_params:
                out.append("%%")
                i += 1
                continue
            out.append(ch)
            i += 1
            continue

        if in_single:
            out.append("%%" if (ch == "%" and has_params) else ch)
            if ch == "\\" and nxt:
                out.append("%%" if (nxt == "%" and has_params) else nxt)
                i += 2
                continue
            if ch == "'" and nxt == "'":
                out.append("'")
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            out.append("%%" if (ch == "%" and has_params) else ch)
            if ch == "\\" and nxt:
                out.append("%%" if (nxt == "%" and has_params) else nxt)
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        # inside backtick
        out.append(ch)
        if ch == "`":
            in_backtick = False
        i += 1

    return "".join(out)


def _split_sql_script(script: str) -> list:
    """Tách DDL script thành danh sách câu lệnh đơn, bỏ comment `--`."""
    stmts = []
    cur = []
    n = len(script)
    i = 0
    in_single = False
    in_double = False
    in_comment = False

    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""
        if in_comment:
            if ch == "\n":
                in_comment = False
                cur.append("\n")
            i += 1
            continue
        if not (in_single or in_double):
            if ch == "-" and nxt == "-":
                in_comment = True
                i += 2
                continue
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == ";":
                stmt = "".join(cur).strip()
                if stmt:
                    stmts.append(stmt)
                cur = []
                i += 1
                continue
        elif in_single:
            if ch == "\\" and nxt:
                cur.append(ch + nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
        elif in_double and ch == '"':
            in_double = False
        cur.append(ch)
        i += 1

    tail = "".join(cur).strip()
    if tail:
        stmts.append(tail)
    return stmts


class _PyMySQLCursorWrapper:
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, sql: str, params: tuple = ()):
        has_params = bool(params)
        translated = _qmark_to_pyformat(sql, has_params=has_params)
        self._cur.execute(translated, params if has_params else None)
        return self

    def executemany(self, sql: str, seq):
        items = list(seq)
        if not items:
            return self
        translated = _qmark_to_pyformat(sql, has_params=True)
        self._cur.executemany(translated, items)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return _normalize_row(row) if row is not None else None

    def fetchall(self):
        rows = self._cur.fetchall() or []
        return [_normalize_row(r) for r in rows]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class _PyMySQLConnWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return _PyMySQLCursorWrapper(self._conn.cursor(pymysql.cursors.DictCursor))

    def execute(self, sql: str, params: tuple = ()):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, script: str):
        with self._conn.cursor() as cur:
            for stmt in _split_sql_script(script):
                cur.execute(stmt)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        # Giữ kết nối thread-local tái sử dụng để tránh lặp TLS handshake tới TiDB Cloud
        pass


def _ensure_tidb_database(cfg: dict):
    cache_key = (cfg["host"], cfg["port"], cfg["user"], cfg["database"])
    if cache_key in _TIDB_READY_KEYS:
        return
    with _TIDB_INIT_LOCK:
        if cache_key in _TIDB_READY_KEYS:
            return
        bootstrap_conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            charset="utf8mb4",
            ssl=cfg["ssl"],
            connect_timeout=10,
            autocommit=True,
        )
        try:
            with bootstrap_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
        finally:
            bootstrap_conn.close()
        _TIDB_READY_KEYS.add(cache_key)


def _get_tidb_connection() -> _PyMySQLConnWrapper:
    if pymysql is None:
        raise RuntimeError("Thiếu thư viện `pymysql`. Vui lòng chạy `pip install pymysql certifi cryptography`.")
    cfg = _get_tidb_config()
    _ensure_tidb_database(cfg)
    key = (cfg["host"], cfg["port"], cfg["user"], cfg["database"])
    cached = getattr(_THREAD_LOCAL, "tidb_entry", None)
    if cached is not None and cached[0] == key:
        raw_conn = cached[1]
        try:
            raw_conn.ping(reconnect=True)
            return _PyMySQLConnWrapper(raw_conn)
        except Exception:
            try:
                raw_conn.close()
            except Exception:
                pass
            _THREAD_LOCAL.tidb_entry = None

    raw_conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        ssl=cfg["ssl"],
        connect_timeout=10,
        read_timeout=20,
        write_timeout=20,
        autocommit=False,
    )
    _THREAD_LOCAL.tidb_entry = (key, raw_conn)
    return _PyMySQLConnWrapper(raw_conn)


def get_connection():
    """Tạo kết nối TiDB Cloud (nếu cấu hình) hoặc SQLite cục bộ."""
    if is_tidb_enabled():
        return _get_tidb_connection()
    db_path = get_db_path()
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir and not os.path.isdir(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
        try:
            conn.rollback()
        except Exception:
            pass
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
    """Chuyển danh sách Row sang list[dict] chuẩn JSON."""
    return [dict(r) for r in rows] if rows else []
