"""Test cho phần mật khẩu và chặn truy cập.

Chia làm bốn nhóm:
  1. hash_password  — băm mật khẩu
  2. authenticate   — đúng/sai tên, đúng/sai mật khẩu, khoá khi thử quá nhiều
  3. cookie phiên   — ký, hết hạn, sửa trộm
  4. cổng vào       — chưa đăng nhập thì không xem được gì
"""

import time

import pytest

from app import auth
from tests.conftest import ADMIN, GOOD_PASSWORD, MEMBER


# ---------------------------------------------------------------- 1. băm

def test_hash_on_dinh_qua_moi_lan_goi():
    assert auth.hash_password("abc123") == auth.hash_password("abc123")


def test_hash_khac_nhau_cho_mat_khau_khac_nhau():
    assert auth.hash_password("abc123") != auth.hash_password("abc124")


def test_hash_phan_biet_chu_hoa_chu_thuong():
    assert auth.hash_password("MatKhau") != auth.hash_password("matkhau")


def test_hash_khong_chua_mat_khau_goc():
    """Hash lộ ra ngoài (git, log) cũng không đọc ngược ra mật khẩu."""
    digest = auth.hash_password("sieu-bi-mat")

    assert "sieu-bi-mat" not in digest
    assert len(digest) == 64                      # sha256 dạng hex
    assert all(c in "0123456789abcdef" for c in digest)


def test_hash_khong_vo_khi_mat_khau_rong():
    assert len(auth.hash_password("")) == 64
    assert len(auth.hash_password(None)) == 64


def test_hash_xu_ly_duoc_tieng_viet_va_emoji():
    assert auth.hash_password("mậtkhẩu💖") != auth.hash_password("matkhau")


# -------------------------------------------------------- 2. authenticate

def test_dung_ten_dung_mat_khau_thi_vao_duoc():
    user = auth.authenticate(MEMBER, GOOD_PASSWORD)

    assert user is not None
    assert user["username"] == MEMBER
    assert user["is_admin"] is False


def test_admin_co_co_admin():
    user = auth.authenticate(ADMIN, GOOD_PASSWORD)

    assert user["is_admin"] is True
    assert user["role"] == "admin"


def test_khong_tra_ve_hash_cho_ben_ngoai():
    """Dict trả ra đi thẳng vào template — lỡ in ra là lộ hash."""
    user = auth.authenticate(MEMBER, GOOD_PASSWORD)

    assert "hash" not in user
    assert "password" not in user


def test_sai_mat_khau_thi_khong_vao_duoc():
    assert auth.authenticate(MEMBER, "mat-khau-bay-ba") is None


def test_ten_khong_ton_tai_thi_khong_vao_duoc():
    assert auth.authenticate("nguoi-la-oi", GOOD_PASSWORD) is None


@pytest.mark.parametrize("password", [
    "",
    None,
    GOOD_PASSWORD + " ",           # thừa khoảng trắng vẫn là sai
    " " + GOOD_PASSWORD,
    GOOD_PASSWORD.upper(),         # sai chữ hoa/thường
    GOOD_PASSWORD[:-1],            # thiếu một ký tự
])
def test_mat_khau_gan_dung_van_bi_tu_choi(password):
    assert auth.authenticate(MEMBER, password) is None


@pytest.mark.parametrize("username", [
    "",
    None,
    "' OR 1=1 --",                 # SQL injection: USERS là dict nên vô hại
    "../../etc/passwd",
    MEMBER + "\x00",
])
def test_ten_dang_nhap_bay_ba_khong_lam_vo_gi(username):
    assert auth.authenticate(username, GOOD_PASSWORD) is None


def test_ten_dang_nhap_khong_phan_biet_hoa_thuong_va_khoang_trang():
    """Gõ "  Test_Admin  " vẫn vào được — chỉ mật khẩu mới khắt khe."""
    user = auth.authenticate(f"  {ADMIN.upper()}  ", GOOD_PASSWORD)

    assert user is not None
    assert user["username"] == ADMIN


