from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import auth, database, migrations
from app.log import log
from app.database import Base, engine
from app.templating import templates, STATIC_DIR
from app.routes import auth as auth_routes
from app.routes import budget, food, plan, study


def _boot() -> None:
    """Tạo bảng còn thiếu + vá cột còn thiếu, rồi báo cáo tình hình ra log.

    Cả hàm nằm trong try: một trục trặc lúc khởi động không được phép giết cả
    site (trên Vercel là mọi route thành 500 không rõ lý do).
    """
    try:
        Base.metadata.create_all(bind=engine)
        applied = migrations.run()

        log(f"[startup] database: {database.describe()}")

        if applied:
            log(f"[startup] da va schema: {', '.join(applied)}")

        if database.BAD_DATABASE_URL:
            log("[startup] CANH BAO: DATABASE_URL co nhung dung khong duoc - "
                "kiem tra lai chuoi ket noi. Dang chay tam bang SQLite.")

        if database.IS_EPHEMERAL:
            log("[startup] CANH BAO: du lieu dang nam o cho se bi xoa moi lan "
                "cold start. Dat DATABASE_URL (Postgres) de giu du lieu.")

        if auth.NO_ACCOUNTS:
            log("[startup] CANH BAO: chua co tai khoan nao - dat WE_USERS hoac "
                "tao app/users.local.json thi moi dang nhap duoc.")

        if auth.USING_DEFAULT_SECRET:
            log("[startup] CANH BAO: SECRET_KEY chua dat, cookie phien dang ky "
                "bang khoa mac dinh cong khai. Dat SECRET_KEY truoc khi cho "
                "nguoi khac vao.")

    except Exception as exc:  # pragma: no cover - lưới an toàn lúc deploy
        log(f"[startup] khoi tao database that bai: {exc!r}")


_boot()

app = FastAPI(title="Just us being goofy ♡", docs_url=None, redoc_url=None)

# check_dir=False: trên Vercel /static do CDN phục vụ, mount này chỉ là dự phòng
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")

# Những đường dẫn không cần đăng nhập (chính trang đăng nhập + file tĩnh).
# So khớp đúng cả chuỗi, không phải tiền tố — "/login-that-bai" không được lọt.
PUBLIC_EXACT = frozenset({"/login", "/logout", "/favicon.ico"})
PUBLIC_PREFIX = ("/static/",)


def _is_public(path: str) -> bool:
    return path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIX)


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Chưa đăng nhập thì không xem được gì ngoài /login.

    Gác ở middleware chứ không gác từng route: route mới thêm sau này tự động
    được bảo vệ, khỏi lo quên. Template đọc user qua `request.state.user`.
    """
    request.state.user = auth.user_from_cookie(request.cookies.get(auth.COOKIE_NAME))

    if request.state.user is None and not _is_public(request.url.path):
        wanted = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(f"/login?next={quote(wanted, safe='/')}", status_code=303)

    response = await call_next(request)

    # Trang riêng tư thì đừng để proxy/CDN giữ lại bản sao cho người khác xem.
    if not _is_public(request.url.path):
        response.headers.setdefault("Cache-Control", "no-store")

    return response


# 🔥 HOME
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "bg": "bghome.mp4"
    })


@app.get("/healthz")
def healthz():
    """Kiểm tra nhanh: app sống chưa, đang nối vào database nào."""
    return {
        "ok": True,
        "database": database.describe(),
        "ephemeral": database.IS_EPHEMERAL,
        "bad_database_url": database.BAD_DATABASE_URL,
        "secret_key_set": not auth.USING_DEFAULT_SECRET,
    }


app.include_router(auth_routes.router)
app.include_router(food.router)
app.include_router(study.router)
app.include_router(plan.router)
app.include_router(budget.router)
