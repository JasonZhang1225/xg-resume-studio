# -*- coding: utf-8 -*-
"""数据目录迁移、整包导出/导入、同步到网盘文件夹。"""
import io
import sqlite3
import zipfile

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import database as db  # noqa: E402
import datasync  # noqa: E402
import app as appmod  # noqa: E402


@pytest.fixture()
def env(monkeypatch, tmp_path):
    data = tmp_path / "data"
    (data / "uploads" / "photos").mkdir(parents=True)
    monkeypatch.setenv("RESUME_NO_BACKUP", "1")
    monkeypatch.setattr(db, "DATA_DIR", str(data))
    monkeypatch.setattr(db, "DB_PATH", str(data / "data.db"))
    monkeypatch.setattr(db, "BACKUP_DIR", str(data / "data_backups"))
    monkeypatch.setattr(db, "LEGACY_DATA_DIR", str(tmp_path / "legacy"))
    db.init_db()
    db.set_setting("initialized", "1")
    return tmp_path


@pytest.fixture()
def client(env):
    return TestClient(appmod.app, follow_redirects=False, client=("127.0.0.1", 50000))


def test_legacy_dir_migrated_once(env):
    legacy = env / "legacy"
    (legacy / "uploads" / "photos").mkdir(parents=True)
    sqlite3.connect(str(legacy / "data.db")).close()
    (legacy / "uploads" / "photos" / "a.png").write_bytes(b"png")
    new = env / "appdata"
    db.DATA_DIR = str(new)
    assert db.migrate_legacy_data() is True
    assert (new / "data.db").is_file() and (new / "uploads" / "photos" / "a.png").read_bytes() == b"png"
    assert (legacy / db.MIGRATED_MARK).exists() and (legacy / "data.db").exists()  # 旧数据原样保留
    assert db.legacy_data_pending() is False
    assert db.migrate_legacy_data() is False  # 新位置已有库，不再覆盖


def test_legacy_pending_when_new_location_has_data(env):
    legacy = env / "legacy"
    legacy.mkdir()
    sqlite3.connect(str(legacy / "data.db")).close()
    assert db.migrate_legacy_data() is False  # 当前数据目录已有库
    assert db.legacy_data_pending() is True


def test_export_import_roundtrip_keeps_local_secrets(client, env):
    db.insert_row("awards", {"user_id": 1, "title": "数学建模一等奖", "date": "2024年"})
    db.set_setting("api_key", "sk-local-secret")
    (env / "data" / "uploads" / "photos" / "p.png").write_bytes(b"photo")

    r = client.get("/api/data/export")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert {"manifest.json", "data.db", "uploads/photos/p.png"} <= set(z.namelist())
    snap = env / "snap.db"
    snap.write_bytes(z.read("data.db"))
    c = sqlite3.connect(str(snap))
    assert c.execute("SELECT COUNT(*) FROM settings WHERE key='api_key'").fetchone()[0] == 0  # Key 不进备份
    c.close()

    # 模拟新电脑：清空条目和照片，本机有自己的 Key
    db.get_conn().execute("DELETE FROM awards").connection.commit()
    (env / "data" / "uploads" / "photos" / "p.png").unlink()
    db.set_setting("api_key", "sk-new-machine")
    r = client.post("/api/data/import", files={"file": ("b.zip", r.content, "application/zip")})
    assert r.status_code == 200, r.text
    assert [a["title"] for a in db.get_rows_where("awards", "user_id=?", (1,))] == ["数学建模一等奖"]
    assert (env / "data" / "uploads" / "photos" / "p.png").read_bytes() == b"photo"
    assert db.get_setting("api_key") == "sk-new-machine"


def test_import_rejects_bad_archives(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("data.db", b"not sqlite")
        z.writestr("uploads/../../evil.txt", b"x")
    r = client.post("/api/data/import", files={"file": ("x.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400
    r = client.post("/api/data/import", files={"file": ("x.zip", b"garbage", "application/zip")})
    assert r.status_code == 400


def test_data_endpoints_local_only(env, monkeypatch):
    monkeypatch.setenv("RESUME_LAN", "1")
    remote = TestClient(appmod.app, follow_redirects=False, client=("192.168.1.20", 50000))
    remote.cookies.set("pair", appmod._pair_code())
    assert remote.get("/api/data/export").status_code == 403
    assert remote.put("/api/data/sync", json={"dir": "/tmp", "enabled": True}).status_code == 403


def test_sync_to_cloud_folder(client, env):
    cloud = env / "OneDrive"
    cloud.mkdir()
    r = client.put("/api/data/sync", json={"dir": str(cloud), "enabled": True})
    assert r.status_code == 200 and r.json()["ok"], r.text
    files = sorted(p.name for p in (cloud / datasync.SYNC_SUBDIR).iterdir())
    assert any(n.endswith("-latest.zip") for n in files) and len(files) == 2
    assert not any(n.endswith(".part") for n in files)
    assert datasync.sync_now(force=False).get("skipped")  # 数据没变就不重复写
    info = client.get("/api/data/info").json()
    assert info["sync"]["enabled"] and info["sync"]["last_sync"]

    bad = client.put("/api/data/sync", json={"dir": str(env / "data" / "uploads"), "enabled": True})
    assert bad.status_code == 400
    assert client.put("/api/data/sync", json={"dir": "relative/path", "enabled": True}).status_code == 400


def test_user_data_dir_per_platform(monkeypatch):
    monkeypatch.setattr(db.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\u\AppData\Roaming")
    assert db._user_data_dir().replace("/", "\\") == r"C:\Users\u\AppData\Roaming\XG Resume Studio\data"
    monkeypatch.setattr(db.sys, "platform", "darwin")
    assert db._user_data_dir().endswith("Library/Application Support/XG Resume Studio/data")