def test_ten_khong_ton_tai_ton_thoi_gian_gan_bang_ten_co_that():
    """Thoát sớm khi tên không tồn tại sẽ để lộ tài khoản nào có thật qua thời
    gian trả lời. Cả hai nhánh đều phải băm một lần."""
    def do(username):
        start = time.perf_counter()
        auth.authenticate(username, "mat-khau-sai")
        return time.perf_counter() - start

    that = min(do(MEMBER) for _ in range(3))
    gia = min(do("khong-he-co-nguoi-nay") for _ in range(3))

    assert 0.4 < gia / that < 2.5, f"chênh lệch thời gian đáng ngờ: {that=} {gia=}"


# ------------------------------------------------- 2b. khoá khi dò mật khẩu

def test_sai_nhieu_lan_thi_bi_khoa_tam():
    ip = "10.0.0.1"

    for _ in range(auth.MAX_ATTEMPTS):
        assert auth.authenticate(MEMBER, "sai-roi", ip) is None

    assert auth.is_locked(MEMBER, ip) is True

    # đúng mật khẩu cũng phải chờ — nếu không thì khoá chẳng để làm gì
    assert auth.authenticate(MEMBER, GOOD_PASSWORD, ip) is None
    assert auth.seconds_locked(MEMBER, ip) > 0


def test_khoa_khong_lan_sang_ip_khac():
    for _ in range(auth.MAX_ATTEMPTS):
        auth.authenticate(MEMBER, "sai-roi", "10.0.0.1")

    assert auth.is_locked(MEMBER, "10.0.0.1") is True
    assert auth.is_locked(MEMBER, "10.0.0.2") is False
    assert auth.authenticate(MEMBER, GOOD_PASSWORD, "10.0.0.2") is not None


def test_dang_nhap_dung_thi_xoa_bo_dem():
    ip = "10.0.0.3"

    for _ in range(auth.MAX_ATTEMPTS - 1):
        auth.authenticate(MEMBER, "sai-roi", ip)

    assert auth.authenticate(MEMBER, GOOD_PASSWORD, ip) is not None

    # đã reset, nên lần sai tiếp theo bắt đầu đếm lại từ đầu
    auth.authenticate(MEMBER, "sai-roi", ip)
    assert auth.is_locked(MEMBER, ip) is False


def test_het_han_khoa_thi_thu_lai_duoc(monkeypatch):
    ip = "10.0.0.4"

    for _ in range(auth.MAX_ATTEMPTS):
        auth.authenticate(MEMBER, "sai-roi", ip)

    assert auth.is_locked(MEMBER, ip) is True

    later = time.time() + auth.LOCKOUT_SECONDS + 1
    monkeypatch.setattr(auth.time, "time", lambda: later)

    assert auth.is_locked(MEMBER, ip) is False
    assert auth.authenticate(MEMBER, GOOD_PASSWORD, ip) is not None


# ------------------------------------------------------------- 3. cookie

def test_cookie_hop_le_doc_ra_dung_user():
    token = auth.make_token(MEMBER)

    assert auth.user_from_cookie(token)["username"] == MEMBER


@pytest.mark.parametrize("token", [
    None,
    "",
    "linh tinh",
    "khong-co-dau-cham",
    "chi.hai-phan",
    f"{MEMBER}.{int(time.time())}.chu-ky-bia-dat",
])
def test_cookie_hong_thi_coi_nhu_chua_dang_nhap(token):
    assert auth.user_from_cookie(token) is None


def test_khong_the_tu_che_cookie_de_thanh_nguoi_khac():
    """Không biết SECRET_KEY thì không ký nổi — đây là chốt chặn chính."""
    gia_mao = f"{ADMIN}.{int(time.time())}.{'a' * 64}"

    assert auth.user_from_cookie(gia_mao) is None


def test_sua_ten_trong_cookie_lam_hong_chu_ky():
    token = auth.make_token(MEMBER)
    _, issued, signature = token.rsplit(".", 2)

    assert auth.user_from_cookie(f"{ADMIN}.{issued}.{signature}") is None


