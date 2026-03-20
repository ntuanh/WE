from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app.database import SessionLocal
from app import crud, models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/food")
def food_page(request: Request):
    db = SessionLocal()
    foods = crud.get_foods(db)

    return templates.TemplateResponse("food.html", {
        "request": request,
        "foods": foods,
        "bg": "bgfood.mp4"
    })


@router.post("/food/add")
def add_food(name: str = Form(...),
             address: str = Form(...),
             note: str = Form(""),
             status: str = Form(...)):

    db = SessionLocal()
    crud.create_food(db, name, address, note, status)

    return RedirectResponse("/food", status_code=303)


# 🔥 DELETE
@router.get("/food/delete/{id}")
def delete_food(id: int):
    db = SessionLocal()
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/food", status_code=303)


# 🔥 EDIT PAGE
@router.get("/food/edit/{id}")
def edit_food_page(request: Request, id: int):
    db = SessionLocal()
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    return templates.TemplateResponse("edit_food.html", {
        "request": request,
        "item": item
    })


# 🔥 UPDATE
@router.post("/food/edit/{id}")
def update_food(id: int,
                name: str = Form(...),
                address: str = Form(...),
                note: str = Form(""),
                status: str = Form(...)):

    db = SessionLocal()
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        item.name = name
        item.address = address
        item.note = note
        item.status = status
        db.commit()

    return RedirectResponse("/food", status_code=303)

from fastapi import Body

@router.post("/food/update-status/{id}")
def update_status(id: int, data: dict = Body(...)):
    db = SessionLocal()
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        item.status = data.get("status")
        db.commit()

    return {"success": True}