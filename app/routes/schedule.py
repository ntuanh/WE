"""Lịch — mỗi đứa một tháng gọn, bấm vào ngày thì xem chi tiết ở bên cạnh.

Ngày ♥ vẫn được vẽ thành hai đường thời gian đặt cạnh nhau, vì đó là chỗ duy
nhất cần nhìn theo giờ: để thấy hai đứa rảnh trùng nhau lúc nào.
"""

import calendar
from datetime import date as date_cls
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud

router = APIRouter()

# Thứ 2 đứng đầu tuần, chủ nhật cuối — đọc lịch kiểu Việt Nam.
WEEKDAYS = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")
DAY_NAMES = ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật")

_cal = calendar.Calendar(firstweekday=calendar.MONDAY)

# Khung giờ của hai đường ngày ♥. Có việc sớm/muộn hơn thì tự nới ra vừa đủ.
DAY_START = 7 * 60
DAY_END = 22 * 60

# Ô trống chung phải rộng hơn chừng này mới đáng gọi là "rảnh cùng nhau" —
# hở 10 phút giữa hai việc thì rủ nhau đi đâu được.
FREE_MINUTES = 45


def _back(month: str = "", open_key: str = "", msg: str = "") -> RedirectResponse:
    """Về lại /schedule, giữ nguyên tháng và mở lại đúng ngày vừa thao tác."""
    parts = []

    if month:
        parts.append(f"month={quote(month)}")
    if open_key:
        parts.append(f"open={quote(open_key)}")
    if msg:
        parts.append(f"msg={quote(msg)}")

    return RedirectResponse("/schedule" + ("?" + "&".join(parts) if parts else ""),
                            status_code=303)


def _shift(month: str, delta: int) -> str:
    """Tháng liền trước / liền sau, dạng YYYY-MM."""
    year, mon = int(month[:4]), int(month[5:7]) + delta

    year += (mon - 1) // 12
    mon = (mon - 1) % 12 + 1

    return f"{year:04d}-{mon:02d}"


def _label(iso: str) -> str:
    day = date_cls.fromisoformat(iso)
    return f"{DAY_NAMES[day.weekday()]}, {day.day:02d}/{day.month:02d}"


def _weeks(month: str, per_day: dict, specials: set, today: str) -> list:
    """Lưới tháng: các tuần × 7 ngày, mỗi ô chỉ cần biết có việc hay không.

    Ô của tháng khác (phần đệm đầu/cuối lưới) để trơ: bấm vào thêm việc ở đó
    thì thêm xong lại không thấy nó đâu, vì đã sang tháng khác mất rồi.
    """
    year, mon = int(month[:4]), int(month[5:7])

    return [[{
        "date": day.isoformat(),
        "day": day.day,
        "in_month": day.month == mon,
        "today": day.isoformat() == today,
        "special": day.isoformat() in specials,
        "count": len(per_day.get(day.isoformat(), ())) if day.month == mon else 0,
    } for day in week] for week in _cal.monthdatescalendar(year, mon)]


def _month_days(month: str) -> list:
    """Các ngày thuộc đúng tháng này, theo thứ tự."""
    year, mon = int(month[:4]), int(month[5:7])
    last = calendar.monthrange(year, mon)[1]

    return [f"{month}-{d:02d}" for d in range(1, last + 1)]


def _pick(month: str, open_key: str, owner: str, today: str) -> str:
    """Ngày đang mở ở bảng chi tiết của một người.

    Bảng bên phải lúc nào cũng có nội dung, nên phải chọn sẵn một ngày: ngày vừa
    thao tác nếu có, không thì hôm nay, không thì ngày đầu tháng.
    """
    if open_key.startswith(f"{owner}:"):
        wanted = open_key.split(":", 1)[1]
        if wanted.startswith(month):
            return wanted

    return today if today.startswith(month) else f"{month}-01"


def _spell(total: int) -> str:
    """90 -> "1 tiếng 30 phút" — đọc nhanh hơn là "90 phút"."""
    if total <= 0:
        return "không có lúc nào"

    hours, mins = divmod(total, 60)
    parts = ([f"{hours} tiếng"] if hours else []) + ([f"{mins} phút"] if mins else [])

    return " ".join(parts)


def _items(events) -> list:
    """Việc của một ngày, việc cả ngày lên đầu rồi mới đến việc có giờ.

    Kèm sẵn độ dài: cột giờ bên trái đã nói bắt đầu/kết thúc rồi, nên nhắc lại
    y hệt trong phần mô tả thì tốn chỗ mà không thêm gì.
    """
    return [{
        "id": e.id,
        "title": e.title,
        "note": e.note,
        "start": e.start,
        "end": e.end,
        "length": _spell(crud.minutes(e.end) - crud.minutes(e.start)) if e.start else "",
    } for e in events]


# ---------- ngày ♥: hai đường thời gian + phần nối ----------

