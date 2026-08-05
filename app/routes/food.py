from fastapi import APIRouter, Request, Form, Body, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud, models

router = APIRouter()


@router.get("/food")
def food_page(request: Request, db: Session = Depends(get_db)):
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
             image: str = Form(""),
             rating: int = Form(0),
             status: str = Form("muon_an"),
             db: Session = Depends(get_db)):

    crud.create_food(db, name, address, note, status, image, rating)

    return RedirectResponse("/food", status_code=303)


# 🔥 DELETE
@router.get("/food/delete/{id}")
def delete_food(id: int, db: Session = Depends(get_db)):
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/food", status_code=303)


# 🔥 EDIT PAGE
@router.get("/food/edit/{id}")
def edit_food_page(request: Request, id: int, db: Session = Depends(get_db)):
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
                image: str = Form(""),
                rating: int = Form(0),
                status: str = Form("muon_an"),
                db: Session = Depends(get_db)):

    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        item.name = name
        item.address = address
        item.note = note
        item.image = image
        item.rating = rating
        item.status = status
        db.commit()

    return RedirectResponse("/food", status_code=303)


@router.post("/food/update-status/{id}")
def update_status(id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    item = db.query(models.FoodPlace).filter(models.FoodPlace.id == id).first()

    if item:
        item.status = data.get("status")
        db.commit()

    return {"success": True}
