"""pytest 全局夹具：把数据库指到临时目录，避免污染任何真实数据。"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="rs-test-")
os.environ["RESUME_DB"] = os.path.join(_TMP, "data.db")
os.environ["RESUME_NO_BACKUP"] = "1"
