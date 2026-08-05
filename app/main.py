from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import migrations
from app.database import Base, engine
from app.templating import templates, STATIC_DIR
from app.routes import food, study
from app.routes import plan


try:
    Base.metadata.create_all(bind=engine)
    migrations.run()
except Exception as exc:  # pragma: no cover - deploy-time safety net
    # Don't let a DB hiccup kill the whole site at import time (on Vercel that
    # turns every route into an opaque 500). Log it; DB-less pages still render.
    print(f"[startup] database init failed: {exc!r}")

app = FastAPI()

# check_dir=False: on Vercel /static is served by the CDN, the mount is only a fallback
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")


# 🔥 HOME
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "bg": "bghome.mp4"
    })


app.include_router(food.router)
app.include_router(study.router)
app.include_router(plan.router)
