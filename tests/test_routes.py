"""Test cho các route — đi qua HTTP thật, có đăng nhập sẵn."""

from urllib.parse import quote, unquote

import pytest

from app import crud
from tests.conftest import ADMIN, MEMBER


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


# ---------- thời gian biểu ----------

def test_trang_lich_co_du_hai_bang_tuan(logged_in):
    trang = logged_in.get("/schedule").text

    assert trang.count('<div class="tt"') == 2          # đúng hai bảng tuần
    assert ADMIN in trang and MEMBER in trang


def test_them_viec_co_gio_bat_dau_va_ket_thuc(logged_in, db):
    res = logged_in.post("/schedule/add", data={
        "owner": MEMBER, "date": "2025-03-14", "title": "Đi xem phim",
        "start": "19:30", "end": "21:30", "note": "CGV",
    }, follow_redirects=False)

    assert res.status_code == 303

    muc = crud.get_week_events(db, "2025-03-10")[0]
    assert (muc.title, muc.start, muc.end) == ("Đi xem phim", "19:30", "21:30")


def test_them_xong_thi_quay_ve_dung_tuan_va_mo_lai_ngay_do(logged_in):
    """Submit xong mà ô vừa mở lại đóng sập thì thêm việc thứ hai rất khó chịu."""
    res = logged_in.post("/schedule/add", data={
        "owner": MEMBER, "date": "2025-03-14", "title": "Việc",
        "start": "08:00", "end": "", "note": "",
    }, follow_redirects=False)

    quay_ve = unquote(res.headers["location"])

    assert "week=2025-03-10" in quay_ve
    assert f"open={MEMBER}:2025-03-14" in quay_ve


def test_o_dang_mo_duoc_bung_san_khong_can_javascript(logged_in, db):
    crud.create_event(db, MEMBER, "2025-03-14", "Đi xem phim", "19:30")

    trang = logged_in.get(f"/schedule?week=2025-03-10&open={MEMBER}:2025-03-14").text
    mo = trang.split(f'id="day-{MEMBER}-2025-03-14"')[1][:40]

    assert "hidden" not in mo


def test_khong_them_duoc_vao_lich_nguoi_khong_co_that(logged_in, db):
    res = logged_in.post("/schedule/add", data={
        "owner": "nguoi-la", "date": "2025-03-14", "title": "Việc",
        "start": "", "end": "", "note": "",
    }, follow_redirects=False)

    assert res.status_code == 303
    assert "msg=" in res.headers["location"]
    assert crud.get_week_events(db, "2025-03-10") == []


def test_tuan_bay_ba_khong_lam_vo_trang(logged_in):
    """date.fromisoformat sẽ nổ nếu ?week= không phải một ngày thật."""
    assert logged_in.get("/schedule?week=linh-tinh").status_code == 200
    assert logged_in.get("/schedule?week=9999-99-99").status_code == 200
    assert logged_in.get("/schedule?week=").status_code == 200


def test_bam_ngay_giua_tuan_van_ra_dung_tuan_do(logged_in):
    """Ô chọn ngày cho gõ ngày bất kỳ, không bắt phải đúng thứ 2."""
    trang = logged_in.get("/schedule?week=2025-03-13").text

    assert "/schedule?week=2025-03-03" in trang       # tuần trước
    assert "/schedule?week=2025-03-17" in trang       # tuần sau


