from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import auth
from app.templating import templates

router = APIRouter()


def _safe_next(target: str) -> str:
    """Chỉ nhận đường dẫn nội bộ — tránh bị nhét link lạ vào ?next=.

    Chặn cả "//evil.com" (trình duyệt hiểu là scheme-relative, ra ngoài luôn)
    lẫn "/\\evil.com" mà vài trình duyệt cũng coi như vậy.
    """
    if not target or not target.startswith("/"):
        return "/"

    if target.startswith("//") or target.startswith("/\\"):
        return "/"

    return target


def _render_login(request: Request, next_url: str, error: str = "",
                  username: str = "", status_code: int = 200):
    return templates.TemplateResponse(request, "login.html", {
        "bg": "bghome.mp4",
        "next": next_url,
        "username": username,
        "error": error,
        "no_accounts": auth.NO_ACCOUNTS,
    }, status_code=status_code)


@router.get("/login")
def login_page(request: Request, next: str = "/"):
    if auth.current_user(request):
        return RedirectResponse(_safe_next(next), status_code=303)

    return _render_login(request, _safe_next(next))


@router.post("/login")
def do_login(request: Request,
             username: str = Form(...),
             password: str = Form(...),
             next: str = Form("/")):

    target = _safe_next(next)
    ip = auth.client_ip(request)

    # Chưa cấu hình tài khoản nào thì nói thẳng, đừng báo "sai mật khẩu" mãi.
    if auth.NO_ACCOUNTS:
        return _render_login(
            request, target,
            error="Chưa có tài khoản nào được cấu hình — xem phần Accounts "
                  "trong README.",
            username=username, status_code=503,
        )

    # Sai quá nhiều lần thì nghỉ một lát — chặn kiểu dò mật khẩu tự động.
    if auth.is_locked(username, ip):
        wait = auth.seconds_locked(username, ip)
        return _render_login(
            request, target,
            error=f"Thử sai nhiều quá rồi 😵 Đợi {wait} giây nữa nha",
            username=username, status_code=429,
        )

    user = auth.authenticate(username, password, ip)

    if not user:
        # Lời nhắn cố tình chung chung: không tiết lộ tên nào có thật.
        return _render_login(
            request, target,
            error="Sai tên đăng nhập hoặc mật khẩu rồi 🥲",
            username=username, status_code=401,
        )

    response = RedirectResponse(target, status_code=303)
    auth.set_cookie(response, request, user["username"])

    return response


@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)

    # Xoá đúng bộ thuộc tính đã dùng lúc đặt, nếu không vài trình duyệt giữ lại
    # cookie cũ và người dùng bấm "Thoát" xong vẫn thấy mình đang đăng nhập.
    response.delete_cookie(
        auth.COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=auth.is_https(request),
    )

    return response
