"""Mọi thao tác chạm vào database nằm ở đây.

Nguyên tắc chung của file này: route chỉ nhận dữ liệu từ form rồi gọi xuống,
còn việc *làm sạch và kiểm tra* là ở đây — nhờ vậy không có đường nào lách qua
được, kể cả khi sau này thêm route mới.
"""

from datetime import date as date_cls, time as time_cls, timedelta

from sqlalchemy.orm import Session

from . import auth, models

# ---------- giá trị hợp lệ ----------

FOOD_STATUSES = ("da_an", "muon_an")
PLAN_PRIORITIES = ("low", "normal", "high")

MAX_TEXT = 500          # đủ dài cho ghi chú, đủ ngắn để không ai dán cả cuốn sách
MAX_URL = 2000


def clean(value, limit: int = MAX_TEXT) -> str:
    """Bỏ khoảng trắng thừa và cắt bớt nếu quá dài. None -> chuỗi rỗng."""
    return str(value or "").strip()[:limit]


def _one_of(value, allowed, fallback):
    """Ép về một trong các giá trị cho phép, sai thì lấy mặc định."""
    value = str(value or "").strip()
    return value if value in allowed else fallback


def _clamp_int(value, low, high, fallback=0) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return fallback


def valid_date(value, fallback_today: bool = True) -> str:
    """Chuẩn hoá về dạng YYYY-MM-DD. Sai định dạng thì lấy hôm nay (hoặc rỗng)."""
    text = clean(value, 10)

    try:
        return date_cls.fromisoformat(text).isoformat()
    except ValueError:
        return date_cls.today().isoformat() if fallback_today else ""


def valid_month(value) -> str:
    """Chuẩn hoá về dạng YYYY-MM. Sai thì lấy tháng này."""
    text = clean(value, 7)

    try:
        date_cls.fromisoformat(text + "-01")
        return text
    except ValueError:
        return date_cls.today().strftime("%Y-%m")


# ---------- FOOD ----------

def get_foods(db: Session):
    return db.query(models.FoodPlace).order_by(models.FoodPlace.id.desc()).all()


def get_food(db: Session, id: int):
    return db.get(models.FoodPlace, id)


