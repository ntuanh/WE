"""Đăng nhập — chỉ hai đứa mình vào được thôi ♡

Phiên đăng nhập nằm trong một cookie ký bằng HMAC (chữ ký hỏng hoặc hết hạn thì
coi như chưa đăng nhập), nên không phải thêm thư viện hay bảng DB nào cả.
"""

import hashlib
import hmac
import json
import os
import time

from fastapi import HTTPException, Request

from .log import log

COOKIE_NAME = "we_session"
MAX_AGE = 30 * 24 * 3600  # 30 ngày rồi mới phải đăng nhập lại

# Đặt SECRET_KEY trong Vercel → Settings → Environment Variables. Đổi khoá này
# là mọi cookie cũ mất hiệu lực ngay (cách "đăng xuất tất cả thiết bị").
DEFAULT_SECRET = "just-us-being-goofy-set-SECRET_KEY-please"
SECRET = os.environ.get("SECRET_KEY", "").strip() or DEFAULT_SECRET
USING_DEFAULT_SECRET = SECRET == DEFAULT_SECRET

SALT = "just-us-being-goofy"
ITERATIONS = 200_000

# Chặn dò mật khẩu: quá số lần sai này thì khoá tạm theo (tên, IP).
MAX_ATTEMPTS = 8
LOCKOUT_SECONDS = 300

# Không có tài khoản nào viết sẵn trong mã. Kho này công khai, mà salt cũng nằm
# ngay dưới đây — băm nằm trong git là ai cũng đem về dò offline được.
#
# Tài khoản lấy từ (theo thứ tự ưu tiên):
#   1. biến môi trường WE_USERS — dùng khi deploy (Vercel → Environment Variables)
#   2. app/users.local.json — máy mình, đã cho vào .gitignore
#
# Tạo băm mật khẩu:  python -m app.auth "mat-khau-moi"
# Xem mẫu:           app/users.example.json
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "users.local.json")


def _clean_users(parsed) -> dict:
    """Lọc lấy các mục đúng dạng {"ten": {"hash": ..., "role": ...}}."""
    users = {}

    for name, account in (parsed or {}).items():
        if isinstance(account, dict) and account.get("hash"):
            users[str(name).strip().lower()] = {
                "hash": str(account["hash"]),
                "role": str(account.get("role", "user")),
            }

    return users


def _load_users() -> dict:
    """Đọc danh sách tài khoản từ WE_USERS, hoặc từ users.local.json."""
    raw = os.environ.get("WE_USERS", "").strip()

    if raw:
        try:
            return _clean_users(json.loads(raw))
        except (ValueError, TypeError) as exc:
            log(f"[auth] WE_USERS khong phai JSON hop le: {exc!r}")

    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return _clean_users(json.load(f))
    except FileNotFoundError:
        pass
    except (ValueError, OSError) as exc:
        log(f"[auth] doc {USERS_FILE} that bai: {exc!r}")

    return {}


USERS = _load_users()

# Không có tài khoản nào thì không ai đăng nhập được — trang login nói rõ ra
# thay vì cứ báo "sai mật khẩu" mãi mà không hiểu vì sao.
NO_ACCOUNTS = not USERS

# Băm giả để so khi tên đăng nhập không tồn tại — xem authenticate().
_DUMMY_HASH = "0" * 64

# (tên, ip) -> [số lần sai, thời điểm sai gần nhất]
_failures: dict = {}


def hash_password(password: str) -> str:
    """PBKDF2 — chậm có chủ đích, để dò mật khẩu từ hash đỡ dễ."""
    return hashlib.pbkdf2_hmac(
        "sha256", (password or "").encode(), SALT.encode(), ITERATIONS
    ).hex()


# ---------- chặn dò mật khẩu ----------

def _key(username: str, ip: str) -> tuple:
    return ((username or "").strip().lower(), ip or "?")


def is_locked(username: str, ip: str = "") -> bool:
    """True khi cặp (tên, IP) đang bị khoá tạm vì sai quá nhiều lần."""
    count, last = _failures.get(_key(username, ip), (0, 0.0))

    if count < MAX_ATTEMPTS:
        return False

    if time.time() - last > LOCKOUT_SECONDS:
        _failures.pop(_key(username, ip), None)  # hết hạn khoá, xoá cho nhẹ
        return False

    return True