def test_keo_dai_han_trong_cookie_lam_hong_chu_ky():
    token = auth.make_token(MEMBER)
    username, issued, signature = token.rsplit(".", 2)

    tuong_lai = str(int(issued) + 999_999)
    assert auth.user_from_cookie(f"{username}.{tuong_lai}.{signature}") is None


def test_cookie_qua_han_thi_khong_dung_duoc():
    qua_han = int(time.time()) - auth.MAX_AGE - 10
    payload = f"{MEMBER}.{qua_han}"
    token = f"{payload}.{auth._sign(payload)}"   # chữ ký đúng, chỉ là quá cũ

    assert auth.user_from_cookie(token) is None


def test_doi_secret_key_lam_moi_cookie_cu_het_hieu_luc():
    token = auth.make_token(MEMBER)
    assert auth.user_from_cookie(token) is not None

    cu = auth.SECRET
    try:
        auth.SECRET = "khoa-hoan-toan-khac"
        assert auth.user_from_cookie(token) is None
    finally:
        auth.SECRET = cu


def test_user_bi_xoa_thi_cookie_cu_khong_con_dung_duoc():
    token = auth.make_token(MEMBER)
    auth.USERS.pop(MEMBER)

    assert auth.user_from_cookie(token) is None


# ------------------------------------------------- 4. cổng vào (HTTP thật)

CAC_TRANG_RIENG = ["/", "/food", "/study", "/plan", "/budget", "/healthz"]


@pytest.mark.parametrize("path", CAC_TRANG_RIENG)
def test_chua_dang_nhap_thi_bi_day_ve_login(client, path):
    res = client.get(path, follow_redirects=False)

    assert res.status_code == 303
    assert res.headers["location"].startswith("/login")


@pytest.mark.parametrize("path", CAC_TRANG_RIENG)
def test_dang_nhap_roi_thi_vao_duoc(logged_in, path):
    assert logged_in.get(path).status_code == 200


def test_trang_login_ai_cung_xem_duoc(client):
    assert client.get("/login").status_code == 200


def test_duong_dan_gan_giong_login_khong_lot_qua_cong(client):
    """Trước đây cổng so bằng startswith nên "/login-gi-do" được thả qua."""
    res = client.get("/login-khong-phai-trang-login", follow_redirects=False)

    assert res.status_code == 303
    assert res.headers["location"].startswith("/login?")


def test_dang_nhap_dung_thi_duoc_cookie(client):
    res = client.post("/login",
                      data={"username": MEMBER, "password": GOOD_PASSWORD},
                      follow_redirects=False)

    assert res.status_code == 303
    assert auth.COOKIE_NAME in res.cookies


def test_cookie_phien_khong_cho_javascript_doc(client):
    res = client.post("/login",
                      data={"username": MEMBER, "password": GOOD_PASSWORD},
                      follow_redirects=False)

    assert "httponly" in res.headers["set-cookie"].lower()


def test_dang_nhap_sai_thi_tra_401_va_khong_co_cookie(client):
    res = client.post("/login",
                      data={"username": MEMBER, "password": "sai-be-bet"},
                      follow_redirects=False)

    assert res.status_code == 401
    assert auth.COOKIE_NAME not in res.cookies


def test_bao_loi_khong_tiet_lo_tai_khoan_nao_co_that(client):
    """Hai lời nhắn phải giống hệt nhau, nếu không là chỉ đường cho người dò."""
    sai_mat_khau = client.post(
        "/login", data={"username": MEMBER, "password": "sai"}).text
    khong_co_ten = client.post(
        "/login", data={"username": "nguoi-la", "password": "sai"}).text

    assert "Sai tên đăng nhập hoặc mật khẩu" in sai_mat_khau
    assert "Sai tên đăng nhập hoặc mật khẩu" in khong_co_ten


