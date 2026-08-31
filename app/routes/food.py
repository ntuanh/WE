from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud

router = APIRouter()


@router.get("/food")
def food_page(request: Request, db: Session = Depends(get_db)):
    foods = crud.get_foods(db)

    return templates.TemplateResponse(request, "food.html", {
        "foods": foods,
        "statuses": crud.FOOD_STATUSES,
        "bg": "bgfood.mp4"
    })


@router.post("/food/add")
def add_food(name: str = Form(...),
             address: str = Form(...),
             note: str = Form(""),
             image: str = Form(""),
             rating: int = Form(0),
             status: str = Form("muon_an"),
             db: Session = Depends(get_db)):

    crud.create_food(db, name, address, note, status, image, rating)

    return RedirectResponse("/food", status_code=303)


# 🔥 DELETE — POST chứ không phải GET: link xoá bằng GET có thể bị trình duyệt
# tự nạp trước (prefetch) và xoá mất dữ liệu mà không ai bấm gì cả.
@router.post("/food/delete/{id}")
def delete_food(id: int, db: Session = Depends(get_db)):
    crud.delete_food(db, id)

    return RedirectResponse("/food", status_code=303)


# 🔥 EDIT PAGE
@router.get("/food/edit/{id}")
def edit_food_page(request: Request, id: int, db: Session = Depends(get_db)):
    item = crud.get_food(db, id)

    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy quán này")

    return templates.TemplateResponse(request, "edit_food.html", {
        "item": item
    })


# 🔥 UPDATE
@router.post("/food/edit/{id}")
def update_food(id: int,
                name: str = Form(...),
                address: str = Form(...),
                note: str = Form(""),
                image: str = Form(""),
                rating: int = Form(0),
                status: str = Form("muon_an"),
                db: Session = Depends(get_db)):

    if not crud.update_food(db, id, name, address, note, image, rating, status):
        raise HTTPException(status_code=404, detail="Không tìm thấy quán này")

    return RedirectResponse("/food", status_code=303)


@router.post("/food/update-status/{id}")
def update_status(id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Kéo thả sang cột khác. Trả về trạng thái thật sau khi lưu để JS biết
    có nên trả thẻ về chỗ cũ không."""
    item = crud.update_food_status(db, id, (data or {}).get("status"))

    if not item:
        raise HTTPException(status_code=400, detail="Id hoặc trạng thái không hợp lệ")

    return {"success": True, "status": item.status}
