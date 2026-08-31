"""Test cho lớp crud — nơi mọi dữ liệu được làm sạch trước khi vào database."""

from datetime import date

import pytest

from app import crud


# ---------- hàm làm sạch dùng chung ----------

@pytest.mark.parametrize("vao, ra", [
    ("  Bún chả  ", "Bún chả"),
    (None, ""),
    ("", ""),
    (123, "123"),
    ("\n\t xin chào \n", "xin chào"),
])
def test_clean_bo_khoang_trang_thua(vao, ra):
    assert crud.clean(vao) == ra


def test_clean_cat_bot_chuoi_qua_dai():
    assert len(crud.clean("a" * 9999)) == crud.MAX_TEXT


@pytest.mark.parametrize("vao, ra", [
    ("2025-03-14", "2025-03-14"),
    ("14/03/2025", None),      # sai định dạng -> hôm nay
    ("linh tinh", None),
    ("", None),
    ("2025-02-30", None),      # ngày không tồn tại
])
def test_valid_date(vao, ra):
    ket_qua = crud.valid_date(vao)
    assert ket_qua == (ra or date.today().isoformat())


def test_valid_date_khong_ep_hom_nay_khi_khong_muon():
    """Deadline để trống là hợp lệ — đừng tự điền hôm nay vào."""
    assert crud.valid_date("", fallback_today=False) == ""


@pytest.mark.parametrize("vao, ra", [
    ("2025-03", "2025-03"),
    ("2025-13", None),         # tháng 13 -> tháng này
    ("linh tinh", None),
    ("", None),
])
def test_valid_month(vao, ra):
    assert crud.valid_month(vao) == (ra or date.today().strftime("%Y-%m"))


# ---------- FOOD ----------

def test_them_va_lay_lai_quan_an(db):
    crud.create_food(db, "  Phở Thìn ", " Lò Đúc ", "ngon", "da_an", "", 5)

    quan = crud.get_foods(db)[0]

    assert quan.name == "Phở Thìn"       # đã cắt khoảng trắng
    assert quan.address == "Lò Đúc"
    assert quan.rating == 5


@pytest.mark.parametrize("rating, mong_doi", [
    (3, 3), (0, 0), (5, 5),
    (99, 5),          # quá tay thì kẹp về 5
    (-4, 0),          # âm thì kẹp về 0
    ("bốn", 0),       # không phải số
    (None, 0),
])
def test_diem_danh_gia_luon_nam_trong_0_5(db, rating, mong_doi):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "da_an", "", rating)
    assert quan.rating == mong_doi


def test_trang_thai_la_thi_ve_mac_dinh(db):
    """Người ta sửa HTML gửi status=xoa_het thì cũng không lọt được."""
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "xoa_het_di")
    assert quan.status == "muon_an"


def test_doi_cot_bang_keo_tha(db):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "muon_an")

    assert crud.update_food_status(db, quan.id, "da_an") is not None
    assert crud.get_food(db, quan.id).status == "da_an"


def test_keo_tha_sang_cot_khong_ton_tai_thi_khong_luu(db):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "muon_an")

    assert crud.update_food_status(db, quan.id, "cot-bia-dat") is None
    assert crud.get_food(db, quan.id).status == "muon_an"     # giữ nguyên


def test_sua_quan_khong_ton_tai_tra_none(db):
    assert crud.update_food(db, 999, "a", "b", "", "", 0, "da_an") is None


def test_xoa_quan(db):
    quan = crud.create_food(db, "Quán", "Đâu đó", "", "da_an")

    assert crud.delete_food(db, quan.id) is True
    assert crud.get_foods(db) == []


def test_xoa_thu_khong_ton_tai_tra_false(db):
    assert crud.delete_food(db, 12345) is False


# ---------- PLAN ----------

def test_ke_hoach_chua_xong_len_truoc(db):
    xong = crud.create_plan(db, "Việc đã xong", "")
    crud.create_plan(db, "Việc chưa xong", "")
    crud.update_plan_status(db, xong.id, 1)

    assert [p.title for p in crud.get_plans(db)][0] == "Việc chưa xong"


@pytest.mark.parametrize("vao, ra", [
    (1, 1), (0, 0), (True, 1), (False, 0),
    ("1", 1),
    (99, 1),          # kẹp về 1
    ("linh tinh", 0),
])
def test_done_luon_la_0_hoac_1(db, vao, ra):
    ke_hoach = crud.create_plan(db, "Việc", "")
    assert crud.update_plan_status(db, ke_hoach.id, vao).done == ra


def test_muc_do_uu_tien_la_thi_ve_normal(db):
    assert crud.create_plan(db, "Việc", "", "sieu-gap").priority == "normal"