def _window(events) -> tuple:
    """Khung giờ của một ngày, nới ra vừa đủ ôm hết việc của ngày đó."""
    timed = [e for e in events if e.start]

    low = min([crud.minutes(e.start) for e in timed] + [DAY_START])
    high = max([crud.minutes(e.end) for e in timed] + [DAY_END])

    # Bo về đầu giờ tròn cho trục giờ đọc được.
    return low // 60 * 60, -(-high // 60) * 60


def _lanes(events) -> list:
    """Chia việc chồng giờ nhau thành các làn cạnh nhau.

    Không có bước này thì hai việc trùng giờ nằm đè lên nhau và cái dưới biến
    mất hẳn. Mỗi cụm việc dính nhau tự tính số làn của riêng nó, nên một ngày
    có đúng một chỗ trùng không làm cả cột hẹp lại.

    Trả về [(việc, làn, tổng số làn của cụm)]. `events` phải sắp theo giờ bắt đầu.
    """
    out, lanes, cluster = [], [], []

    def close():
        out.extend((item, lane, len(lanes)) for item, lane in cluster)

    for event in events:
        start, end = crud.minutes(event.start), crud.minutes(event.end)

        # Không dính vào việc nào của cụm đang mở nữa: chốt cụm, mở cụm mới.
        if lanes and start >= max(lanes):
            close()
            lanes, cluster = [], []

        for i, lane_end in enumerate(lanes):
            if start >= lane_end:
                lanes[i] = end
                cluster.append((event, i))
                break
        else:
            lanes.append(end)
            cluster.append((event, len(lanes) - 1))

    close()
    return out


def _blocks(events, top: int, bottom: int) -> list:
    """Xếp việc có giờ thành các ô đặt tuyệt đối trên trục giờ (đơn vị %)."""
    span = bottom - top or 1

    return [{
        "id": e.id,
        "title": e.title,
        "start": e.start,
        "end": e.end,
        "offset": (crud.minutes(e.start) - top) / span * 100,
        "height": (crud.minutes(e.end) - crud.minutes(e.start)) / span * 100,
        "left": lane / total * 100,
        "width": 100 / total,
    } for e, lane, total in _lanes([e for e in events if e.start])]


def _busy(events) -> list:
    """Các khoảng bận, đã gộp những khoảng chồng/dính nhau lại làm một."""
    spans = sorted((crud.minutes(e.start), crud.minutes(e.end))
                   for e in events if e.start)

    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    return merged


def _free(busy, top: int, bottom: int) -> list:
    """Phần bù của `busy` trong khung giờ — những lúc người này rảnh."""
    free, cursor = [], top

    for start, end in busy:
        if start > cursor:
            free.append([cursor, min(start, bottom)])
        cursor = max(cursor, end)

    if cursor < bottom:
        free.append([cursor, bottom])

    return [[a, b] for a, b in free if b > a]


def _overlap(left, right) -> list:
    """Giao của hai danh sách khoảng — cả hai cùng rảnh, hoặc cùng bận."""
    out, i, j = [], 0, 0

    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])

        if end > start:
            out.append([start, end])

        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1

    return out


def _connection(sides, top, bottom) -> dict:
    """Phần nối giữa hai đường thời gian của một ngày ♥.

    Hai thứ đáng nhìn nhất khi so lịch hai đứa với nhau:
      - *rảnh cùng nhau*: cả hai đều trống, đủ dài để rủ nhau đi đâu đó;
      - *bận cùng lúc*: cả hai đều kín, biết trước mà khỏi rủ.
    """
    span = bottom - top or 1

    def band(pairs, kind, label):
        return [{
            "kind": kind,
            "label": label,
            "from": crud.hhmm(a),
            "to": crud.hhmm(b),
            "offset": (a - top) / span * 100,
            "height": (b - a) / span * 100,
        } for a, b in pairs]

    busy = [_busy(side) for side in sides]
    free = [_free(b, top, bottom) for b in busy]

    together = [p for p in _overlap(free[0], free[1]) if p[1] - p[0] >= FREE_MINUTES]
    clashing = _overlap(busy[0], busy[1])

    bands = band(together, "free", "rảnh cùng nhau") + band(clashing, "busy", "cả hai đều bận")
    bands.sort(key=lambda b: b["offset"])

    free_minutes = sum(b - a for a, b in together)
    busy_minutes = sum(b - a for a, b in clashing)

    return {
        "bands": bands,
        "free_minutes": free_minutes,
        "busy_minutes": busy_minutes,
        "free_label": _spell(free_minutes),
        "busy_label": _spell(busy_minutes),
    }


def _hours(top: int, bottom: int) -> list:
    """Vạch giờ của trục dọc."""
    span = bottom - top or 1

    # Không dùng crud.hhmm ở đây: nó kẹp về 23:59 để giờ kết thúc của một việc
    # không tràn sang ngày sau, còn vạch cuối của trục thì phải đọc là 24:00.
    return [{
        "label": f"{m // 60:02d}:{m % 60:02d}",
        "offset": (m - top) / span * 100,
    } for m in range(top, bottom + 1, 60)]


