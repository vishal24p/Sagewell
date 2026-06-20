"""M3: `create_app()` factory sanity checks."""
from __future__ import annotations

import pytest
from fastapi import FastAPI

from src.api.app import create_app


def test_create_app_returns_fastapi_instance():
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_is_idempotent():
    """Two calls produce distinct app instances."""
    a, b = create_app(), create_app()
    assert a is not b
    assert isinstance(a, FastAPI)
    assert isinstance(b, FastAPI)


def test_create_app_exposes_expected_paths():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert {"/health", "/openapi.json", "/docs", "/redoc"}.issubset(paths)
