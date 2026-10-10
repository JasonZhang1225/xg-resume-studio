"""数据整包导出 / 导入，以及同步到网盘文件夹（OneDrive、iCloud 等）。

整包格式（zip）：
    manifest.json   格式版本、生成时间、来源机器
    data.db         数据库快照（sqlite backup API，WAL 下也是一致的）
    uploads/...     证件照、证书、附件原件

同步思路：不碰网盘的 API，只把整包写进用户选定的「本地同步文件夹」，由 OneDrive 等客户端
负责上传。活动数据库绝不放进网盘目录（同步客户端会在写入途中上传 WAL，导致损坏）。
"""
import json
import os
import shutil
import socket
import sqlite3
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import database as db

FORMAT = 1
APP_TAG = "XG Resume Studio"
# 只属于本机的设置：导出时剔除（API Key 不上云），导入时保留本机原值
LOCAL_ONLY_KEYS = ("api_key", "cookie_secret", "pair_code", "lan_enabled", "lan_manual_ip")
SYNC_SUBDIR = "滴鱼简历助手备份"
KEEP_DAILY = 7
SYNC_INTERVAL = 300  # 秒：后台每 5 分钟看一次数据有没有变化

_lock = threading.Lock()


def upload_dir() -> Path:
    return Path(db.DATA_DIR) / "uploads"


# ---------- 导出 ----------

def _snapshot_db(dest: str):
    src = sqlite3.connect(db.DB_PATH)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
        marks = ",".join("?" * len(LOCAL_ONLY_KEYS))
        dst.execute(f"DELETE FROM settings WHERE key IN ({marks})", LOCAL_ONLY_KEYS)
        dst.commit()
    finally:
        dst.close()
        src.close()


def write_export(dest_zip: str) -> str:
    """把当前全部数据打成 zip。先写临时文件再改名，网盘客户端不会上传半截文件。"""
    tmp_zip = dest_zip + ".part"
    with tempfile.TemporaryDirectory() as tmp:
        snap = os.path.join(tmp, "data.db")
        _snapshot_db(snap)
        manifest = {"app": APP_TAG, "format": FORMAT,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "host": socket.gethostname()}
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            z.write(snap, "data.db")
            up = upload_dir()
            if up.is_dir():
                for f in sorted(up.rglob("*")):
                    if f.is_file():
                        z.write(f, "uploads/" + f.relative_to(up).as_posix())
    os.replace(tmp_zip, dest_zip)
    return dest_zip


# ---------- 导入 ----------

def _check_db(path: str):
    try:
        c = sqlite3.connect(path)
        try:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            c.close()
    except sqlite3.DatabaseError as e:
        raise ValueError(f"备份里的数据库已损坏：{e}") from e
    if not {"users", "profile", "settings"} <= tables:
        raise ValueError("这不是滴鱼简历助手的数据备份")


def _restore_from(db_file: str, uploads_src: Path | None):
    """用 db_file 覆盖当前库，上传件合并进来（只增不删，文件名都是随机串不会冲突）。"""
    _check_db(db_file)
    db.backup_db()  # 覆盖前先兜底快照一份
    local = {k: db.get_setting(k) for k in LOCAL_ONLY_KEYS}
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(db.DB_PATH)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    db.init_db()  # 旧版本备份也补齐新列
    for k, v in local.items():
        if v:
            db.set_setting(k, v)
    if uploads_src and uploads_src.is_dir():
        shutil.copytree(uploads_src, upload_dir(), dirs_exist_ok=True)