def test_sua_ke_hoach(db):
    ke_hoach = crud.create_plan(db, "Cũ", "mô tả cũ", "low", "")

    crud.update_plan(db, ke_hoach.id, "Mới", "mô tả mới", "high", "2025-12-25")

    ke_hoach = crud.get_plan(db, ke_hoach.id)
    assert (ke_hoach.title, ke_hoach.priority, ke_hoach.deadline) == \
           ("Mới", "high", "2025-12-25")


# ---------- MONEY ----------

def test_chi_lay_giao_dich_dung_thang(db):
    crud.create_transaction(db, 50_000, "out", "an", "tháng 3", "2025-03-14")
    crud.create_transaction(db, 60_000, "out", "an", "tháng 4", "2025-04-01")

    thang_ba = crud.get_transactions(db, "2025-03")

    assert len(thang_ba) == 1
    assert thang_ba[0].note == "tháng 3"


def test_so_tien_am_bi_kep_ve_0(db):
    """Cột amount luôn là số dương, dấu nằm ở `kind`."""
    assert crud.create_transaction(db, -50_000, "out", "an", "", "2025-03-14").amount == 0


def test_hang_muc_la_thi_ve_khac(db):
    tx = crud.create_transaction(db, 1000, "out", "hang-muc-bia", "", "2025-03-14")
    assert tx.category == "khac"


def test_dat_han_muc_va_sua_lai(db):
    crud.set_budget(db, "2025-03", 3_000_000)
    crud.set_budget(db, "2025-03", 4_000_000)      # sửa, không tạo thêm dòng mới

    assert crud.get_budget(db, "2025-03").amount == 4_000_000


def test_danh_sach_thang_moi_nhat_truoc(db):
    for ngay in ("2025-01-05", "2025-03-14", "2025-02-20", "2025-03-30"):
        crud.create_transaction(db, 1000, "out", "an", "", ngay)

    assert crud.get_months(db) == ["2025-03", "2025-02", "2025-01"]


# ---------- import sao kê ----------

def _dong(ref="", ngay="2025-03-14", tien=50_000, ghi_chu="Highlands"):
    return {"amount": tien, "kind": "out", "category": "an", "note": ghi_chu,
            "date": ngay, "source": "momo", "ref": ref}


def test_import_lan_dau_ghi_het(db):
    them, bo_qua = crud.import_transactions(db, [_dong("GD1"), _dong("GD2")])

    assert (them, bo_qua) == (2, 0)


def test_import_lai_dung_file_cu_khong_nhan_doi(db):
    rows = [_dong("GD1"), _dong("GD2")]

    crud.import_transactions(db, rows)
    them, bo_qua = crud.import_transactions(db, rows)

    assert (them, bo_qua) == (0, 2)
    assert len(crud.get_transactions(db, "2025-03")) == 2


def test_khong_co_ma_giao_dich_thi_so_theo_ngay_tien_ghi_chu(db):
    rows = [_dong(ref="")]

    crud.import_transactions(db, rows)
    them, bo_qua = crud.import_transactions(db, rows)

    assert (them, bo_qua) == (0, 1)


def test_hai_giao_dich_giong_het_trong_cung_file_van_giu_ca_hai_neu_khac_ma(db):
    """Đi ăn hai lần cùng ngày cùng giá — có mã GD thì không được gộp."""
    them, _ = crud.import_transactions(db, [_dong("GD1"), _dong("GD2")])

    assert them == 2


def test_dong_trung_trong_chinh_mot_file_bi_bo_qua(db):
    """File sao kê thỉnh thoảng lặp dòng; không có mã thì coi như một."""
    them, bo_qua = crud.import_transactions(db, [_dong(ref=""), _dong(ref="")])

    assert (them, bo_qua) == (1, 1)


def test_import_danh_sach_rong(db):
    assert crud.import_transactions(db, []) == (0, 0)
    assert crud.import_transactions(db, None) == (0, 0)


def test_import_lai_dong_co_ngay_hong_van_khong_nhan_doi(db):
    """Ngày hỏng được chuẩn hoá về hôm nay lúc ghi; khoá so trùng phải dùng
    đúng giá trị đã chuẩn hoá đó, không thì lần import sau ghi lại lần nữa."""
    rows = [_dong(ref="", ngay="ngay-hong")]

    crud.import_transactions(db, rows)
    them, bo_qua = crud.import_transactions(db, rows)

    assert (them, bo_qua) == (0, 1)


def test_import_lam_sach_du_lieu_ban(db):
    them, _ = crud.import_transactions(db, [
        {"amount": "-99", "kind": "linh tinh", "category": "bia dat",
         "note": "  x  ", "date": "sai bet", "source": "?", "ref": ""},
    ])

    tx = db.query(crud.models.Transaction).one()

    assert them == 1
    assert tx.amount == 0
    assert tx.kind == "out"
    assert tx.category == "khac"
    assert tx.note == "x"
    assert tx.date == date.today().isoformat()
