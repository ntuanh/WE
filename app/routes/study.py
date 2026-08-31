from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.templating import templates
from app import crud

router = APIRouter()


@router.get("/study")
def study_page(request: Request, db: Session = Depends(get_db)):
    studies = crud.get_studies(db)

    return templates.TemplateResponse(request, "study.html", {
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


# POST chứ không phải GET — xem ghi chú ở app/routes/food.py
@router.post("/study/delete/{id}")
def delete_study(id: int, db: Session = Depends(get_db)):
    crud.delete_study(db, id)

    return RedirectResponse("/study", status_code=303)


# 🔥 SHOW FORM EDIT
@router.get("/study/edit/{id}")
def edit_study_page(request: Request, id: int, db: Session = Depends(get_db)):
    item = crud.get_study(db, id)

    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy chỗ này")

    return templates.TemplateResponse(request, "edit_study.html", {
        "item": item
    })


# 🔥 UPDATE DATA
@router.post("/study/edit/{id}")
def update_study(id: int,
                 name: str = Form(...),
                 address: str = Form(...),
                 note: str = Form(""),
                 db: Session = Depends(get_db)):

    if not crud.update_study(db, id, name, address, note):
        raise HTTPException(status_code=404, detail="Không tìm thấy chỗ này")

    return RedirectResponse("/study", status_code=303)
