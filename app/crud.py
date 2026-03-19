from sqlalchemy.orm import Session
from . import models

# FOOD
def get_foods(db: Session):
    return db.query(models.FoodPlace).all()

def create_food(db: Session, name, address, note, status):
    food = models.FoodPlace(
        name=name,
        address=address,
        note=note,
        status=status
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food

# STUDY
def get_studies(db: Session):
    return db.query(models.StudyPlace).all()

def create_study(db: Session, name, address, note):
    study = models.StudyPlace(
        name=name,
        address=address,
        note=note
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return study