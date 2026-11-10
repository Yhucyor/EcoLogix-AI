"""Shared test isolation & live ASGI HTTP helpers using Python stdlib only."""
import json
import os
import shutil
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

import uvicorn

from backend.database.connection import DEFAULT_DB_FILE
from backend.database.models import init_database
from backend.database.seed import seed_all
from backend.main import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http_request(base_url: str, method: str, path: str, payload=None, token: str = ""):
    url = f"{base_url}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as err:
        raw_err = err.read()
        err.close()
        return err.code, {k.lower(): v for k, v in err.headers.items()}, raw_err


def http_json(base_url: str, method: str, path: str, payload=None, token: str = ""):
    status, headers, raw = http_request(base_url, method, path, payload=payload, token=token)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        parsed = {"raw": raw.decode("utf-8", errors="replace")}
    return status, parsed


class IsolatedDbTestCase(unittest.TestCase):
    """Provides a per-class isolated SQLite copy via ECOLOGIX_DB_PATH."""

    @classmethod
    def setUpClass(cls):
        cls._prev_db_env = os.environ.get("ECOLOGIX_DB_PATH")
        cls._tmpdir = tempfile.mkdtemp(prefix="ecologix_test_")
        cls.test_db_path = os.path.join(cls._tmpdir, "ecologix_test.db")
        if os.path.exists(DEFAULT_DB_FILE):
            shutil.copy2(DEFAULT_DB_FILE, cls.test_db_path)
            os.environ["ECOLOGIX_DB_PATH"] = cls.test_db_path
        else:
            os.environ["ECOLOGIX_DB_PATH"] = cls.test_db_path
            init_database()
            seed_all()

    @classmethod
    def tearDownClass(cls):
        if cls._prev_db_env is None:
            os.environ.pop("ECOLOGIX_DB_PATH", None)
        else:
            os.environ["ECOLOGIX_DB_PATH"] = cls._prev_db_env
        shutil.rmtree(cls._tmpdir, ignore_errors=True)


class LiveApiTestCase(IsolatedDbTestCase):
    """Runs FastAPI app over Uvicorn on an ephemeral port against the isolated DB."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.port = find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        config = uvicorn.Config(app, host="127.0.0.1", port=cls.port, log_level="critical")
        cls._server = uvicorn.Server(config)
        cls._thread = threading.Thread(target=cls._server.run, daemon=True)
        cls._thread.start()
        deadline = time.time() + 10.0
        while time.time() < deadline:
            try:
                status, _ = http_json(cls.base_url, "GET", "/api/health")
                if status == 200:
                    return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("Live test Uvicorn server did not become ready in time")

    @classmethod
    def tearDownClass(cls):
        cls._server.should_exit = True
        cls._thread.join(timeout=5)
        super().tearDownClass()
