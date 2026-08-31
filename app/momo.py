"""Đọc sao kê MoMo.

MoMo **không** có API công khai cho lịch sử ví cá nhân — developers.momo.vn chỉ
là cổng thanh toán cho merchant. Nên đường duy nhất để đưa chi tiêu MoMo vào
đây là file sao kê tự xuất: MoMo → Ví của tôi → Lịch sử giao dịch → Sao kê,
rồi tải file CSV về và upload ở trang /budget.

Mỗi bản xuất của MoMo lại đặt tên cột hơi khác nhau, nên không dò cột theo vị
trí mà theo từ khoá trong header (đã bỏ dấu), và bỏ qua mọi cột không hiểu.
"""

import csv
import io
import re
import unicodedata
from datetime import datetime

# key -> (nhãn hiển thị, màu trong biểu đồ)
CATEGORIES = {
    "an":       ("🍜 Ăn uống",   "oklch(0.70 0.15 25)"),
    "di_lai":   ("🛵 Đi lại",    "oklch(0.72 0.13 250)"),
    "mua_sam":  ("🛍 Mua sắm",   "oklch(0.75 0.11 350)"),
    "hoa_don":  ("🧾 Hoá đơn",   "oklch(0.74 0.13 150)"),
    "giai_tri": ("🎬 Giải trí",  "oklch(0.72 0.11 300)"),
    "khac":     ("✨ Khác",      "oklch(0.80 0.12 75)"),
}

# từ khoá trong mô tả giao dịch -> category
_KEYWORDS = [
    ("an",       ("food", "an uong", "coffee", "ca phe", "cafe", "highlands", "starbucks",
                  "phuc long", "trung nguyen", "bake", "tra sua", "milk tea", "nha hang",
                  "quan an", "com", "bun", "pho ", "kfc", "lotteria", "jollibee", "baemin")),
    ("di_lai",   ("grab", "be group", "gojek", "xanh sm", "taxi", "xe bus", "vexere",
                  "xang", "petrolimex", "gui xe", "ve may bay", "vietjet", "bamboo")),
    ("mua_sam",  ("shopee", "lazada", "tiki", "sendo", "uniqlo", "mua sam", "shop",
                  "circle k", "winmart", "bach hoa", "co.opmart", "guardian")),
    ("hoa_don",  ("tien dien", "tien nuoc", "hoa don", "internet", "wifi", "evn",
                  "vnpt", "viettel", "mobifone", "vinaphone", "nap tien dien thoai",
                  "hoc phi", "tien nha", "bao hiem")),
    ("giai_tri", ("netflix", "spotify", "youtube", "cgv", "lotte cinema", "beta cinema",
                  "galaxy cinema", "steam", "game", "karaoke", "du lich", "booking")),
]


def strip_accents(s: str) -> str:
    """'Thời gian' -> 'thoi gian' — để so header không phụ thuộc dấu tiếng Việt."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").strip().lower()


def guess_category(text: str) -> str:
    """Đoán hạng mục từ mô tả giao dịch. Không chắc thì trả 'khac'."""
    plain = strip_accents(text)
    for key, words in _KEYWORDS:
        if any(w in plain for w in words):
            return key
    return "khac"


def parse_amount(raw: str):
    """'-50.000đ' -> (50000, 'out') · '+1,200,000' -> (1200000, 'in').

    Trả (0, None) nếu ô trống hoặc không phải số.
    """
    if raw is None:
        return 0, None

    text = str(raw).strip()
    if not text:
        return 0, None

    negative = text.startswith("-") or "(" in text
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return 0, None

    return int(digits), ("out" if negative else "in")


def parse_date(raw: str) -> str:
    """Về dạng 'YYYY-MM-DD'. Không đọc được thì trả chuỗi rỗng."""
    text = (raw or "").strip()
    if not text:
        return ""

    # bỏ phần giờ nếu có: "12/03/2025 14:22:01" -> "12/03/2025"
    head = text.split(" ")[0].replace(".", "/").replace("-", "/")

    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d/%m/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(head, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""


def _decode(data: bytes) -> str:
    """Sao kê MoMo có bản UTF-8-BOM, có bản UTF-16 — thử lần lượt."""
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _find(headers, *keywords):
    """Tên cột đầu tiên (đã bỏ dấu) chứa một trong các từ khoá."""
    for name, plain in headers.items():
        if any(k in plain for k in keywords):
            return name
    return None


def parse_csv(data: bytes):
    """bytes của file sao kê -> list dict sẵn sàng ghi vào bảng transactions.

    Bỏ qua dòng không có số tiền hoặc không có ngày hợp lệ.
    """
    text = _decode(data)

    # MoMo xuất bằng ',' hoặc ';' tuỳ locale máy
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []

    headers = {name: strip_accents(name) for name in reader.fieldnames if name}

    col_date = _find(headers, "thoi gian", "ngay", "date", "time")
    col_amount = _find(headers, "so tien", "amount", "gia tri", "money")
    col_out = _find(headers, "tien ra", "chi", "debit", "withdraw")
    col_in = _find(headers, "tien vao", "thu", "credit", "deposit")
    col_note = _find(headers, "mo ta", "noi dung", "loai giao dich", "description",
                     "ghi chu", "doi tac", "nguoi nhan", "detail")
    col_ref = _find(headers, "ma giao dich", "ma gd", "transaction id", "trans id", "ma tham chieu")

    rows = []
    for raw in reader:
        date = parse_date(raw.get(col_date, "")) if col_date else ""
        if not date:
            continue

        # dạng 1 cột "Số tiền" có dấu, hoặc dạng 2 cột tiền ra / tiền vào
        amount, kind = parse_amount(raw.get(col_amount, "")) if col_amount else (0, None)
        if not amount and col_out:
            amount, _ = parse_amount(raw.get(col_out, ""))
            kind = "out"
        if not amount and col_in:
            amount, _ = parse_amount(raw.get(col_in, ""))
            kind = "in"
        if not amount:
            continue

        note = (raw.get(col_note) or "").strip() if col_note else ""
        rows.append({
            "amount": amount,
            "kind": kind or "out",   # sao kê không ghi dấu thì coi như tiền chi
            "category": guess_category(note),
            "note": note or "Giao dịch MoMo",
            "date": date,
            "source": "momo",
            "ref": (raw.get(col_ref) or "").strip() if col_ref else "",
        })

    return rows
