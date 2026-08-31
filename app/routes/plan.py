from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud

router = APIRouter()


@router.get("/plan")
def plan_page(request: Request, db: Session = Depends(get_db)):
    plans = crud.get_plans(db)

    return templates.TemplateResponse(request, "plan.html", {
        "plans": plans,
        "priorities": crud.PLAN_PRIORITIES,
        "bg": "bgfood.mp4"
    })


@router.post("/plan/add")
def add_plan(title: str = Form(...),
             script: str = Form(""),
             priority: str = Form("normal"),
             deadline: str = Form(""),
             db: Session = Depends(get_db)):

    crud.create_plan(db, title, script, priority, deadline)

    return RedirectResponse("/plan", status_code=303)


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/plan/delete/{id}")
def delete_plan(id: int, db: Session = Depends(get_db)):
    crud.delete_plan(db, id)

    return RedirectResponse("/plan", status_code=303)


# 🔥 SỬA — trước đây crud.update_plan có mà không route nào gọi tới
@router.get("/plan/edit/{id}")
def edit_plan_page(request: Request, id: int, db: Session = Depends(get_db)):
    item = crud.get_plan(db, id)

    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch này")

    return templates.TemplateResponse(request, "edit_plan.html", {
        "item": item,
        "priorities": crud.PLAN_PRIORITIES,
    })


@router.post("/plan/edit/{id}")
def update_plan(id: int,
                title: str = Form(...),
                script: str = Form(""),
                priority: str = Form("normal"),
                deadline: str = Form(""),
                db: Session = Depends(get_db)):

    if not crud.update_plan(db, id, title, script, priority, deadline):
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch này")

    return RedirectResponse("/plan", status_code=303)


@router.post("/plan/toggle/{id}")
def toggle_plan(id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    item = crud.update_plan_status(db, id, (data or {}).get("done", 0))

    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch này")

    return {"ok": True, "done": item.done}