@router.get("/schedule")
def schedule_page(request: Request, month: str = "", open: str = "", msg: str = "",
                  db: Session = Depends(get_db)):
    # valid_month chặn luôn ?month=lung-tung — nếu không, _weeks vỡ ở
    # int(month[:4]) và cả trang thành 500.
    month = crud.valid_month(month or date_cls.today().strftime("%Y-%m"))
    today = date_cls.today().isoformat()
    days = _month_days(month)

    owners = crud.people()
    events = crud.get_events(db, days[0], days[-1])
    specials = crud.get_special_days(db, days[0], days[-1])
    special_dates = {s.date for s in specials}

    # (chủ lịch, ngày) -> việc, dựng một lần rồi dùng lại cho cả lưới lẫn bảng
    # chi tiết — thay vì lọc lại danh sách ở từng ô.
    per_owner_day = {}
    for event in events:
        per_owner_day.setdefault((event.owner, event.date), []).append(event)

    open_key = crud.clean(open, 80)

    boards = []
    for owner in owners:
        per_day = {d: v for (o, d), v in per_owner_day.items() if o == owner}
        chosen = _pick(month, open_key, owner, today)

        boards.append({
            "owner": owner,
            "me": request.state.user and request.state.user["username"] == owner,
            "count": sum(len(v) for v in per_day.values()),
            "weeks": _weeks(month, per_day, special_dates, today),
            "chosen": chosen,
            "panels": [{
                "date": day,
                "label": _label(day),
                "special": next((s.title for s in specials if s.date == day), None),
                # KHÔNG đặt tên khoá này là "items": trong template Jinja sẽ
                # hiểu p.items là phương thức dict.items chứ không phải dữ liệu.
                "events": _items(per_day.get(day, [])),
            } for day in days],
        })

    # Ngày ♥: hai đường thời gian đặt cạnh nhau, ở giữa là phần nối.
    special_days = []
    for special in specials:
        sides = [per_owner_day.get((o, special.date), []) for o in owners]
        top, bottom = _window([e for side in sides for e in side])

        special_days.append({
            "date": special.date,
            "title": special.title,
            "label": _label(special.date),
            "hours": _hours(top, bottom),
            "lines": [{
                "owner": owner,
                "blocks": _blocks(sides[i], top, bottom),
            } for i, owner in enumerate(owners)],
            "link": _connection(sides if len(owners) == 2 else [[], []], top, bottom),
        })

    return templates.TemplateResponse(request, "schedule.html", {
        "bg": "bgfood.mp4",
        "month": month,
        "month_label": f"Tháng {int(month[5:7])}, {month[:4]}",
        "prev_month": _shift(month, -1),
        "next_month": _shift(month, 1),
        "this_month": date_cls.today().strftime("%Y-%m"),
        "today": today,
        "weekdays": WEEKDAYS,
        "boards": boards,
        "special_days": special_days,
        "open_key": open_key,
        "msg": crud.clean(msg, 200),
    })


@router.post("/schedule/add")
def add_event(owner: str = Form(...),
              date: str = Form(""),
              title: str = Form(""),
              start: str = Form(""),
              end: str = Form(""),
              note: str = Form(""),
              db: Session = Depends(get_db)):

    date = crud.valid_date(date)
    event = crud.create_event(db, owner, date, title, start, end, note)

    if not event:
        return _back(date[:7], f"{owner}:{date}",
                     "Cần tên lịch có thật và một tiêu đề nha")

    return _back(event.date[:7], f"{event.owner}:{event.date}")


@router.post("/schedule/edit/{id}")
def edit_event(id: int,
               title: str = Form(""),
               start: str = Form(""),
               end: str = Form(""),
               note: str = Form(""),
               db: Session = Depends(get_db)):

    item = crud.get_event(db, id)

    if not item:
        return _back(msg="Việc này không còn nữa")

    key, month = f"{item.owner}:{item.date}", item.date[:7]

    if not crud.update_event(db, id, title, start, end, note):
        return _back(month, key, "Tiêu đề không được để trống")

    return _back(month, key)


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/schedule/delete/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    item = crud.get_event(db, id)
    key, month = (f"{item.owner}:{item.date}", item.date[:7]) if item else ("", "")

    crud.delete_event(db, id)

    return _back(month, key)


@router.post("/schedule/special")
def toggle_special(date: str = Form(""), title: str = Form(""),
                   db: Session = Depends(get_db)):
    """Bật/tắt dấu ♥ cho một ngày — ngày của cả hai, ai bật cũng được."""
    date = crud.valid_date(date)
    crud.toggle_special_day(db, date, title)

    return _back(date[:7], f"{crud.people()[0]}:{date}" if crud.people() else "")