def seconds_locked(username: str, ip: str = "") -> int:
    """Còn phải chờ bao nhiêu giây nữa mới thử lại được."""
    if not is_locked(username, ip):
        return 0

    _, last = _failures[_key(username, ip)]
    return max(1, int(LOCKOUT_SECONDS - (time.time() - last)))


def _record_failure(username: str, ip: str) -> None:
    count, _ = _failures.get(_key(username, ip), (0, 0.0))
    _failures[_key(username, ip)] = (count + 1, time.time())


def reset_failures(username: str = "", ip: str = "") -> None:
    """Xoá bộ đếm — gọi sau khi đăng nhập đúng, và trong test."""
    if not username and not ip:
        _failures.clear()
    else:
        _failures.pop(_key(username, ip), None)


# ---------- xác thực ----------

def authenticate(username: str, password: str, ip: str = ""):
    """Trả về user nếu đúng tên + mật khẩu, ngược lại None.

    Tên không tồn tại vẫn phải băm một lần rồi so với hash giả: nếu thoát sớm,
    thời gian trả lời sẽ tiết lộ tài khoản nào có thật.
    """
    name = (username or "").strip().lower()

    if is_locked(name, ip):
        return None

    account = USERS.get(name)
    expected = account["hash"] if account else _DUMMY_HASH

    ok = hmac.compare_digest(expected, hash_password(password)) and account is not None

    if not ok:
        _record_failure(name, ip)
        return None

    reset_failures(name, ip)

    return _public(name, account)


def _public(username: str, account: dict) -> dict:
    """Phần thông tin đưa ra template — không kèm hash."""
    return {
        "username": username,
        "role": account["role"],
        "is_admin": account["role"] == "admin",
    }


# ---------- cookie ----------

def _sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(username: str) -> str:
    payload = f"{username}.{int(time.time())}"
    return f"{payload}.{_sign(payload)}"


def user_from_cookie(token: str):
    """Đọc cookie → user, hoặc None nếu thiếu / sai chữ ký / quá hạn."""
    try:
        # rsplit: tên đăng nhập có dấu chấm cũng không làm vỡ việc tách chuỗi
        username, issued, signature = token.rsplit(".", 2)
    except (AttributeError, ValueError):
        return None

    if not hmac.compare_digest(signature, _sign(f"{username}.{issued}")):
        return None

    if not issued.isdigit() or time.time() - int(issued) > MAX_AGE:
        return None

    account = USERS.get(username)

    return _public(username, account) if account else None


def is_https(request: Request) -> bool:
    """Vercel/Heroku cắt TLS ở proxy, nên scheme thấy được có thể là http."""
    forwarded = request.headers.get("x-forwarded-proto", "")

    if forwarded:
        return forwarded.split(",")[0].strip() == "https"

    return request.url.scheme == "https"


def client_ip(request: Request) -> str:
    """IP người gọi, ưu tiên header proxy đặt vào."""
    forwarded = request.headers.get("x-forwarded-for", "")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "?"


def set_cookie(response, request: Request, username: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        make_token(username),
        max_age=MAX_AGE,
        httponly=True,          # JS không đọc được
        samesite="lax",
        secure=is_https(request),  # bật khi chạy thật, tắt khi localhost
        path="/",
    )


# ---------- dùng trong route ----------

def current_user(request: Request):
    """User của request hiện tại (middleware trong app/main.py gán vào)."""
    return getattr(request.state, "user", None)


def require_login(request: Request):
    """Dependency cho route cần đăng nhập (middleware đã gác, đây là lớp hai)."""
    user = current_user(request)

    if not user:
        raise HTTPException(status_code=401, detail="Đăng nhập đã nha")

    return user


def require_admin(request: Request):
    """Dependency chặn route chỉ dành cho admin: Depends(auth.require_admin)."""
    user = current_user(request)

    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Chỉ admin mới làm được cái này")

    return user


if __name__ == "__main__":  # python -m app.auth "mat-khau-moi"
    import sys

    if len(sys.argv) != 2:
        print('Cach dung: python -m app.auth "mat-khau-moi"')
        raise SystemExit(1)

    print(hash_password(sys.argv[1]))
