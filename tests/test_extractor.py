# -*- coding: utf-8 -*-
"""规则提取与 AI JSON 清洗。"""
from extractor import DATE_RE2, extract_candidates, _parse_llm_json


def test_award_only():
    r = extract_candidates("2024年6月获得全国大学生数学建模竞赛一等奖")
    assert len(r["awards"]) == 1 and not r["positions"]


def test_position_only():
    r = extract_candidates("2023年9月担任班长")
    assert not r["awards"] and len(r["positions"]) == 1


def test_mixed_line_splits_by_clause():
    r = extract_candidates("2023年9月担任班长；2024年6月获国家奖学金")
    assert len(r["awards"]) == 1 and len(r["positions"]) == 1


def test_mixed_inseparable_yields_both():
    r = extract_candidates("担任班长期间获得一等奖学金")
    assert len(r["awards"]) == 1 and len(r["positions"]) == 1


def test_date_regex_ignores_serial_numbers():
    # 旧正则会把编号里的 2023-05 当日期
    r = extract_candidates("证书编号2023-0521号 一等奖学金")
    dates = [a["date"] for a in r["awards"]]
    assert "2023年5月" not in dates


def test_llm_json_sanitized():
    out = _parse_llm_json(
        '{"awards":[{"title":null,"level":"省级"},'
        '{"title":"X奖","date":null,"organizer":None}],"positions":[{"org":"学生会"},{"title":"部长","start":null}]}'
        .replace("None", "null"))
    assert out["awards"] == [{"title": "X奖", "level": "", "category": "",
                              "date": "", "organizer": "", "description": ""}]
    assert out["positions"] == [{"title": "部长", "org": "", "start": "", "end": "", "description": ""}]


def test_date_re2_boundary():
    assert DATE_RE2.search("编号2023-0521") is None
    m = DATE_RE2.search("2023.09开学")
    assert m and (m.group(1), m.group(2)) == ("2023", "09")
