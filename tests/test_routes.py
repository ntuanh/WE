"""Test cho các route — đi qua HTTP thật, có đăng nhập sẵn."""

from urllib.parse import quote, unquote

import pytest

from app import crud


# ---------- ăn uống ----------

def test_them_quan_qua_form(logged_in, db):
    res = logged_in.post("/food/add", data={
        "name": "Phở Thìn", "address": "Lò Đúc", "note": "ngon",
        "image": "", "rating": "5", "status": "da_an",
    }, follow_redirects=False)

    assert res.status_code == 303
    assert crud.get_foods(db)[0].name == "Phở Thìn"


def test_trang_an_uong_hien_ten_quan(logged_in, db):
    crud.create_food(db, "Bún chả Hương Liên", "Lê Văn Hưu", "", "da_an")

    assert "Bún chả Hương Liên" in logged_in.get("/food").text


def test_xoa_quan_bang_post(logged_in, db):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "da_an")

    logged_in.post(f"/food/delete/{quan.id}", follow_redirects=False)

    assert crud.get_foods(db) == []


def test_khong_xoa_duoc_bang_get(logged_in, db):
    """Link xoá kiểu GET có thể bị trình duyệt nạp trước và xoá oan —
    giờ phải là POST."""
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "da_an")

    res = logged_in.get(f"/food/delete/{quan.id}", follow_redirects=False)

    assert res.status_code == 405
    assert len(crud.get_foods(db)) == 1


def test_khong_con_cot_chua_an(logged_in):
    """Bảng đồ ăn giờ chỉ còn hai cột."""
    trang = logged_in.get("/food").text

    assert 'data-status="chua_an"' not in trang
    assert 'data-status="da_an"' in trang
    assert 'data-status="muon_an"' in trang


def test_trang_thai_bo_di_quay_ve_muon_an(logged_in, db):
    """Form cũ (hoặc ai đó gõ tay) gửi lên "chua_an" thì không được lọt vào DB."""
    logged_in.post("/food/add", data={
        "name": "Quán", "address": "Đâu đó", "note": "",
        "image": "", "rating": "0", "status": "chua_an",
    }, follow_redirects=False)

    assert crud.get_foods(db)[0].status == "muon_an"


def test_vong_quay_doc_ten_quan_tu_the(logged_in, db):
    """Vòng quay lấy danh sách thẳng từ các thẻ trong cột "Muốn ăn", nên tên
    quán phải nằm sẵn trên thẻ ở dạng máy đọc được."""
    quan = crud.create_food(db, "Cơm tấm Ba Ghiền", "Phan Xích Long", "", "muon_an")

    trang = logged_in.get("/food").text

    assert 'id="wheel-spin"' in trang
    assert 'id="wheel-verify"' in trang
    assert 'id="wheel-again"' in trang
    assert f'id="food-{quan.id}"' in trang
    assert 'data-name="Cơm tấm Ba Ghiền"' in trang


def test_sua_quan_khong_co_that_tra_404(logged_in):
    assert logged_in.get("/food/edit/9999").status_code == 404


def test_keo_tha_doi_trang_thai(logged_in, db):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "muon_an")

    res = logged_in.post(f"/food/update-status/{quan.id}", json={"status": "da_an"})

    assert res.json() == {"success": True, "status": "da_an"}
    assert crud.get_food(db, quan.id).status == "da_an"


def test_keo_tha_trang_thai_bay_ba_tra_400(logged_in, db):
    """Trước đây route trả {"success": true} rồi ghi thẳng giá trị lạ vào DB."""
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "muon_an")

    res = logged_in.post(f"/food/update-status/{quan.id}", json={"status": "bia_dat"})

    assert res.status_code == 400
    assert crud.get_food(db, quan.id).status == "muon_an"


# ---------- học tập ----------

def test_them_va_xoa_cho_hoc(logged_in, db):
    logged_in.post("/study/add", data={
        "name": "Thư viện Quốc gia", "address": "Tràng Thi", "note": "",
    }, follow_redirects=False)

    cho = crud.get_studies(db)[0]
    assert cho.name == "Thư viện Quốc gia"

    logged_in.post(f"/study/delete/{cho.id}", follow_redirects=False)
    assert crud.get_studies(db) == []


def test_sua_cho_hoc(logged_in, db):
    cho = crud.create_study(db, "Cũ", "Địa chỉ cũ", "")

    logged_in.post(f"/study/edit/{cho.id}", data={
        "name": "Mới", "address": "Địa chỉ mới", "note": "yên tĩnh",
    }, follow_redirects=False)

    assert crud.get_study(db, cho.id).name == "Mới"


# ---------- kế hoạch ----------

def test_them_ke_hoach(logged_in, db):
    logged_in.post("/plan/add", data={
        "title": "Đi Đà Lạt", "script": "3 ngày 2 đêm",
        "priority": "high", "deadline": "2025-12-25",
    }, follow_redirects=False)

    ke_hoach = crud.get_plans(db)[0]
    assert (ke_hoach.title, ke_hoach.priority) == ("Đi Đà Lạt", "high")


def test_tick_xong_ke_hoach(logged_in, db):
    ke_hoach = crud.create_plan(db, "Việc", "")

    res = logged_in.post(f"/plan/toggle/{ke_hoach.id}", json={"done": 1})

    assert res.json() == {"ok": True, "done": 1}
    assert crud.get_plan(db, ke_hoach.id).done == 1


