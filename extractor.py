"""从原始文本中整理出「获奖情况」和「任职情况」候选条目。

默认用规则做初步提取；如果配置了兼容 OpenAI 的 API Key，还可以用大模型做更准的智能整理。
"""
import json
import re
import urllib.request

DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月")
DATE_RE2 = re.compile(r"(?<!\d)(20\d{2})\s*[./\-]\s*(\d{1,2})(?!\d)")
YEAR_RE = re.compile(r"(20\d{2})\s*年")
POS_RANGE_RE = re.compile(r"(20\d{2}\s*年\s*\d{1,2}\s*月)\s*[\-—~至到]+\s*(20\d{2}\s*年\s*\d{1,2}\s*月|至今|现在)")
POS_DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月")
LEADING_RE = re.compile(r"^[\s\d\.\-、\)）:：]+")
CLAUSE_SPLIT_RE = re.compile(r"[；;。！？]+")

LEVELS = [
    ("国家级", ["国家级", "全国", "国赛", "国家奖", "国家"]),
    ("省级", ["省级", "全省", "省赛", "省部级", "省"]),
    ("市级", ["市级", "全市", "市赛"]),
    ("校级", ["校级", "全校", "校内"]),
    ("院级", ["院级", "院内", "系级"]),
]

AWARD_WORDS = ["一等奖", "二等奖", "三等奖", "特等奖", "奖学金", "荣誉", "称号",
               "表彰", "优秀", "冠军", "亚军", "季军", "竞赛", "比赛", "获奖", "奖"]

POSITION_WORDS = ["担任", "任职", "主席", "部长", "副部长", "委员", "班长", "团支书",
                  "会长", "社长", "队长", "干事", "助理", "负责人", "代表", "理事",
                  "组长", "组织", "策划"]

CATEGORY_WORDS = [
    ("学业", ["奖学金", "学业", "成绩", "绩点", "三好", "学习"]),
    ("竞赛", ["竞赛", "比赛", "建模", "挑战杯", "互联网+", "大创", "编程", "创新"]),
    ("荣誉", ["荣誉", "称号", "优秀", "先进", "标兵"]),
]


def find_date(line):
    m = DATE_RE.search(line) or DATE_RE2.search(line)
    if m:
        return f"{m.group(1)}年{int(m.group(2))}月"
    m = YEAR_RE.search(line)
    if m:
        return f"{m.group(1)}年"
    return ""


def detect_level(line):
    for level, words in LEVELS:
        for w in words:
            if w in line:
                return level
    return ""


def detect_category(line):
    for cat, words in CATEGORY_WORDS:
        for w in words:
            if w in line:
                return cat
    return ""


def clean_title(text):
    text = LEADING_RE.sub("", text.strip())
    return text.strip()


def _dedup(items):
    seen = set()
    out = []
    for it in items:
        key = (it.get("title", ""), it.get("date", ""))
        if not key[0] or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _award_candidate(line):
    date = find_date(line)
    title = line
    if date and date in title:
        title = title.replace(date, "")
    return {
        "title": clean_title(title) or line,
        "level": detect_level(line),
        "category": detect_category(line),
        "date": date,
        "organizer": "",
        "description": line,
        "source_file": "",
    }


def _position_candidate(line):
    start = end = ""
    m = POS_RANGE_RE.search(line)
    if m:
        start = m.group(1)
        end = m.group(2)
        line = (line[:m.start()] + " " + line[m.end():]).strip()
    else:
        m = POS_DATE_RE.search(line)
        if m:
            start = f"{m.group(1)}年{int(m.group(2))}月"
    line = re.sub(r"^(担任|任职|曾任|现任)\s*", "", line)
    return {
        "title": clean_title(line),
        "org": "",
        "start": start,
        "end": end,
        "description": line,
        "source_file": "",
    }


def extract_candidates(raw_text):
    """规则提取，返回 {'awards': [...], 'positions': [...]}。"""
    awards, positions = [], []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if len(line) < 4:
            continue
        has_award = any(w in line for w in AWARD_WORDS)
        has_pos = any(w in line for w in POSITION_WORDS)
        if has_award and has_pos:
            # 一句话里两类词都有：先按子句拆开分别归类，避免丢掉其中一类
            pieces = [p.strip() for p in CLAUSE_SPLIT_RE.split(line) if len(p.strip()) >= 4]
            matched = False
            for piece in pieces:
                a_flag = any(w in piece for w in AWARD_WORDS)
                p_flag = any(w in piece for w in POSITION_WORDS)
                if a_flag and not p_flag:
                    awards.append(_award_candidate(piece))
                    matched = True
                elif p_flag and not a_flag:
                    positions.append(_position_candidate(piece))
                    matched = True
            if not matched:
                # 拆不开就两类都生成候选，宁多勿漏，由用户在确认弹窗里取舍
                awards.append(_award_candidate(line))
                positions.append(_position_candidate(line))
        elif has_award:
            awards.append(_award_candidate(line))
        elif has_pos:
            positions.append(_position_candidate(line))
    return {"awards": _dedup(awards), "positions": _dedup(positions)}


def _clean_str(value):
    return str(value).strip() if value is not None else ""


def _parse_llm_json(content):
    """解析大模型输出，并做字段清洗：非 dict 丢弃、空标题丢弃、None 归空串。"""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    data = json.loads(content)

    awards = []
    for it in data.get("awards") or []:
        if not isinstance(it, dict):
            continue
        title = _clean_str(it.get("title"))
        if not title:
            continue
        awards.append({
            "title": title,
            "level": _clean_str(it.get("level")),
            "category": _clean_str(it.get("category")),
            "date": _clean_str(it.get("date")),
            "organizer": _clean_str(it.get("organizer")),
            "description": _clean_str(it.get("description")),
        })

    positions = []
    for it in data.get("positions") or []:
        if not isinstance(it, dict):
            continue
        title = _clean_str(it.get("title"))
        if not title:
            continue
        positions.append({
            "title": title,
            "org": _clean_str(it.get("org")),
            "start": _clean_str(it.get("start")),
            "end": _clean_str(it.get("end")),
            "description": _clean_str(it.get("description")),
        })

    return {"awards": awards, "positions": positions}


def ai_extract(raw_text, api_base, api_key, model):
    """调用兼容 OpenAI 的接口做智能整理，返回 {'awards': [...], 'positions': [...]}。"""
    system = (
        "你是一个中文简历信息整理助手。用户会给你一份文档的原始文字（可能来自扫描件OCR，"
        "可能包含错字）。请从中提取「获奖情况」和「任职情况」，只输出 JSON，格式："
        '{"awards":[{"title":"奖项名称","level":"国家级/省级/校级等，不知道就留空",'
        '"category":"学业/竞赛/荣誉等，不知道就留空","date":"YYYY年M月","organizer":"颁发单位",'
        '"description":"一句话说明"}],"positions":[{"title":"职务名称","org":"组织/单位",'
        '"start":"YYYY年M月","end":"YYYY年M月","description":"主要工作"}]]}。'
        "没有的内容给空数组，不要编造。"
    )
    url = api_base.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": raw_text[:12000]},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    return _parse_llm_json(content)
