"""Test cho các route — đi qua HTTP thật, có đăng nhập sẵn."""

from urllib.parse import unquote

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


# ---------- chi tiêu ----------

def test_them_giao_dich(logged_in, db):
    res = logged_in.post("/budget/add", data={
        "amount": "150000", "kind": "out", "category": "an",
        "note": "Ăn trưa", "date": "2025-03-14", "source": "momo",
    }, follow_redirects=False)

    assert res.headers["location"].startswith("/budget?month=2025-03")
    assert crud.get_transactions(db, "2025-03")[0].amount == 150_000


def test_so_tien_co_dau_cham_van_hieu(logged_in, db):
    """Gõ "150.000" theo thói quen thì cũng phải hiểu."""
    logged_in.post("/budget/add", data={
        "amount": "150.000", "kind": "out", "category": "an",
        "note": "", "date": "2025-03-14", "source": "momo",
    }, follow_redirects=False)

    assert crud.get_transactions(db, "2025-03")[0].amount == 150_000


@pytest.mark.parametrize("so_tien", ["", "0", "-5000", "linh tinh"])
def test_so_tien_khong_hop_le_thi_bao_loi_chu_khong_500(logged_in, db, so_tien):
    res = logged_in.post("/budget/add", data={
        "amount": so_tien, "kind": "out", "category": "an",
        "note": "", "date": "2025-03-14", "source": "momo",
    }, follow_redirects=False)

    assert res.status_code == 303
    assert "msg=" in res.headers["location"]
    assert crud.get_transactions(db, "2025-03") == []


def test_thang_bay_ba_khong_lam_vo_trang(logged_in):
    """int(month[:4]) trong _summarise sẽ nổ nếu month không phải YYYY-MM."""
    assert logged_in.get("/budget?month=linh-tinh").status_code == 200
    assert logged_in.get("/budget?month=9999-99").status_code == 200
    assert logged_in.get("/budget?month=").status_code == 200


def test_dat_han_muc(logged_in, db):
    logged_in.post("/budget/set", data={"month": "2025-03", "amount": "5000000"},
                   follow_redirects=False)

    assert crud.get_budget(db, "2025-03").amount == 5_000_000


def test_xoa_giao_dich_quay_ve_dung_thang(logged_in, db):
    tx = crud.create_transaction(db, 50_000, "out", "an", "", "2025-03-14")

    res = logged_in.post(f"/budget/delete/{tx.id}", follow_redirects=False)

    assert "month=2025-03" in res.headers["location"]
    assert crud.get_transactions(db, "2025-03") == []


def test_trang_chi_tieu_cong_dung_tong(logged_in, db):
    crud.create_transaction(db, 100_000, "out", "an", "", "2025-03-01")
    crud.create_transaction(db, 50_000, "out", "di_lai", "", "2025-03-02")
    crud.create_transaction(db, 500_000, "in", "khac", "Lương", "2025-03-03")

    trang = logged_in.get("/budget?month=2025-03").text

    assert "150.000" in trang       # tổng chi
    assert "500.000" in trang       # tổng thu


# ---------- nhập sao kê ----------

SAO_KE = (
    "Thời gian,Số tiền,Mô tả,Mã giao dịch\n"
    "14/03/2025 12:30:00,-50.000,Highlands Coffee,GD001\n"
    "15/03/2025 08:00:00,-120.000,Grab,GD002\n"
    "16/03/2025 09:00:00,+2.000.000,Nhận tiền,GD003\n"
)


def test_nhap_file_sao_ke(logged_in, db):
    res = logged_in.post("/budget/import",
                         files={"file": ("saoke.csv", SAO_KE.encode(), "text/csv")},
                         follow_redirects=False)

    assert "Đã nhập 3 giao dịch" in unquote(res.headers["location"])
    assert len(crud.get_transactions(db, "2025-03")) == 3


def test_nhap_lai_dung_file_do_khong_nhan_doi(logged_in, db):
    for _ in range(2):
        logged_in.post("/budget/import",
                       files={"file": ("saoke.csv", SAO_KE.encode(), "text/csv")},
                       follow_redirects=False)

    assert len(crud.get_transactions(db, "2025-03")) == 3


def test_file_khong_phai_sao_ke_thi_bao_nhe_nhang(logged_in, db):
    res = logged_in.post("/budget/import",
                         files={"file": ("anh.csv", b"day khong phai csv", "text/csv")},
                         follow_redirects=False)

    assert res.status_code == 303
    assert "msg=" in res.headers["location"]
    assert crud.get_months(db) == []


def test_file_qua_lon_bi_tu_choi(logged_in):
    to_qua = b"x" * (5 * 1024 * 1024 + 100)

    res = logged_in.post("/budget/import",
                         files={"file": ("to.csv", to_qua, "text/csv")},
                         follow_redirects=False)

    assert "lớn quá" in unquote(res.headers["location"])


# ---------- linh tinh ----------

def test_healthz_bao_dang_dung_database_nao(logged_in):
    body = logged_in.get("/healthz").json()

    assert body["ok"] is True
    assert "database" in body


def test_thanh_dieu_huong_hien_ten_nguoi_dang_dang_nhap(logged_in):
    from tests.conftest import MEMBER

    assert MEMBER in logged_in.get("/").text