def test_sai_qua_nhieu_lan_thi_form_bao_cho_doi(client):
    for _ in range(auth.MAX_ATTEMPTS):
        client.post("/login", data={"username": MEMBER, "password": "sai"})

    res = client.post("/login", data={"username": MEMBER, "password": GOOD_PASSWORD})

    assert res.status_code == 429
    assert "Đợi" in res.text


def test_thoat_thi_mat_quyen_vao(logged_in):
    logged_in.get("/logout", follow_redirects=False)

    res = logged_in.get("/food", follow_redirects=False)
    assert res.status_code == 303


def test_dang_nhap_xong_quay_lai_dung_trang_dang_dinh_xem(client):
    res = client.get("/budget", follow_redirects=False)
    assert res.headers["location"] == "/login?next=/budget"

    res = client.post("/login",
                      data={"username": MEMBER, "password": GOOD_PASSWORD,
                            "next": "/budget"},
                      follow_redirects=False)

    assert res.headers["location"] == "/budget"


@pytest.mark.parametrize("doc_hai", [
    "https://cho-lua-dao.com",
    "//cho-lua-dao.com",
    "/\\cho-lua-dao.com",
    "javascript:alert(1)",
])
def test_khong_the_muon_trang_login_de_day_nguoi_khac_ra_ngoai(client, doc_hai):
    res = client.post("/login",
                      data={"username": MEMBER, "password": GOOD_PASSWORD,
                            "next": doc_hai},
                      follow_redirects=False)

    assert res.headers["location"] == "/"


def test_trang_rieng_khong_cho_proxy_luu_lai(logged_in):
    assert logged_in.get("/food").headers.get("cache-control") == "no-store"


# --------------------------------- 5. nguồn tài khoản (không nằm trong git)

def test_doc_tai_khoan_tu_bien_moi_truong(monkeypatch):
    monkeypatch.setenv("WE_USERS", '{"Ai_Do": {"hash": "abc", "role": "admin"}}')

    users = auth._load_users()

    assert users == {"ai_do": {"hash": "abc", "role": "admin"}}   # tên viết thường


def test_doc_tai_khoan_tu_file_local(monkeypatch, tmp_path):
    monkeypatch.delenv("WE_USERS", raising=False)

    f = tmp_path / "users.local.json"
    f.write_text('{"ai_do": {"hash": "abc"}}', encoding="utf-8")
    monkeypatch.setattr(auth, "USERS_FILE", str(f))

    assert auth._load_users() == {"ai_do": {"hash": "abc", "role": "user"}}


def test_bien_moi_truong_thang_the_file(monkeypatch, tmp_path):
    f = tmp_path / "users.local.json"
    f.write_text('{"tu_file": {"hash": "abc"}}', encoding="utf-8")
    monkeypatch.setattr(auth, "USERS_FILE", str(f))
    monkeypatch.setenv("WE_USERS", '{"tu_env": {"hash": "xyz"}}')

    assert list(auth._load_users()) == ["tu_env"]


@pytest.mark.parametrize("noi_dung", ['khong phai json', '[]', 'null', '{"a": "khong phai dict"}'])
def test_cau_hinh_tai_khoan_hong_thi_tra_ve_rong_chu_khong_no(monkeypatch, noi_dung):
    monkeypatch.setenv("WE_USERS", noi_dung)
    monkeypatch.setattr(auth, "USERS_FILE", "/khong/co/file/nay.json")

    assert auth._load_users() == {}


def test_khong_co_tai_khoan_nao_thi_khong_ai_vao_duoc(monkeypatch):
    monkeypatch.setattr(auth, "USERS", {})

    assert auth.authenticate("bat-ky-ai", "bat-ky-mat-khau-nao") is None


def test_trang_login_noi_ro_khi_chua_cau_hinh_tai_khoan(client, monkeypatch):
    """Đừng để người ta gõ mật khẩu mãi mà không hiểu vì sao luôn sai."""
    monkeypatch.setattr(auth, "USERS", {})
    monkeypatch.setattr(auth, "NO_ACCOUNTS", True)

    res = client.post("/login", data={"username": "ai_do", "password": "gi_do"})

    assert res.status_code == 503
    assert "Chưa có tài khoản nào" in res.text
    assert "WE_USERS" in res.text


