from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud, models

router = APIRouter()


@router.get("/study")
def study_page(request: Request, db: Session = Depends(get_db)):
    studies = crud.get_studies(db)

    return templates.TemplateResponse("study.html", {
        "request": request,
        "studies": studies,
        "bg": "bghome.mp4"
    })


@router.post("/study/add")
def add_study(name: str = Form(...),
              address: str = Form(...),
              note: str = Form(""),
              db: Session = Depends(get_db)):

    crud.create_study(db, name, address, note)

    return RedirectResponse("/study", status_code=303)


@router.get("/study/delete/{id}")
def delete_study(id: int, db: Session = Depends(get_db)):
    item = db.query(models.StudyPlace).filter(models.StudyPlace.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse("/study", status_code=303)


# 🔥 SHOW FORM EDIT
@router.get("/study/edit/{id}")
def edit_study_page(request: Request, id: int, db: Session = Depends(get_db)):
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
                 note: str = Form(""),
                 db: Session = Depends(get_db)):

    item = db.query(models.StudyPlace).filter(models.StudyPlace.id == id).first()

    if item:
        item.name = name
        item.address = address
        item.note = note
        db.commit()

    return RedirectResponse("/study", status_code=303)
