"""Backward-compatible ASGI shim pointing to `backend.main:app`."""
from backend.main import app

__all__ = ["app"]
