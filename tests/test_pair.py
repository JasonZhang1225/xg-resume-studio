# -*- coding: utf-8 -*-
"""局域网配对码门卫回归（RESUME_LAN=1 时，非本机设备需持配对 Cookie）。"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
from app import app  # noqa: E402

CODE = "AB2345"


@pytest.fixture()
def lan_client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_LAN", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "pair.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    db.set_setting("pair_code", CODE)
    return TestClient(app, follow_redirects=False)


def test_unpaired_remote_redirected_to_pair(lan_client):
    r = lan_client.get("/")
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("/pair")


def test_unpaired_api_blocked(lan_client):
    r = lan_client.get("/api/items")
    assert r.status_code == 403
    assert r.json()["need_pair"] is True


def test_wrong_code_rejected(lan_client):
    r = lan_client.post("/api/pair", json={"code": "ZZZZ99", "next": "/"})
    assert r.status_code == 400


def test_correct_code_grants_access(lan_client):
    r = lan_client.post("/api/pair", json={"code": CODE, "next": "/items"})
    assert r.status_code == 200 and r.json()["next"] == "/items"
    assert "pair" in r.cookies
    home = lan_client.get("/items")
    assert home.status_code == 200


def test_open_redirect_blocked(lan_client):
    r = lan_client.post("/api/pair", json={"code": CODE, "next": "//evil.example"})
    assert r.status_code == 200
    assert r.json()["next"] == "/"