def import_zip(zip_path: str):
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if "data.db" not in names:
            raise ValueError("压缩包里没有 data.db，不是本程序导出的备份")
        try:
            manifest = json.loads(z.read("manifest.json")) if "manifest.json" in names else {}
        except ValueError:
            manifest = {}
        if manifest.get("format", FORMAT) > FORMAT:
            raise ValueError("这个备份来自更新版本的程序，请先升级")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for info in z.infolist():
                n = info.filename
                if info.is_dir() or not (n == "data.db" or n.startswith("uploads/")):
                    continue
                target = (root / n).resolve()
                if root not in target.parents:  # 防止 ../ 路径穿越
                    raise ValueError(f"备份里有非法路径：{n}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as s, open(target, "wb") as d:
                    shutil.copyfileobj(s, d)
            _restore_from(str(root / "data.db"), root / "uploads")
    return manifest


def import_legacy_dir():
    """把程序旁旧 data/ 里的数据导进来（新位置已有别的库、没有自动迁移的情况）。"""
    legacy = Path(db.LEGACY_DATA_DIR)
    if not (legacy / "data.db").is_file():
        raise ValueError("旧目录里没有数据")
    with tempfile.TemporaryDirectory() as tmp:
        snap = os.path.join(tmp, "data.db")
        src = sqlite3.connect(str(legacy / "data.db"))
        dst = sqlite3.connect(snap)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        _restore_from(snap, legacy / "uploads")
    (legacy / db.MIGRATED_MARK).write_text(
        f"{datetime.now():%Y-%m-%d %H:%M} 已导入到：\n{db.DATA_DIR}\n", encoding="utf-8")


# ---------- 同步到网盘文件夹 ----------

def _config_path() -> Path:
    # 同步配置属于这台机器，不放进数据库，避免导入别处的备份时被覆盖
    return Path(db.DATA_DIR) / "sync.json"


def load_config() -> dict:
    try:
        return json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict):
    _config_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def cloud_candidates() -> list[dict]:
    """找本机已登录的网盘同步文件夹，供设置页一键选择。"""
    out, seen = [], set()

    def add(label, path):
        p = os.path.abspath(path)
        if os.path.isdir(p) and p not in seen:
            seen.add(p)
            out.append({"label": label, "path": p})

    for env, label in (("OneDriveConsumer", "OneDrive 个人版"), ("OneDriveCommercial", "OneDrive 工作/学校"),
                       ("OneDrive", "OneDrive")):
        if os.environ.get(env):
            add(label, os.environ[env])
    cloud = Path.home() / "Library" / "CloudStorage"
    if cloud.is_dir():
        for d in sorted(cloud.iterdir()):
            if d.name.startswith("OneDrive"):
                add("OneDrive" + d.name[len("OneDrive"):].replace("-", " ").rstrip(), str(d))
    add("iCloud 云盘", str(Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"))
    return out


def validate_dir(path: str) -> Path:
    p = Path(os.path.expanduser(path.strip())) if path else None
    if not p or not p.is_absolute():
        raise ValueError("请填写完整的文件夹路径")
    if not p.is_dir():
        raise ValueError("文件夹不存在")
    data = Path(db.DATA_DIR).resolve()
    if p.resolve() == data or data in p.resolve().parents:
        raise ValueError("同步文件夹不能放在数据目录里面")
    target = p / SYNC_SUBDIR
    try:
        target.mkdir(exist_ok=True)
        probe = target / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        raise ValueError(f"文件夹不可写：{e}") from e
    return p


def _host_tag() -> str:
    keep = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in socket.gethostname())
    return keep.strip("-")[:40] or "this-pc"


def _fingerprint() -> str:
    parts = []
    for suffix in ("", "-wal"):
        try:
            st = os.stat(db.DB_PATH + suffix)
            parts.append(f"{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append("-")
    return "|".join(parts)


def sync_now(force: bool = True) -> dict:
    """把整包写到「同步文件夹/滴鱼简历助手备份/」：一份 latest 覆盖写，每天另留一份，保留 7 天。"""
    with _lock:
        cfg = load_config()
        if not cfg.get("dir"):
            raise ValueError("还没有设置同步文件夹")
        fp = _fingerprint()
        if not force and fp == cfg.get("fingerprint"):
            return {"ok": True, "skipped": True}
        try:
            target = validate_dir(cfg["dir"]) / SYNC_SUBDIR
            host = _host_tag()
            latest = target / f"{host}-latest.zip"
            write_export(str(latest))
            daily = target / f"{host}-{datetime.now():%Y%m%d}.zip"
            shutil.copyfile(latest, daily)
            olds = sorted(target.glob(f"{host}-2*.zip"))
            for old in olds[:-KEEP_DAILY]:
                try:
                    old.unlink()
                except OSError:
                    pass
        except Exception as e:
            cfg.update(last_error=str(e), last_try=datetime.now().strftime("%Y-%m-%d %H:%M"))
            save_config(cfg)
            raise
        cfg.update(fingerprint=fp, last_sync=datetime.now().strftime("%Y-%m-%d %H:%M"),
                   last_file=str(latest), last_error="")
        save_config(cfg)
        return {"ok": True, "file": str(latest)}


def _loop():
    time.sleep(20)  # 让启动先跑完
    while True:
        cfg = load_config()
        if cfg.get("enabled") and cfg.get("dir"):
            try:
                sync_now(force=False)
            except Exception:
                pass  # 错误已记进 sync.json，设置页会显示
        time.sleep(SYNC_INTERVAL)


def start_background():
    if os.environ.get("RESUME_NO_BACKUP"):
        return
    threading.Thread(target=_loop, name="datasync", daemon=True).start()
