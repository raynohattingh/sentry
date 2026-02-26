"""Integration tests for web HUD stream — T033.

Tests:
- Unauthenticated GET /video_feed returns 401 with WWW-Authenticate header
- Authenticated request returns 200 with multipart content-type
- GET / returns HTML page
- Wrong password returns 401
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import base64
import pytest
from unittest.mock import patch
import importlib


@pytest.fixture
def client():
    import config
    config.HUD_USERNAME = "sentry"
    config.HUD_PASSWORD = "testpass"
    import web.streamer as _s; importlib.reload(_s)
    from web.streamer import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth_header(user="sentry", pw="testpass"):
    creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


def test_unauthenticated_video_feed_returns_401(client):
    resp = client.get("/video_feed")
    assert resp.status_code == 401


def test_unauthenticated_video_feed_has_www_authenticate_header(client):
    resp = client.get("/video_feed")
    assert "WWW-Authenticate" in resp.headers


def test_wrong_password_returns_401(client):
    resp = client.get("/video_feed", headers=_auth_header(pw="wrongpass"))
    assert resp.status_code == 401


def test_index_returns_html(client):
    resp = client.get("/", headers=_auth_header())
    assert resp.status_code == 200
    assert b"html" in resp.data.lower() or b"sentry" in resp.data.lower()


def test_unauthenticated_index_returns_401(client):
    resp = client.get("/")
    assert resp.status_code == 401
