"""Pytest fixtures for the M3 API tests.

The `app` fixture invokes the same `create_app()` factory the
production launch contract uses, so coverage is faithful.

The `client` fixture builds an `httpx.AsyncClient` against the
app via `ASGITransport`. ASGI transport lets us exercise the
full ASGI stack (middleware + exception handlers) without a
real socket.
"""
from __future__ import annotations

import pytest

import httpx

from src.api.app import create_app


@pytest.fixture
def app():
    """A fresh API skeleton per test."""
    return create_app()


@pytest.fixture
def client(app):
    """An `httpx.AsyncClient` bound to the ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")