def test_khong_co_bam_mat_khau_nao_nam_trong_ma_nguon():
    """Kho này công khai: băm lọt vào git là ai cũng đem về dò offline được."""
    import pathlib
    import re

    goc = pathlib.Path(__file__).resolve().parent.parent

    for f in list(goc.glob("app/**/*.py")) + list(goc.glob("app/**/*.json")):
        if f.name == "users.local.json":       # file này đã bị .gitignore chặn
            continue

        noi_dung = f.read_text(encoding="utf-8")
        # chuỗi 64 ký tự hex đứng cạnh chữ "hash" = một băm mật khẩu thật
        assert not re.search(r'hash"?\s*:\s*"[0-9a-f]{64}"', noi_dung), \
            f"co ve nhu {f.name} dang chua mot bam mat khau that"


# ------------------------- 6. chưa đăng nhập thì không lộ gì ra ngoài

# Những thứ chỉ được phép xuất hiện sau khi đã đăng nhập.
RIENG_TU = [
    ("bg-video", "thẻ video nền"),
    (".mp4", "đường dẫn file video"),
    ("bghome", "tên file video nhà"),
    ("bgfood", "tên file video đồ ăn"),
    ("tenor.com", "script của bên thứ ba"),
    ('class="navbar"', "thanh điều hướng"),
]


@pytest.mark.parametrize("dau_vet, ten", RIENG_TU)
def test_trang_login_khong_lo_gi(client, dau_vet, ten):
    """Video nền là ảnh riêng của hai người — để nó chạy ở màn hình đăng nhập
    thì ai đi ngang qua cũng xem được mà không cần mật khẩu."""
    html = client.get("/login").text

    assert dau_vet not in html, f"trang login vẫn còn {ten}"


def test_trang_login_khong_goi_ra_may_chu_ben_ngoai(client):
    """Chỉ nên tải CSS của chính mình — không gọi ra ngoài trước khi đăng nhập."""
    import re

    html = client.get("/login").text
    ben_ngoai = [u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)]

    assert ben_ngoai == [], f"trang login gọi ra ngoài: {ben_ngoai}"


def test_tieu_de_tab_khong_lo_ten_app_khi_chua_dang_nhap(client):
    """Tab trình duyệt và lịch sử duyệt web là chỗ dễ bị liếc thấy nhất."""
    html = client.get("/login").text

    assert "<title>Đăng nhập</title>" in html
    assert "Just us being goofy</title>" not in html


def test_trang_login_van_co_nen_rieng(client):
    """Bỏ video đi rồi thì phải có nền CSS thay thế, không thì trơ trọi."""
    html = client.get("/login").text

    assert "auth-bg" in html
    assert "auth-blob" in html


@pytest.mark.parametrize("dau_vet, ten", [
    ("bg-video", "thẻ video nền"),
    (".mp4", "đường dẫn file video"),
    ("bghome", "video nền của trang chủ"),
    ("tenor.com", "script của bên thứ ba"),
    ('class="navbar"', "thanh điều hướng"),
])
def test_dang_nhap_roi_thi_moi_hien_day_du(logged_in, dau_vet, ten):
    """Mặt còn lại: đăng nhập xong thì video và thanh điều hướng phải quay lại."""
    html = logged_in.get("/").text

    assert dau_vet in html, f"đăng nhập rồi mà thiếu {ten}"


def test_moi_trang_giu_dung_video_cua_no(logged_in):
    """Mỗi trang có video riêng — đừng để lúc bỏ video khỏi màn hình đăng nhập
    thì làm hỏng luôn phần chọn video của các trang trong."""
    assert "bghome" in logged_in.get("/").text
    assert "bgfood" in logged_in.get("/food").text


def test_dang_nhap_roi_thi_khong_con_nen_dang_nhap(logged_in):
    html = logged_in.get("/").text

    assert "auth-bg" not in html
    assert "Just us being goofy" in html
