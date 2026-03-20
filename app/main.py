from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import Base, engine
from app.routes import food, study
from app.routes import plan


Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 🔥 HOME (bạn đang thiếu cái này)
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bg": "bghome.mp4"
    })


app.include_router(food.router)
app.include_router(study.router)
app.include_router(plan.router)