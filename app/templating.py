import os

from fastapi.templating import Jinja2Templates

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(APP_DIR, "static")

# absolute, not "app/templates" — serverless doesn't run from the project root
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def vnd(value) -> str:
    """1234567 -> '1.234.567' — dấu chấm ngăn nghìn kiểu Việt Nam."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


templates.env.filters["vnd"] = vnd
