"""Lịch chung — mỗi đứa một cuốn, xem cạnh nhau cho dễ hẹn."""

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


def _grid(month: str, events, today: str) -> list:
    """Xếp các mục của một người vào lưới tuần × 7 ngày của tháng.

    Ô của tháng khác (phần đệm đầu/cuối lưới) để trơ: bấm vào thêm việc ở đó
    thì thêm xong lại không thấy nó đâu, vì đã sang tháng khác mất rồi.
    """
    year, mon = int(month[:4]), int(month[5:7])

    per_day = {}
    for event in events:
        per_day.setdefault(event.date, []).append(event)

    return [[{
        "date": day.isoformat(),
        "day": day.day,
        "in_month": day.month == mon,
        "today": day.isoformat() == today,
        "label": f"{DAY_NAMES[day.weekday()]}, {day.day:02d}/{day.month:02d}",
        "events": per_day.get(day.isoformat(), []) if day.month == mon else [],
    } for day in week] for week in _cal.monthdatescalendar(year, mon)]


@router.get("/schedule")
def schedule_page(request: Request, month: str = "", open: str = "", msg: str = "",
                  db: Session = Depends(get_db)):
    # valid_month chặn luôn ?month=lung-tung — nếu không, _grid vỡ ở int(month[:4])
    # và cả trang thành 500.
    month = crud.valid_month(month or date_cls.today().strftime("%Y-%m"))
    today = date_cls.today().isoformat()

    events = crud.get_events(db, month)

    calendars = [{
        "owner": owner,
        "weeks": _grid(month, [e for e in events if e.owner == owner], today),
        "count": sum(1 for e in events if e.owner == owner),
        "me": request.state.user and request.state.user["username"] == owner,
    } for owner in crud.people()]

    return templates.TemplateResponse(request, "schedule.html", {
        "bg": "bgfood.mp4",
        "month": month,
        "month_label": f"Tháng {int(month[5:7])} / {month[:4]}",
        "prev_month": _shift(month, -1),
        "next_month": _shift(month, 1),
        "this_month": date_cls.today().strftime("%Y-%m"),
        "today": today,
        "weekdays": WEEKDAYS,
        "calendars": calendars,
        # "chủ lịch:ngày" của ô đang mở — giữ ô mở qua mỗi lần submit form
        "open_key": crud.clean(open, 80),
        "msg": crud.clean(msg, 200),
    })


@router.post("/schedule/add")
def add_event(owner: str = Form(...),
              date: str = Form(""),
              title: str = Form(""),
              start: str = Form(""),
              note: str = Form(""),
              db: Session = Depends(get_db)):

    date = crud.valid_date(date)
    event = crud.create_event(db, owner, date, title, start, note)

    if not event:
        return _back(date[:7], f"{owner}:{date}",
                     "Cần tên lịch có thật và một tiêu đề nha")

    return _back(date[:7], f"{event.owner}:{event.date}")


@router.post("/schedule/edit/{id}")
def edit_event(id: int,
               title: str = Form(""),
               start: str = Form(""),
               note: str = Form(""),
               db: Session = Depends(get_db)):

    item = crud.get_event(db, id)

    if not item:
        return _back(msg="Mục này không còn nữa")

    key, month = f"{item.owner}:{item.date}", item.date[:7]

    if not crud.update_event(db, id, title, start, note):
        return _back(month, key, "Tiêu đề không được để trống")

    return _back(month, key)


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/schedule/delete/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    item = crud.get_event(db, id)
    key, month = (f"{item.owner}:{item.date}", item.date[:7]) if item else ("", "")

    crud.delete_event(db, id)

    return _back(month, key)