def test_sua_mot_muc_trong_lich(logged_in, db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Cũ", "08:00")

    logged_in.post(f"/schedule/edit/{muc.id}", data={
        "title": "Mới", "start": "20:00", "end": "22:00", "note": "đổi giờ",
    }, follow_redirects=False)

    muc = crud.get_event(db, muc.id)
    assert (muc.title, muc.start, muc.end) == ("Mới", "20:00", "22:00")


def test_xoa_mot_muc_quay_ve_dung_ngay(logged_in, db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc", "08:00")

    res = logged_in.post(f"/schedule/delete/{muc.id}", follow_redirects=False)

    assert f"open={quote(MEMBER + ':2025-03-14')}" in res.headers["location"]
    assert crud.get_week_events(db, "2025-03-10") == []


def test_khong_xoa_duoc_muc_lich_bang_get(logged_in, db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc", "08:00")

    assert logged_in.get(f"/schedule/delete/{muc.id}",
                         follow_redirects=False).status_code == 405
    assert len(crud.get_week_events(db, "2025-03-10")) == 1


def test_lich_hien_viec_cua_ca_hai_dua(logged_in, db):
    crud.create_event(db, MEMBER, "2025-03-14", "Việc của mình", "08:00")
    crud.create_event(db, ADMIN, "2025-03-12", "Việc của người kia", "10:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "Việc của mình" in trang
    assert "Việc của người kia" in trang


def test_khung_gio_noi_ra_om_het_viec_som_va_muon(logged_in, db):
    """Khung mặc định là 07:00-22:00; việc 05:30 và 23:00 phải kéo nó rộng ra."""
    crud.create_event(db, MEMBER, "2025-03-14", "Dậy sớm", "05:30", "06:30")
    crud.create_event(db, MEMBER, "2025-03-14", "Về muộn", "23:00", "23:45")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert ">05:00<" in trang
    assert ">24:00<" in trang


def test_hai_viec_trung_gio_nam_canh_nhau_chu_khong_de_len_nhau(logged_in, db):
    """Không chia làn thì cái dưới bị che mất hẳn, nhìn như chưa từng thêm."""
    crud.create_event(db, MEMBER, "2025-03-14", "Học", "08:00", "10:00")
    crud.create_event(db, MEMBER, "2025-03-14", "Họp", "09:00", "11:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "width: 50.0%" in trang
    assert "left: 50.0%" in trang


def test_viec_khong_trung_gio_thi_chiem_ca_cot(logged_in, db):
    crud.create_event(db, MEMBER, "2025-03-14", "Học", "08:00", "10:00")
    crud.create_event(db, MEMBER, "2025-03-14", "Họp", "10:00", "11:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "width: 100.0%" in trang
    assert "width: 50.0%" not in trang


# ---------- ngày đặc biệt: hai đường + phần nối ----------

def test_danh_dau_ngay_dac_biet_thi_hien_hai_duong(logged_in, db):
    logged_in.post("/schedule/special",
                   data={"date": "2025-03-14", "title": "Kỷ niệm"},
                   follow_redirects=False)

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "Kỷ niệm" in trang
    assert trang.count('class="sp-line') == 2          # đúng hai đường thời gian
    assert 'class="sp-link"' in trang


def test_ngay_thuong_khong_ve_hai_duong(logged_in):
    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert 'class="sp-link"' not in trang


def test_phan_noi_chi_ra_luc_ca_hai_cung_ranh(logged_in, db):
    """Mình bận 08-10, người kia bận 08-09 → 10:00 trở đi là rảnh cùng nhau."""
    crud.toggle_special_day(db, "2025-03-14", "Hẹn")
    crud.create_event(db, MEMBER, "2025-03-14", "Học", "08:00", "10:00")
    crud.create_event(db, ADMIN, "2025-03-14", "Lab", "08:00", "09:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert 'sp-band free' in trang
    assert "10:00" in trang


def test_phan_noi_chi_ra_luc_ca_hai_cung_ban(logged_in, db):
    crud.toggle_special_day(db, "2025-03-14", "Hẹn")
    crud.create_event(db, MEMBER, "2025-03-14", "Học", "08:00", "10:00")
    crud.create_event(db, ADMIN, "2025-03-14", "Lab", "09:00", "11:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "sp-band busy" in trang


def test_ca_hai_kin_lich_thi_khong_co_luc_nao_ranh_cung_nhau(logged_in, db):
    crud.toggle_special_day(db, "2025-03-14", "Kín mít")

    for ai in (MEMBER, ADMIN):
        crud.create_event(db, ai, "2025-03-14", "Bận", "07:00", "22:00")

    trang = logged_in.get("/schedule?week=2025-03-10").text

    assert "không có lúc nào" in trang
    assert "sp-band free" not in trang


def test_bo_dau_ngay_dac_biet(logged_in, db):
    crud.toggle_special_day(db, "2025-03-14", "Kỷ niệm")

    logged_in.post("/schedule/special", data={"date": "2025-03-14", "title": ""},
                   follow_redirects=False)

    assert crud.get_special_day(db, "2025-03-14") is None


def test_danh_dau_xong_quay_ve_dung_tuan(logged_in):
    res = logged_in.post("/schedule/special",
                         data={"date": "2025-03-14", "title": "Kỷ niệm"},
                         follow_redirects=False)

    assert "week=2025-03-10" in res.headers["location"]


# ---------- linh tinh ----------

def test_healthz_bao_dang_dung_database_nao(logged_in):
    body = logged_in.get("/healthz").json()

    assert body["ok"] is True
    assert "database" in body


def test_thanh_dieu_huong_hien_ten_nguoi_dang_dang_nhap(logged_in):
    from tests.conftest import MEMBER

    assert MEMBER in logged_in.get("/").text
