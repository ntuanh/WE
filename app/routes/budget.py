import calendar
import math
from datetime import date as date_cls
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud, momo

router = APIRouter()

DONUT_R = 54
DONUT_C = 2 * math.pi * DONUT_R

# Sao kê một tháng chỉ vài chục KB; chặn ở đây để không ai nạp file 1 GB vào RAM.
MAX_UPLOAD = 5 * 1024 * 1024


def _back(month: str = "", msg: str = "") -> RedirectResponse:
    """Về lại trang /budget đúng tháng, kèm lời nhắn nếu có."""
    url = "/budget"

    if month:
        url += f"?month={quote(month)}"
    if msg:
        url += ("&" if month else "?") + f"msg={quote(msg)}"

    return RedirectResponse(url, status_code=303)


def _summarise(txs, budget_amount, month):
    """Số liệu cho phần biểu đồ: tổng chi/thu, vòng tròn hạng mục, cột theo ngày."""
    spent = sum(t.amount for t in txs if t.kind == "out")
    earned = sum(t.amount for t in txs if t.kind == "in")

    # vòng tròn theo hạng mục — mỗi cung là một đoạn của cùng đường tròn
    per_cat = {}
    for t in txs:
        if t.kind == "out":
            per_cat[t.category] = per_cat.get(t.category, 0) + t.amount

    slices, offset = [], 0.0
    for key, amount in sorted(per_cat.items(), key=lambda kv: -kv[1]):
        label, color = momo.CATEGORIES.get(key, momo.CATEGORIES["khac"])
        share = amount / spent if spent else 0
        slices.append({
            "key": key,
            "label": label,
            "color": color,
            "amount": amount,
            "percent": round(share * 100),
            "dash": share * DONUT_C,
            "gap": DONUT_C - share * DONUT_C,
            "offset": -offset,
        })
        offset += share * DONUT_C

    # cột theo ngày trong tháng
    per_day = {}
    for t in txs:
        if t.kind == "out" and len(t.date) == 10:
            day = int(t.date[8:10])
            per_day[day] = per_day.get(day, 0) + t.amount

    peak = max(per_day.values()) if per_day else 0
    last_day = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
    days = [{
        "day": d,
        "amount": per_day.get(d, 0),
        "height": round(per_day.get(d, 0) / peak * 100) if peak else 0,
    } for d in range(1, last_day + 1)]

    return {
        "spent": spent,
        "earned": earned,
        "left": budget_amount - spent,
        "used_percent": round(spent / budget_amount * 100) if budget_amount else 0,
        "slices": slices,
        "days": days,
        "peak": peak,
        "count": len(txs),
    }


@router.get("/budget")
def budget_page(request: Request, month: str = "", msg: str = "",
                db: Session = Depends(get_db)):
    # valid_month chặn luôn ?month=lung-tung — nếu không, _summarise sẽ vỡ ở
    # int(month[:4]) và cả trang thành 500.
    month = crud.valid_month(month or date_cls.today().strftime("%Y-%m"))

    txs = crud.get_transactions(db, month)
    budget = crud.get_budget(db, month)
    budget_amount = budget.amount if budget else 0

    months = crud.get_months(db)
    if month not in months:
        months = sorted(set(months) | {month}, reverse=True)

    return templates.TemplateResponse(request, "budget.html", {
        "bg": "bgfood.mp4",
        "month": month,
        "months": months,
        "txs": txs,
        "budget": budget_amount,
        "categories": momo.CATEGORIES,
        "stats": _summarise(txs, budget_amount, month),
        "msg": crud.clean(msg, 200),
        "donut_c": DONUT_C,
        "donut_r": DONUT_R,
    })


@router.post("/budget/add")
def add_transaction(amount: str = Form(""),
                    kind: str = Form("out"),
                    category: str = Form("khac"),
                    note: str = Form(""),
                    date: str = Form(""),
                    source: str = Form("momo"),
                    db: Session = Depends(get_db)):
    """amount nhận dạng chuỗi rồi tự kiểm tra, thay vì để FastAPI trả 422 —
    gõ nhầm một chữ mà văng ra trang lỗi trắng thì khó chịu."""
    date = crud.valid_date(date)

    try:
        value = int(str(amount).strip().replace(".", "").replace(",", "") or 0)
    except ValueError:
        value = 0

    if value <= 0:
        return _back(date[:7], "Số tiền phải là số lớn hơn 0 nha")

    crud.create_transaction(db, value, kind, category, note, date, source)

    return _back(date[:7])


@router.post("/budget/set")
def set_budget(month: str = Form(...), amount: int = Form(0),
               db: Session = Depends(get_db)):

    month = crud.valid_month(month)
    crud.set_budget(db, month, amount)

    return _back(month)


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/budget/delete/{id}")
def delete_transaction(id: int, db: Session = Depends(get_db)):
    item = crud.get_transaction(db, id)
    month = item.date[:7] if item else ""

    crud.delete_transaction(db, id)

    return _back(month)


@router.post("/budget/import")
async def import_momo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload file sao kê MoMo (CSV). Xem app/momo.py để biết cách lấy file."""
    data = await file.read(MAX_UPLOAD + 1)

    if len(data) > MAX_UPLOAD:
        return _back("", "File lớn quá (giới hạn 5 MB) — thử xuất sao kê từng tháng")

    rows = momo.parse_csv(data)

    if not rows:
        return _back("", "Không đọc được giao dịch nào trong file — cần bản CSV sao kê MoMo")

    added, skipped = crud.import_transactions(db, rows)
    month = max(r["date"] for r in rows)[:7]

    return _back(month, f"Đã nhập {added} giao dịch, bỏ qua {skipped} cái trùng")
