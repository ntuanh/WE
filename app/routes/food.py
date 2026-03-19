from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse

from app.database import SessionLocal
from app import crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/food")
def food_page(request: Request):
    db = SessionLocal()
    foods = crud.get_foods(db)

    return templates.TemplateResponse("food.html", {
        "request": request,
        "foods": foods
    })


@router.post("/food/add")
def add_food(name: str = Form(...),
             address: str = Form(...),
             note: str = Form(""),
             status: str = Form(...)):

    db = SessionLocal()
    crud.create_food(db, name, address, note, status)

    return RedirectResponse("/food", status_code=303)