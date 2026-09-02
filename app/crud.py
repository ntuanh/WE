"""Mọi thao tác chạm vào database nằm ở đây.

Nguyên tắc chung của file này: route chỉ nhận dữ liệu từ form rồi gọi xuống,
còn việc *làm sạch và kiểm tra* là ở đây — nhờ vậy không có đường nào lách qua
được, kể cả khi sau này thêm route mới.
"""

from datetime import date as date_cls

from sqlalchemy.orm import Session

from . import models

# ---------- giá trị hợp lệ ----------

FOOD_STATUSES = ("da_an", "muon_an")
PLAN_PRIORITIES = ("low", "normal", "high")
TX_KINDS = ("out", "in")
TX_SOURCES = ("momo", "tien_mat", "bank")
TX_CATEGORIES = ("an", "di_lai", "mua_sam", "hoa_don", "giai_tri", "khac")

MAX_TEXT = 500          # đủ dài cho ghi chú, đủ ngắn để không ai dán cả cuốn sách
MAX_URL = 2000
MAX_AMOUNT = 10 ** 15   # chặn số vô lý làm tràn cột BigInteger


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


# ---------- MONEY ----------

def get_transactions(db: Session, month: str):
    """Giao dịch của một tháng YYYY-MM, mới nhất lên trên.

    Ngày lưu dạng chuỗi nên lọc bằng LIKE — chạy giống nhau trên SQLite lẫn Postgres.
    """
    return (db.query(models.Transaction)
              .filter(models.Transaction.date.like(f"{valid_month(month)}-%"))
              .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
              .all())


def get_transaction(db: Session, id: int):
    return db.get(models.Transaction, id)


def create_transaction(db: Session, amount, kind, category, note, date,
                       source="tien_mat", ref=""):
    tx = models.Transaction(
        amount=_clamp_int(amount, 0, MAX_AMOUNT),
        kind=_one_of(kind, TX_KINDS, "out"),
        category=_one_of(category, TX_CATEGORIES, "khac"),
        note=clean(note),
        date=valid_date(date),
        source=_one_of(source, TX_SOURCES, "tien_mat"),
        ref=clean(ref, 100),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, id: int) -> bool:
    return _delete(db, models.Transaction, id)


def import_transactions(db: Session, rows):
    """Ghi các dòng đọc từ sao kê MoMo. Trả (số thêm mới, số bỏ qua vì trùng).

    Trùng = cùng mã giao dịch MoMo, hoặc cùng ngày + số tiền + mô tả khi sao kê
    không có mã — nhờ vậy import lại đúng file cũ không nhân đôi chi tiêu.

    Đọc sẵn khoá của các giao dịch đã có thành một tập hợp rồi mới duyệt, thay
    vì bắn một câu SELECT cho mỗi dòng: file sao kê vài trăm dòng là thấy khác.
    """
    # Làm sạch trước, so trùng sau. Nếu so bằng dữ liệu thô rồi mới chuẩn hoá
    # lúc ghi, khoá đem đi so sẽ khác giá trị nằm trong DB — lần import sau
    # không nhận ra dòng cũ và ghi lại lần nữa.
    sach = [{
        "amount": _clamp_int(r.get("amount"), 0, MAX_AMOUNT),
        "kind": _one_of(r.get("kind"), TX_KINDS, "out"),
        "category": _one_of(r.get("category"), TX_CATEGORIES, "khac"),
        "note": clean(r.get("note")),
        "date": valid_date(r.get("date")),
        "source": _one_of(r.get("source"), TX_SOURCES, "momo"),
        "ref": clean(r.get("ref"), 100),
    } for r in (rows or [])]

    if not sach:
        return 0, 0

    months = {r["date"][:7] for r in sach}

    existing = (db.query(models.Transaction)
                  .filter(models.Transaction.date >= min(months) + "-01",
                          models.Transaction.date <= max(months) + "-31")
                  .all())

    seen_refs = {t.ref for t in existing if t.ref}
    seen_rows = {(t.date, t.amount, t.note) for t in existing}

    added = skipped = 0

    for row in sach:
        ref = row["ref"]
        key = (row["date"], row["amount"], row["note"])

        # trùng với DB, hoặc trùng với một dòng vừa xử lý trong chính file này
        if (ref and ref in seen_refs) or (not ref and key in seen_rows):
            skipped += 1
            continue

        db.add(models.Transaction(**row))

        if ref:
            seen_refs.add(ref)
        seen_rows.add(key)
        added += 1

    db.commit()
    return added, skipped


def get_budget(db: Session, month: str):
    return (db.query(models.Budget)
              .filter(models.Budget.month == valid_month(month))
              .first())


def set_budget(db: Session, month: str, amount):
    month = valid_month(month)
    amount = _clamp_int(amount, 0, MAX_AMOUNT)

    item = get_budget(db, month)
    if item:
        item.amount = amount
    else:
        item = models.Budget(month=month, amount=amount)
        db.add(item)

    db.commit()
    return item


def get_months(db: Session):
    """Các tháng đã có giao dịch, mới nhất trước — để đổ vào ô chọn tháng."""
    rows = db.query(models.Transaction.date).distinct().all()
    months = {r[0][:7] for r in rows if r[0] and len(r[0]) >= 7}
    return sorted(months, reverse=True)


# ---------- dùng chung ----------

def _delete(db: Session, model, id: int) -> bool:
    """Xoá theo id. True nếu có xoá thật, False nếu không tìm thấy."""
    item = db.get(model, id)
    if not item:
        return False

    db.delete(item)
    db.commit()
    return True