def create_food(db: Session, name, address, note, status, image="", rating=0):
    food = models.FoodPlace(
        name=clean(name, 200),
        address=clean(address),
        note=clean(note),
        image=clean(image, MAX_URL),
        rating=_clamp_int(rating, 0, 5),
        status=_one_of(status, FOOD_STATUSES, "muon_an"),
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food


def update_food(db: Session, id: int, name, address, note, image, rating, status):
    """Sửa một quán. Trả về bản ghi, hoặc None nếu không có id đó."""
    item = get_food(db, id)
    if not item:
        return None

    item.name = clean(name, 200)
    item.address = clean(address)
    item.note = clean(note)
    item.image = clean(image, MAX_URL)
    item.rating = _clamp_int(rating, 0, 5)
    item.status = _one_of(status, FOOD_STATUSES, item.status)

    db.commit()
    return item


def update_food_status(db: Session, id: int, status):
    """Đổi cột (kéo thả). Trả None nếu id sai, hoặc status không hợp lệ."""
    item = get_food(db, id)
    if not item or status not in FOOD_STATUSES:
        return None

    item.status = status
    db.commit()
    return item


def delete_food(db: Session, id: int) -> bool:
    return _delete(db, models.FoodPlace, id)


# ---------- STUDY ----------

def get_studies(db: Session):
    return db.query(models.StudyPlace).order_by(models.StudyPlace.id.desc()).all()


def get_study(db: Session, id: int):
    return db.get(models.StudyPlace, id)


def create_study(db: Session, name, address, note):
    study = models.StudyPlace(
        name=clean(name, 200),
        address=clean(address),
        note=clean(note),
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


def update_study(db: Session, id: int, name, address, note):
    item = get_study(db, id)
    if not item:
        return None

    item.name = clean(name, 200)
    item.address = clean(address)
    item.note = clean(note)

    db.commit()
    return item


def delete_study(db: Session, id: int) -> bool:
    return _delete(db, models.StudyPlace, id)


# ---------- PLAN ----------

def get_plans(db: Session):
    # chưa xong lên trước, mới nhất lên trên
    return db.query(models.Plan).order_by(models.Plan.done, models.Plan.id.desc()).all()


def get_plan(db: Session, id: int):
    return db.get(models.Plan, id)


def create_plan(db: Session, title, script, priority="normal", deadline=""):
    plan = models.Plan(
        title=clean(title, 200),
        script=clean(script),
        priority=_one_of(priority, PLAN_PRIORITIES, "normal"),
        deadline=valid_date(deadline, fallback_today=False),
        done=0,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan_status(db: Session, id: int, done):
    """Tick / bỏ tick. Trả bản ghi hoặc None."""
    item = get_plan(db, id)
    if not item:
        return None

    item.done = 1 if _clamp_int(done, 0, 1) else 0
    db.commit()
    return item


def update_plan(db: Session, id: int, title, script, priority, deadline):
    item = get_plan(db, id)
    if not item:
        return None

    item.title = clean(title, 200)
    item.script = clean(script)
    item.priority = _one_of(priority, PLAN_PRIORITIES, item.priority)
    item.deadline = valid_date(deadline, fallback_today=False)

    db.commit()
    return item


def delete_plan(db: Session, id: int) -> bool:
    return _delete(db, models.Plan, id)


# ---------- LỊCH ----------

# Việc không ghi giờ kết thúc thì coi như dài chừng này — đủ để thành một ô
# nhìn thấy được trên thời gian biểu, thay vì một vạch mỏng dính.
DEFAULT_MINUTES = 60


def people() -> list:
    """Tên hai chủ lịch, lấy thẳng từ danh sách tài khoản.

    Đọc lúc gọi chứ không phải lúc import: test thay `auth.USERS` bằng tài khoản
    giả, mà tên viết cứng ở đây thì mọi thứ lệch nhau ngay.
    """
    return sorted(auth.USERS)


def valid_time(value) -> str:
    """Chuẩn hoá về "HH:MM". Không đọc được thì trả rỗng = việc cả ngày.

    Không dùng thẳng `time.fromisoformat`: nó đòi đủ hai chữ số, mà trình duyệt
    cũ không có ô chọn giờ thì cho gõ tay — "8:5" cũng phải hiểu là 08:05.
    """
    parts = clean(value, 8).split(":")

    try:
        return time_cls(int(parts[0]), int(parts[1])).strftime("%H:%M")
    except (IndexError, ValueError):
        return ""


def minutes(hhmm: str) -> int:
    """"08:30" -> 510. Chuỗi rỗng hoặc hỏng -> 0."""
    parts = clean(hhmm, 5).split(":")

    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (IndexError, ValueError):
        return 0


def hhmm(total: int) -> str:
    """510 -> "08:30". Kẹp trong một ngày để không đẻ ra "25:10"."""
    total = max(0, min(int(total), 24 * 60 - 1))
    return f"{total // 60:02d}:{total % 60:02d}"


def _span(start: str, end: str) -> tuple:
    """Cặp (giờ bắt đầu, giờ kết thúc) đã hợp lệ hoá.

    Kết thúc trước hoặc bằng bắt đầu là gõ nhầm — đẩy thành một tiếng sau, chứ
    để nguyên thì ô việc có chiều cao âm và thời gian biểu vỡ hình.
    """
    start = valid_time(start)

    if not start:
        return "", ""          # việc cả ngày: không nằm trên trục giờ

    end = valid_time(end)

    if not end or minutes(end) <= minutes(start):
        end = hhmm(minutes(start) + DEFAULT_MINUTES)

    return start, end


def monday_of(value) -> str:
    """Thứ 2 của tuần chứa ngày này, dạng YYYY-MM-DD."""
    day = date_cls.fromisoformat(valid_date(value))
    return (day - timedelta(days=day.weekday())).isoformat()


def week_days(monday: str) -> list:
    """Bảy ngày của tuần bắt đầu từ `monday`."""
    first = date_cls.fromisoformat(monday_of(monday))
    return [(first + timedelta(days=i)).isoformat() for i in range(7)]


def get_events(db: Session, start_date: str, end_date: str, owner: str = ""):
    """Việc trong khoảng ngày [start_date, end_date], sớm nhất lên trước.

    Ngày lưu dạng chuỗi YYYY-MM-DD nên so sánh chuỗi cũng chính là so sánh ngày
    — chạy giống nhau trên SQLite lẫn Postgres. Việc không có giờ ("") xếp lên
    đầu ngày, coi như việc cả ngày.
    """
    query = (db.query(models.ScheduleEvent)
               .filter(models.ScheduleEvent.date >= valid_date(start_date),
                       models.ScheduleEvent.date <= valid_date(end_date)))

    if owner:
        query = query.filter(models.ScheduleEvent.owner == owner)

    return query.order_by(models.ScheduleEvent.date,
                          models.ScheduleEvent.start,
                          models.ScheduleEvent.id).all()


def get_week_events(db: Session, monday: str, owner: str = ""):
    days = week_days(monday)
    return get_events(db, days[0], days[-1], owner)


def get_event(db: Session, id: int):
    return db.get(models.ScheduleEvent, id)


def create_event(db: Session, owner, date, title, start="", end="", note=""):
    """Thêm một việc. Trả None nếu chủ lịch không phải người có tài khoản.

    Ở đây *không* dùng `_one_of` để đẩy về giá trị mặc định như chỗ khác: gõ sai
    tên mà lẳng lặng nhét vào lịch người kia thì tai hại hơn là báo lỗi.
    """
    owner = clean(owner, 50).lower()
    title = clean(title, 200)

    if owner not in people() or not title:
        return None

    start, end = _span(start, end)

    event = models.ScheduleEvent(
        owner=owner,
        date=valid_date(date),
        start=start,
        end=end,
        title=title,
        note=clean(note),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, id: int, title, start, end, note):
    """Sửa nội dung một việc — không cho đổi chủ lịch hay ngày ở đây."""
    item = get_event(db, id)
    if not item:
        return None

    title = clean(title, 200)
    if not title:
        return None

    item.title = title
    item.start, item.end = _span(start, end)
    item.note = clean(note)

    db.commit()
    return item


def delete_event(db: Session, id: int) -> bool:
    return _delete(db, models.ScheduleEvent, id)


# ---------- NGÀY ĐẶC BIỆT ----------

def get_special_days(db: Session, start_date: str, end_date: str):
    """Các ngày ♥ trong khoảng, sớm nhất trước."""
    return (db.query(models.SpecialDay)
              .filter(models.SpecialDay.date >= valid_date(start_date),
                      models.SpecialDay.date <= valid_date(end_date))
              .order_by(models.SpecialDay.date)
              .all())


def get_special_day(db: Session, date: str):
    return (db.query(models.SpecialDay)
              .filter(models.SpecialDay.date == valid_date(date))
              .first())


def toggle_special_day(db: Session, date: str, title=""):
    """Bật/tắt dấu ♥ cho một ngày. Trả bản ghi mới, hoặc None khi vừa tắt.

    Đánh dấu lại một ngày đã ♥ mà có gõ tên mới thì hiểu là *đổi tên*, không
    phải tắt đi — bấm nhầm nút xoá mất tên vừa gõ thì ức chế.
    """
    date = valid_date(date)
    title = clean(title, 200)

    item = get_special_day(db, date)

    if item:
        if title and title != item.title:
            item.title = title
            db.commit()
            return item

        db.delete(item)
        db.commit()
        return None

    item = models.SpecialDay(date=date, title=title)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---------- dùng chung ----------

def _delete(db: Session, model, id: int) -> bool:
    """Xoá theo id. True nếu có xoá thật, False nếu không tìm thấy."""
    item = db.get(model, id)
    if not item:
        return False

    db.delete(item)
    db.commit()
    return True
