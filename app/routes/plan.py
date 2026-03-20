from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi import Body

from app.database import SessionLocal
from app import crud, models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/plan")
def plan_page(request: Request):
    db = SessionLocal()
    plans = crud.get_plans(db)

    return templates.TemplateResponse("plan.html", {
        "request": request,
        "plans": plans,
        "bg": "bgfood.mp4"
    })


@router.post("/plan/add")
def add_plan(title: str = Form(...), script: str = Form(...)):
    db = SessionLocal()
    crud.create_plan(db, title, script)

    return RedirectResponse("/plan", status_code=303)


@router.get("/plan/delete/{id}")
def delete_plan(id: int):
    db = SessionLocal()
    item = db.query(models.Plan).filter(models.Plan.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/plan", status_code=303)

@router.post("/plan/toggle/{id}")
def toggle_plan(id: int, data: dict = Body(...)):
    db = SessionLocal()
    crud.update_plan_status(db, id, data.get("done"))
    return {"ok": True}