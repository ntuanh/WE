from fastapi import APIRouter, Request, Form, Body, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud, models

router = APIRouter()


@router.get("/plan")
def plan_page(request: Request, db: Session = Depends(get_db)):
    plans = crud.get_plans(db)

    return templates.TemplateResponse("plan.html", {
        "request": request,
        "plans": plans,
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


@router.get("/plan/delete/{id}")
def delete_plan(id: int, db: Session = Depends(get_db)):
    item = db.query(models.Plan).filter(models.Plan.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/plan", status_code=303)


@router.post("/plan/toggle/{id}")
def toggle_plan(id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    crud.update_plan_status(db, id, data.get("done", 0))
    return {"ok": True}
