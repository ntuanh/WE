"""Test cho lớp crud — nơi mọi dữ liệu được làm sạch trước khi vào database."""

from datetime import date

import pytest

from app import crud
from tests.conftest import ADMIN, MEMBER


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


# ---------- LỊCH ----------

def test_hai_chu_lich_lay_tu_danh_sach_tai_khoan(db):
    """Tên hai bảng không viết cứng ở đâu cả — có tài khoản nào, bảng nấy."""
    assert crud.people() == sorted([ADMIN, MEMBER])


@pytest.mark.parametrize("vao, ra", [
    ("08:30", "08:30"),
    ("8:5", "08:05"),
    ("08:30:00", "08:30"),
    ("", ""),
    ("linh tinh", ""),
    ("25:00", ""),
    (None, ""),
])
def test_valid_time(vao, ra):
    assert crud.valid_time(vao) == ra


@pytest.mark.parametrize("vao, ra", [("08:30", 510), ("00:00", 0), ("", 0), ("xx", 0)])
def test_doi_gio_ra_phut(vao, ra):
    assert crud.minutes(vao) == ra


@pytest.mark.parametrize("vao, ra", [(510, "08:30"), (0, "00:00"), (99_999, "23:59"), (-5, "00:00")])
def test_doi_phut_ra_gio(vao, ra):
    assert crud.hhmm(vao) == ra


def test_khong_ghi_gio_ket_thuc_thi_dai_mot_tieng(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc", "08:00")

    assert (muc.start, muc.end) == ("08:00", "09:00")


def test_gio_ket_thuc_truoc_gio_bat_dau_bi_day_ve_sau(db):
    """Để nguyên thì ô việc có chiều cao âm và thời gian biểu vỡ hình."""
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc", "14:00", "09:00")

    assert (muc.start, muc.end) == ("14:00", "15:00")


def test_viec_ca_ngay_khong_co_gio_nao(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Về quê", "", "17:00")

    assert (muc.start, muc.end) == ("", "")


def test_gio_ket_thuc_khong_tran_sang_ngay_hom_sau(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Khuya", "23:30")

    assert muc.end == "23:59"


def test_thu_hai_cua_tuan(db):
    # 2025-03-14 la thu 6
    assert crud.monday_of("2025-03-14") == "2025-03-10"
    assert crud.monday_of("2025-03-10") == "2025-03-10"
    assert crud.monday_of("2025-03-16") == "2025-03-10"      # chu nhat van thuoc tuan do


def test_bay_ngay_cua_tuan(db):
    days = crud.week_days("2025-03-14")

    assert days[0] == "2025-03-10" and days[-1] == "2025-03-16"
    assert len(days) == 7


def test_chi_lay_viec_trong_tuan(db):
    crud.create_event(db, MEMBER, "2025-03-14", "Trong tuần", "08:00")
    crud.create_event(db, MEMBER, "2025-03-20", "Tuần sau", "08:00")

    trong_tuan = crud.get_week_events(db, "2025-03-10")

    assert [e.title for e in trong_tuan] == ["Trong tuần"]


def test_lich_xep_theo_ngay_roi_theo_gio(db):
    crud.create_event(db, MEMBER, "2025-03-15", "Trưa", "12:00")
    crud.create_event(db, MEMBER, "2025-03-14", "Chiều", "17:00")
    crud.create_event(db, MEMBER, "2025-03-14", "Sáng", "07:00")
    crud.create_event(db, MEMBER, "2025-03-14", "Cả ngày")

    assert [e.title for e in crud.get_week_events(db, "2025-03-10")] == \
           ["Cả ngày", "Sáng", "Chiều", "Trưa"]


def test_loc_theo_chu_lich(db):
    crud.create_event(db, MEMBER, "2025-03-14", "Của mình", "08:00")
    crud.create_event(db, ADMIN, "2025-03-14", "Của người kia", "08:00")

    cua_toi = crud.get_week_events(db, "2025-03-10", owner=MEMBER)

    assert [e.title for e in cua_toi] == ["Của mình"]


def test_khong_them_duoc_vao_lich_nguoi_la(db):
    """Gõ sai tên mà lẳng lặng nhét sang lịch người kia thì tai hại hơn là báo lỗi."""
    assert crud.create_event(db, "nguoi-la", "2025-03-14", "Việc") is None
    assert crud.get_week_events(db, "2025-03-10") == []


def test_khong_them_duoc_muc_khong_co_ten(db):
    assert crud.create_event(db, MEMBER, "2025-03-14", "   ") is None
    assert crud.get_week_events(db, "2025-03-10") == []


def test_sua_mot_muc_trong_lich(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Cũ", "08:00", "09:00", "ghi chú")

    crud.update_event(db, muc.id, "Mới", "9:30", "11:00", "khác")

    muc = crud.get_event(db, muc.id)
    assert (muc.title, muc.start, muc.end, muc.note) == ("Mới", "09:30", "11:00", "khác")


def test_sua_thanh_ten_rong_thi_khong_luu(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Giữ nguyên", "08:00")

    assert crud.update_event(db, muc.id, "", "08:00", "09:00", "") is None
    assert crud.get_event(db, muc.id).title == "Giữ nguyên"


def test_xoa_mot_muc(db):
    muc = crud.create_event(db, MEMBER, "2025-03-14", "Việc", "08:00")

    assert crud.delete_event(db, muc.id) is True
    assert crud.get_week_events(db, "2025-03-10") == []


# ---------- NGÀY ĐẶC BIỆT ----------

def test_danh_dau_roi_bo_dau_ngay_dac_biet(db):
    assert crud.toggle_special_day(db, "2025-03-14", "Kỷ niệm").title == "Kỷ niệm"
    assert crud.get_special_day(db, "2025-03-14") is not None

    assert crud.toggle_special_day(db, "2025-03-14") is None
    assert crud.get_special_day(db, "2025-03-14") is None


def test_go_ten_moi_thi_la_doi_ten_chu_khong_phai_bo_dau(db):
    """Bấm nhầm nút mà mất luôn tên vừa gõ thì ức chế."""
    crud.toggle_special_day(db, "2025-03-14", "Kỷ niệm")

    lai = crud.toggle_special_day(db, "2025-03-14", "Sinh nhật")

    assert lai is not None and lai.title == "Sinh nhật"


def test_chi_lay_ngay_dac_biet_trong_khoang(db):
    crud.toggle_special_day(db, "2025-03-14", "Trong tuần")
    crud.toggle_special_day(db, "2025-03-25", "Ngoài tuần")

    trong = crud.get_special_days(db, "2025-03-10", "2025-03-16")

    assert [s.title for s in trong] == ["Trong tuần"]