def test_tick_ke_hoach_khong_ton_tai_tra_404(logged_in):
    """Trước đây route lặng lẽ trả ok:true dù chẳng lưu được gì."""
    assert logged_in.post("/plan/toggle/9999", json={"done": 1}).status_code == 404


def test_sua_ke_hoach_qua_trang_web(logged_in, db):
    """crud.update_plan trước đây không có route nào gọi tới."""
    ke_hoach = crud.create_plan(db, "Cũ", "", "low", "")

    assert logged_in.get(f"/plan/edit/{ke_hoach.id}").status_code == 200

    logged_in.post(f"/plan/edit/{ke_hoach.id}", data={
        "title": "Mới", "script": "", "priority": "high", "deadline": "2025-12-25",
    }, follow_redirects=False)

    assert crud.get_plan(db, ke_hoach.id).title == "Mới"


# ---------- lịch ----------

def test_trang_lich_co_du_hai_cuon(logged_in):
    from tests.conftest import ADMIN, MEMBER

    trang = logged_in.get("/schedule").text

    assert trang.count('<table class="cal">') == 2
    assert ADMIN in trang and MEMBER in trang


def test_them_viec_vao_lich(logged_in, db):
    from tests.conftest import MEMBER

    res = logged_in.post("/schedule/add", data={
        "owner": MEMBER, "date": "2025-03-14", "title": "Đi xem phim",
        "start": "19:30", "note": "CGV",
    }, follow_redirects=False)

    assert res.status_code == 303
    assert crud.get_events(db, "2025-03")[0].title == "Đi xem phim"


def test_them_xong_thi_mo_lai_dung_ngay_do(logged_in):
    """Submit xong mà ô vừa mở lại đóng sập thì thêm việc thứ hai rất khó chịu."""
    from tests.conftest import MEMBER

    res = logged_in.post("/schedule/add", data={
        "owner": MEMBER, "date": "2025-03-14", "title": "Việc", "start": "", "note": "",
    }, follow_redirects=False)

    quay_ve = unquote(res.headers["location"])

    assert "month=2025-03" in quay_ve
    assert f"open={MEMBER}:2025-03-14" in quay_ve


def test_o_dang_mo_duoc_bung_san_khong_can_javascript(logged_in, db):
    from tests.conftest import MEMBER

    crud.create_event(db, MEMBER, "2025-03-14", "Đi xem phim")

    trang = logged_in.get(f"/schedule?month=2025-03&open={MEMBER}:2025-03-14").text
    mo = trang.split(f'id="day-{MEMBER}-2025-03-14"')[1][:40]

    assert "hidden" not in mo


def test_khong_them_duoc_vao_lich_nguoi_khong_co_that(logged_in, db):
    res = logged_in.post("/schedule/add", data={
        "owner": "nguoi-la", "date": "2025-03-14", "title": "Việc",
        "start": "", "note": "",
    }, follow_redirects=False)

    assert res.status_code == 303
    assert "msg=" in res.headers["location"]
    assert crud.get_events(db, "2025-03") == []


def test_thang_bay_ba_khong_lam_vo_trang_lich(logged_in):
    """int(month[:4]) trong _grid sẽ nổ nếu month không phải YYYY-MM."""
    assert logged_in.get("/schedule?month=linh-tinh").status_code == 200
    assert logged_in.get("/schedule?month=9999-99").status_code == 200
    assert logged_in.get("/schedule?month=").status_code == 200


def test_qua_thang_12_thi_sang_nam_moi(logged_in):
    truoc = logged_in.get("/schedule?month=2025-01").text
    sau = logged_in.get("/schedule?month=2025-12").text

    assert "/schedule?month=2024-12" in truoc
    assert "/schedule?month=2026-01" in sau


def test_sua_mot_muc_trong_lich(logged_in, db):
    from tests.conftest import MEMBER

    muc = crud.create_event(db, MEMBER, "2025-03-14", "Cũ")

    logged_in.post(f"/schedule/edit/{muc.id}", data={
        "title": "Mới", "start": "20:00", "note": "đổi giờ",
    }, follow_redirects=False)

    assert crud.get_event(db, muc.id).title == "Mới"


def test_xoa_mot_muc_quay_ve_dung_ngay(logged_in, db):
    from tests.conftest import MEMBER

    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc")

    res = logged_in.post(f"/schedule/delete/{muc.id}", follow_redirects=False)

    assert f"open={quote(MEMBER + ':2025-03-14')}" in res.headers["location"]
    assert crud.get_events(db, "2025-03") == []


def test_khong_xoa_duoc_muc_lich_bang_get(logged_in, db):
    from tests.conftest import MEMBER

    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc")

    assert logged_in.get(f"/schedule/delete/{muc.id}",
                         follow_redirects=False).status_code == 405
    assert len(crud.get_events(db, "2025-03")) == 1


def test_lich_hien_viec_cua_ca_hai_dua(logged_in, db):
    from tests.conftest import ADMIN, MEMBER

    crud.create_event(db, MEMBER, "2025-03-14", "Việc của mình")
    crud.create_event(db, ADMIN, "2025-03-20", "Việc của người kia")

    trang = logged_in.get("/schedule?month=2025-03").text

    assert "Việc của mình" in trang
    assert "Việc của người kia" in trang


# ---------- linh tinh ----------

def test_healthz_bao_dang_dung_database_nao(logged_in):
    body = logged_in.get("/healthz").json()

    assert body["ok"] is True
    assert "database" in body


def test_thanh_dieu_huong_hien_ten_nguoi_dang_dang_nhap(logged_in):
    from tests.conftest import MEMBER

    assert MEMBER in logged_in.get("/").text
