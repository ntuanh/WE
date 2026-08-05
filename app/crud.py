from sqlalchemy.orm import Session
from . import models

# FOOD
def get_foods(db: Session):
    return db.query(models.FoodPlace).order_by(models.FoodPlace.id.desc()).all()

def create_food(db: Session, name, address, note, status, image="", rating=0):
    food = models.FoodPlace(
        name=name,
        address=address,
        note=note,
        image=image,
        rating=rating,
        status=status
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food

# STUDY
def get_studies(db: Session):
    return db.query(models.StudyPlace).order_by(models.StudyPlace.id.desc()).all()

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

# PLAN
def get_plans(db: Session):
    # chưa xong lên trước, mới nhất lên trên
    return db.query(models.Plan).order_by(models.Plan.done, models.Plan.id.desc()).all()

def create_plan(db: Session, title, script, priority="normal", deadline=""):
    plan = models.Plan(
        title=title,
        script=script,
        priority=priority,
        deadline=deadline
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

def update_plan_status(db: Session, id: int, done: int):
    item = db.query(models.Plan).filter(models.Plan.id == id).first()
    if item:
        item.done = done
        db.commit()


def update_plan(db: Session, id, title, script, priority, deadline):
    item = db.query(models.Plan).filter(models.Plan.id == id).first()
    if item:
        item.title = title
        item.script = script
        item.priority = priority
        item.deadline = deadline
        db.commit()
