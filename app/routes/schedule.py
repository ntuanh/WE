"""Thời gian biểu — mỗi đứa một bảng tuần, ngày ♥ thì ghép hai bên lại."""

from datetime import date as date_cls, timedelta
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

# Khung giờ luôn hiện, kể cả tuần trống. Có việc sớm hơn / muộn hơn thì khung
# tự nới ra vừa đủ, chứ không kéo dài 00:00-24:00 làm bảng cao vô ích.
DAY_START = 7 * 60
DAY_END = 22 * 60

# Ô trống chung phải rộng hơn chừng này mới đáng gọi là "rảnh cùng nhau" —
# hở 10 phút giữa hai việc thì rủ nhau đi đâu được.
FREE_MINUTES = 45


def _back(monday: str = "", open_key: str = "", msg: str = "") -> RedirectResponse:
    """Về lại /schedule, giữ nguyên tuần và mở lại đúng ngày vừa thao tác."""
    parts = []

    if monday:
        parts.append(f"week={quote(monday)}")
    if open_key:
        parts.append(f"open={quote(open_key)}")
    if msg:
        parts.append(f"msg={quote(msg)}")

    return RedirectResponse("/schedule" + ("?" + "&".join(parts) if parts else ""),
                            status_code=303)


def _shift(monday: str, weeks: int) -> str:
    day = date_cls.fromisoformat(monday) + timedelta(weeks=weeks)
    return day.isoformat()


def _label(iso: str) -> str:
    day = date_cls.fromisoformat(iso)
    return f"{DAY_NAMES[day.weekday()]}, {day.day:02d}/{day.month:02d}"


def _window(events) -> tuple:
    """Khung giờ hiển thị, nới ra vừa đủ ôm hết việc của tuần."""
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
        "note": e.note,
        "start": e.start,
        "end": e.end,
        "date": e.date,
        "owner": e.owner,
        "offset": (crud.minutes(e.start) - top) / span * 100,
        "height": (crud.minutes(e.end) - crud.minutes(e.start)) / span * 100,
        "left": lane / total * 100,
        "width": 100 / total,
    } for e, lane, total in _lanes([e for e in events if e.start])]


def _grid(events, days, top, bottom) -> list:
    """Bảy cột ngày, mỗi cột là các ô việc + phần việc cả ngày ở trên đầu."""
    today = date_cls.today().isoformat()

    return [{
        "date": day,
        "weekday": WEEKDAYS[i],
        "day": int(day[8:10]),
        "month": int(day[5:7]),
        "today": day == today,
        "label": _label(day),
        "allday": [e for e in events if e.date == day and not e.start],
        "blocks": _blocks([e for e in events if e.date == day], top, bottom),
    } for i, day in enumerate(days)]


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


def _spell(total: int) -> str:
    """90 -> "1 tiếng 30 phút" — đọc nhanh hơn là "90 phút"."""
    if total <= 0:
        return "không có lúc nào"

    hours, mins = divmod(total, 60)
    parts = ([f"{hours} tiếng"] if hours else []) + ([f"{mins} phút"] if mins else [])

    return " ".join(parts)


def _connection(events_by_owner, owners, top, bottom) -> dict:
    """Phần nối giữa hai thời gian biểu của một ngày ♥.

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
            "minutes": b - a,
            "offset": (a - top) / span * 100,
            "height": (b - a) / span * 100,
        } for a, b in pairs]

    busy = [_busy(events_by_owner.get(o, [])) for o in owners]
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
def schedule_page(request: Request, week: str = "", open: str = "", msg: str = "",
                  db: Session = Depends(get_db)):
    # monday_of đi qua valid_date, nên ?week=lung-tung rơi về tuần này thay vì
    # làm vỡ cả trang ở date.fromisoformat.
    monday = crud.monday_of(week or date_cls.today().isoformat())
    days = crud.week_days(monday)

    owners = crud.people()
    events = crud.get_week_events(db, monday)
    specials = crud.get_special_days(db, days[0], days[-1])

    top, bottom = _window(events)

    by_owner = {}
    for event in events:
        by_owner.setdefault(event.owner, []).append(event)

    boards = [{
        "owner": owner,
        "days": _grid(by_owner.get(owner, []), days, top, bottom),
        "count": len(by_owner.get(owner, [])),
        "me": request.state.user and request.state.user["username"] == owner,
    } for owner in owners]

    # Ngày ♥: hai đường thời gian đặt cạnh nhau, ở giữa là phần nối.
    special_days = []
    for special in specials:
        same_day = {o: [e for e in by_owner.get(o, []) if e.date == special.date]
                    for o in owners}

        special_days.append({
            "date": special.date,
            "title": special.title,
            "label": _label(special.date),
            "lines": [{
                "owner": owner,
                "allday": [e for e in same_day[owner] if not e.start],
                "blocks": _blocks(same_day[owner], top, bottom),
            } for owner in owners],
            "link": _connection(same_day, owners, top, bottom)
                    if len(owners) == 2 else _connection({}, ["", ""], top, bottom),
        })

    return templates.TemplateResponse(request, "schedule.html", {
        "bg": "bgfood.mp4",
        "monday": monday,
        "days": days,
        "week_label": f"{days[0][8:10]}/{days[0][5:7]} – {days[-1][8:10]}/{days[-1][5:7]}"
                      f"/{days[-1][:4]}",
        "prev_week": _shift(monday, -1),
        "next_week": _shift(monday, 1),
        "this_week": crud.monday_of(date_cls.today().isoformat()),
        "today": date_cls.today().isoformat(),
        "weekdays": WEEKDAYS,
        "boards": boards,
        "special_days": special_days,
        "special_dates": {s.date for s in specials},
        "specials_by_date": {s.date: s.title for s in specials},
        "hours": _hours(top, bottom),
        # "chủ lịch:ngày" của ô đang mở — giữ ô mở qua mỗi lần submit form
        "open_key": crud.clean(open, 80),
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
        return _back(crud.monday_of(date), f"{owner}:{date}",
                     "Cần tên lịch có thật và một tiêu đề nha")

    return _back(crud.monday_of(event.date), f"{event.owner}:{event.date}")


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

    key, monday = f"{item.owner}:{item.date}", crud.monday_of(item.date)

    if not crud.update_event(db, id, title, start, end, note):
        return _back(monday, key, "Tiêu đề không được để trống")

    return _back(monday, key)


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/schedule/delete/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    item = crud.get_event(db, id)
    key, monday = ((f"{item.owner}:{item.date}", crud.monday_of(item.date))
                   if item else ("", ""))

    crud.delete_event(db, id)

    return _back(monday, key)


@router.post("/schedule/special")
def toggle_special(date: str = Form(""), title: str = Form(""),
                   db: Session = Depends(get_db)):
    """Bật/tắt dấu ♥ cho một ngày — ngày của cả hai, ai bật cũng được."""
    date = crud.valid_date(date)
    crud.toggle_special_day(db, date, title)

    return _back(crud.monday_of(date))
