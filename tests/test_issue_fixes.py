# -*- coding: utf-8 -*-
"""证书归档页 500、AI 测试连接用已保存 Key、模型列表拉取。"""
import io
import json

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
import app as appmod  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("RESUME_NO_BACKUP", "1")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "fix.db"))
    db.init_db()
    db.set_setting("initialized", "1")
    appmod.seed_builtin_templates()
    return TestClient(appmod.app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_certs_page_renders_with_certificates(client):
    db.insert_row("certificates", {"user_id": 1, "title": "数学建模一等奖", "category": "竞赛获奖",
                                   "date": "2024年", "level": "国家级"})
    r = client.get("/certs")
    assert r.status_code == 200
    assert "数学建模一等奖" in r.text and "1 份" in r.text


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_ai_models_uses_saved_key(client, monkeypatch):
    db.set_setting("api_key", "sk-saved")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["auth"] = req.get_header("Authorization")
        return _FakeResp(json.dumps({"data": [{"id": "deepseek-reasoner"}, {"id": "deepseek-chat"}]}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    r = client.post("/api/ai/models", json={"api_base": "https://api.deepseek.com", "api_key": ""})
    assert r.json() == {"ok": True, "models": ["deepseek-chat", "deepseek-reasoner"]}
    assert seen["auth"] == "Bearer sk-saved"


def test_ai_test_uses_saved_key_when_masked(client, monkeypatch):
    db.set_setting("api_key", "sk-saved")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["auth"] = req.get_header("Authorization")
        return _FakeResp(b"{}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    r = client.post("/api/ai/test", json={"api_base": "https://api.deepseek.com",
                                          "api_key": "sk-***aved", "model": "deepseek-chat"})
    assert r.json()["ok"] is True
    assert seen["auth"] == "Bearer sk-saved"


def test_settings_split_from_home(client):
    home = client.get("/").text
    assert 'href="/settings"' in home and 'href="/resume"' in home
    assert 'id="aiPreset"' not in home and 'id="backupList"' not in home
    # 手动 IP 函数不能再被包在 rotateToken 里
    assert "async function rotateToken() {\n\nasync function" not in home
    r = client.get("/settings")
    assert r.status_code == 200
    for marker in ('id="aiPreset"', 'id="backupList"', "demoLoad()", db.DATA_DIR):
        assert marker in r.text
