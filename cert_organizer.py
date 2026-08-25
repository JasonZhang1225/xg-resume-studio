"""证书自动整理：把 OCR 文本 / 文件名归纳成结构化的证书信息。

不依赖网络：纯规则识别标题、类别、日期、级别、发证单位；
识别结果用户随时可以在归档页手动修改。
"""
import os
import re
import uuid

from extractor import detect_level, find_date

# 类别关键词：顺序即优先级（奖学金优先于竞赛，避免「国家励志奖学金」被归到荣誉）
CATEGORY_RULES = [
    ("奖学金", ["奖学金", "励志", "助学金"]),
    ("荣誉称号", ["三好", "优秀学生", "优秀学生干部", "优秀干部", "优秀团员", "优秀党员",
                  "优秀毕业生", "标兵", "先进个人", "先进班集体", "荣誉称号", "精神文明"]),
    ("竞赛获奖", ["竞赛", "大赛", "比赛", "挑战杯", "互联网+", "建模", "大创", "创新创业",
                  "一等奖", "二等奖", "三等奖", "特等奖", "金奖", "银奖", "铜奖", "优胜奖"]),
    ("资格证书", ["资格证书", "合格证书", "等级证书", "职业资格", "cet", "四六级", "四级", "六级",
                  "普通话", "计算机等级", "教师资格", "驾驶证", "驾照", "toefl", "ielts",
                  "雅思", "托福", "初级会计", "证券从业", "银行从业"]),
    ("聘书任职", ["聘书", "聘任", "聘为", "聘请"]),
    ("结业培训", ["结业证书", "结业", "培训证书", "研修", "社会实践证明", "实习证明", "志愿服务证明"]),
]

CERT_WORDS = ["证书", "奖状", "奖章", "荣誉证", "聘书", "证明"]
# 只有这几个词本身的行是通用抬头，不能当证书名
GENERIC_TITLES = {"证书", "奖状", "荣誉证书", "获奖证书", "荣誉证", "聘书",
                  "结业证书", "培训证书", "资格证书", "合格证书", "成绩报告单"}
# 发证机构行通常以这些词结尾；用行尾判断避免把奖项名误认成机构
_ISSUER_SUFFIXES = ("大学", "学院", "学校", "中学", "小学", "委员会", "教育局", "教育厅",
                    "教育部", "中心", "协会", "学会", "公司", "集团", "研究院", "研究所",
                    "事务所", "基金会", "组委会", "人民政府", "联合会", "考试院", "出版社")
_ISSUER_LABEL_RE = re.compile(r"^(颁发单位|主办单位|承办单位|授予单位|发证单位|出具单位|颁发|主办)[:：]?")
NOISE_RE = re.compile(r"^(编号|no|证书编号|二维码|扫描件|拍照)\s*[:：]?", re.I)


def _clean(text):
    return re.sub(r"\s+", "", str(text or "")).strip()


def detect_category(text):
    low = str(text or "").lower()
    for cat, words in CATEGORY_RULES:
        if any(w in low for w in words):
            return cat
    return ""


def _strip_date(title, date):
    if date:
        title = title.replace(date, "")
    return re.sub(r"(20\d{2})\s*[年./\-]?\s*(\d{1,2})?\s*月?", "", title).strip(" ：:，,·-—")


def extract_title(lines, filename):
    """优先取含证书字样且较短的行；其次取类别命中的行；再退回首个有效行；最后用文件名。"""
    scored = []
    for i, raw in enumerate(lines):
        line = _clean(raw)
        if len(line) < 4 or NOISE_RE.match(line):
            continue
        score = 0
        if any(w in line for w in CERT_WORDS):
            score += 10
        if line in GENERIC_TITLES:
            score -= 25  # 「荣誉证书」「获奖证书」这类通用抬头，让位给具体奖项名
        if detect_category(line):
            score += 6
        if len(line) <= 30:
            score += 4
        if len(line) > 60:
            score -= 6
        if i <= 3:
            score += 1
        if score > 0:
            scored.append((score, -i, line))
    if scored:
        return sorted(scored, reverse=True)[0][2]
    for raw in lines:
        line = _clean(raw)
        if 4 <= len(line) <= 40 and not NOISE_RE.match(line):
            return line
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    return re.sub(r"^(IMG_|DSC_|WX20\d{6})\w*", "", stem).strip() or "未命名证书"


def extract_issuer(lines):
    """发证单位：取以机构后缀结尾的整行（如「共青团XX大学委员会」），取最长者。"""
    best = ""
    for raw in lines:
        line = _ISSUER_LABEL_RE.sub("", _clean(raw))
        if len(line) < 4 or len(line) > 30:
            continue
        if any(line.endswith(suf) for suf in _ISSUER_SUFFIXES):
            if len(line) > len(best):
                best = line
    return best


def analyze(ocr_text, filename=""):
    """从 OCR 文本与文件名推断证书信息，返回结构化 dict。"""
    lines = [l.strip() for l in str(ocr_text or "").splitlines() if l.strip()]
    joined = "\n".join(lines)
    date = find_date(joined)
    title = _strip_date(extract_title(lines, filename), date)
    # 标题行里往往同时带着发证单位，单独从全文找更稳
    issuer = extract_issuer(lines)
    if issuer and issuer in title:
        title = _strip_date(title.replace(issuer, ""), "").strip(" ：:，,·-—") or title
    category = detect_category(joined) or (detect_category(filename) or "其他")
    return {
        "title": title or "未命名证书",
        "category": category,
        "date": date,
        "level": detect_level(joined),
        "issuer": issuer,
    }


def make_thumbnail(path, max_side=520):
    """给图片生成缩略图（同目录 .thumb.jpg）；非图片或 Pillow 缺失时返回空串。"""
    try:
        from PIL import Image
    except ImportError:
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"):
        return ""
    thumb = f"{path}.thumb-{uuid.uuid4().hex[:8]}.jpg"
    try:
        with Image.open(path) as img:
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            img = img.convert("RGB")
            img.thumbnail((max_side, max_side))
            img.save(thumb, "JPEG", quality=82)
        return thumb
    except Exception:
        if os.path.exists(thumb):
            try:
                os.unlink(thumb)
            except OSError:
                pass
        return ""
