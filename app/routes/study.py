from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from app.database import SessionLocal
from app import crud, models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/study")
def study_page(request: Request):
    db = SessionLocal()
    studies = crud.get_studies(db)

    return templates.TemplateResponse("study.html", {
        "request": request,
        "studies": studies,
        "bg": "bghome.mp4"
    })

@router.post("/study/add")
def add_study(name: str = Form(...),
              address: str = Form(...),
              note: str = Form("")):

    db = SessionLocal()
    crud.create_study(db, name, address, note)

    return RedirectResponse("/study", status_code=303)


@router.get("/study/delete/{id}")
def delete_study(id: int):
    db = SessionLocal()
    item = db.query(models.StudyPlace).filter(models.StudyPlace.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/study", status_code=303)

# 🔥 SHOW FORM EDIT
@router.get("/study/edit/{id}")
def edit_study_page(request: Request, id: int):
    db = SessionLocal()
    item = db.query(models.StudyPlace).filter(models.StudyPlace.id == id).first()

    return templates.TemplateResponse("edit_study.html", {
        "request": request,
        "item": item
    })


# 🔥 UPDATE DATA
@router.post("/study/edit/{id}")
def update_study(id: int,
                 name: str = Form(...),
                 address: str = Form(...),
                 note: str = Form("")):

    db = SessionLocal()
    item = db.query(models.StudyPlace).filter(models.StudyPlace.id == id).first()

    if item:
        item.name = name
        item.address = address
        item.note = note
        db.commit()

    return RedirectResponse("/study", status_code=303)