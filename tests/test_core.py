# -*- coding: utf-8 -*-
"""核心纯函数与数据库行为。"""
import database as db
from app import _date_key, _mark_ongoing, _mask_secret, _normalize_layout, _pick, _to_flag


def test_date_key_ordering():
    assert _date_key("2024年10月") > _date_key("2024年9月")
    assert _date_key("2024-6") == (2024, 6)
    assert _date_key("2023.09") == (2023, 9)
    assert _date_key("至今") > _date_key("2030年12月")
    assert _date_key("") == (0, 0)


def test_pick_none_to_empty():
    assert _pick({"title": None}, ["title"]) == {"title": ""}


def test_to_flag():
    for v in (1, True, "1", "on", "Yes"):
        assert _to_flag(v) == 1
    for v in (0, False, "", "0", None):
        assert _to_flag(v) == 0


def test_mark_ongoing_injects_zhijin():
    rows = [{"end": "2026年6月", "ongoing": 0}, {"end": "", "ongoing": 1}]
    out = _mark_ongoing(rows)
    assert out[0]["end"] == "2026年6月" and out[1]["end"] == "至今"


def test_mask_secret():
    assert _mask_secret("") == ""
    assert _mask_secret("sk-1234567890abcd").startswith("sk-")
    assert "***" in _mask_secret("sk-1234567890abcd")


def test_normalize_layout_filters_bogus_keys():
    r = _normalize_layout('{"order":["awards","summary","bogus"],"hidden":["papers","x"]}')
    assert r["order"][0] == "awards"
    assert "bogus" not in r["order"]
    assert "papers" in r["hidden"] and "x" not in r["hidden"]


def test_default_user_seeded():
    users = db.all_rows("users")
    assert len(users) >= 1


def test_seed_demo_and_wipe(tmp_path):
    from app import seed_demo_data
    uid = db.all_rows("users")[0]["id"]
    before = len(db.get_rows_where("awards", "user_id=?", (uid,)))
    if before:  # 其他测试可能已写入，先清空保证可载入
        for t in ("awards", "positions", "education", "papers", "projects"):
            db.delete_rows_where(t, "user_id=?", (uid,))
    seed_demo_data(uid)
    assert len(db.get_rows_where("awards", "user_id=?", (uid,))) == 3
    assert len(db.get_rows_where("positions", "user_id=?", (uid,))) == 2
    prof = db.get_row("profile", uid)
    assert prof["name"] == "李明"
    # 清空（保留账户名）
    for t in ("awards", "positions", "education", "papers", "projects"):
        db.delete_rows_where(t, "user_id=?", (uid,))
    assert db.get_rows_where("awards", "user_id=?", (uid,)) == []
