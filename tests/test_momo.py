"""Test cho bộ đọc sao kê MoMo.

Mỗi bản xuất của MoMo đặt tên cột một kiểu, nên phần lớn test ở đây là đưa vào
các biến thể header khác nhau và đòi kết quả giống nhau.
"""

import pytest

from app import momo


# ---------- bỏ dấu ----------

@pytest.mark.parametrize("vao, ra", [
    ("Thời gian", "thoi gian"),
    ("Số tiền", "so tien"),
    ("Mã giao dịch", "ma giao dich"),
    ("ĐƠN HÀNG", "don hang"),
    ("", ""),
    (None, ""),
])
def test_strip_accents(vao, ra):
    assert momo.strip_accents(vao) == ra


# ---------- đọc số tiền ----------

@pytest.mark.parametrize("vao, tien, loai", [
    ("-50.000đ", 50_000, "out"),
    ("+1,200,000", 1_200_000, "in"),
    ("50000", 50_000, "in"),
    ("(75.000)", 75_000, "out"),      # kế toán ghi số âm bằng ngoặc
    ("-2.000.000 VND", 2_000_000, "out"),
    ("", 0, None),
    (None, 0, None),
    ("linh tinh", 0, None),
    ("   ", 0, None),
])
def test_parse_amount(vao, tien, loai):
    assert momo.parse_amount(vao) == (tien, loai)


# ---------- đọc ngày ----------

@pytest.mark.parametrize("vao, ra", [
    ("14/03/2025", "2025-03-14"),
    ("14/03/2025 12:30:00", "2025-03-14"),
    ("2025/03/14", "2025-03-14"),
    ("14-03-2025", "2025-03-14"),
    ("14.03.2025", "2025-03-14"),
    ("", ""),
    (None, ""),
    ("hôm qua", ""),
])
def test_parse_date(vao, ra):
    assert momo.parse_date(vao) == ra


# ---------- đoán hạng mục ----------

@pytest.mark.parametrize("mo_ta, hang_muc", [
    ("Thanh toán Highlands Coffee", "an"),
    ("HIGHLANDS COFFEE", "an"),
    ("Chuyển tiền Grab", "di_lai"),
    ("Mua hàng Shopee", "mua_sam"),
    ("Thanh toán tiền điện EVN", "hoa_don"),
    ("Netflix Premium", "giai_tri"),
    ("Chuyển tiền cho bạn", "khac"),
    ("", "khac"),
])
def test_guess_category(mo_ta, hang_muc):
    assert momo.guess_category(mo_ta) == hang_muc


def test_doan_hang_muc_khong_phu_thuoc_dau_tieng_viet():
    assert momo.guess_category("Ca phe sang") == momo.guess_category("Cà phê sáng")


# ---------- đọc cả file ----------

CHUAN = (
    "Thời gian,Số tiền,Mô tả,Mã giao dịch\n"
    "14/03/2025 12:30:00,-50.000,Highlands Coffee,GD001\n"
)


def test_doc_file_chuan():
    rows = momo.parse_csv(CHUAN.encode())

    assert len(rows) == 1
    assert rows[0] == {
        "amount": 50_000, "kind": "out", "category": "an",
        "note": "Highlands Coffee", "date": "2025-03-14",
        "source": "momo", "ref": "GD001",
    }


def test_dau_cham_phay_cung_doc_duoc():
    """Máy đặt locale tiếng Việt thì Excel xuất ra dấu chấm phẩy."""
    data = ("Thời gian;Số tiền;Mô tả;Mã giao dịch\n"
            "14/03/2025;-50000;Highlands;GD001\n")

    assert momo.parse_csv(data.encode())[0]["amount"] == 50_000


def test_dang_hai_cot_tien_ra_tien_vao():
    data = ("Ngày,Tiền ra,Tiền vào,Nội dung\n"
            "14/03/2025,50000,,Highlands\n"
            "15/03/2025,,2000000,Nhận lương\n")

    rows = momo.parse_csv(data.encode())

    assert [(r["amount"], r["kind"]) for r in rows] == [(50_000, "out"), (2_000_000, "in")]


def test_ten_cot_tieng_anh():
    data = ("Date,Amount,Description,Transaction ID\n"
            "14/03/2025,-50000,Coffee,TX1\n")

    assert momo.parse_csv(data.encode())[0]["ref"] == "TX1"


def test_bo_qua_dong_thieu_ngay_hoac_thieu_tien():
    data = ("Thời gian,Số tiền,Mô tả\n"
            "14/03/2025,-50.000,Có đủ\n"
            ",-60.000,Thiếu ngày\n"
            "16/03/2025,,Thiếu tiền\n"
            "linh tinh,-70.000,Ngày hỏng\n")

    rows = momo.parse_csv(data.encode())

    assert len(rows) == 1
    assert rows[0]["note"] == "Có đủ"


def test_dong_khong_co_mo_ta_van_co_ten_mac_dinh():
    data = "Thời gian,Số tiền,Mô tả\n14/03/2025,-50000,\n"

    assert momo.parse_csv(data.encode())[0]["note"] == "Giao dịch MoMo"


@pytest.mark.parametrize("ma_hoa", ["utf-8-sig", "utf-16", "utf-8"])
def test_doc_duoc_nhieu_kieu_ma_hoa(ma_hoa):
    """MoMo có bản xuất UTF-8-BOM, có bản UTF-16."""
    rows = momo.parse_csv(CHUAN.encode(ma_hoa))

    assert len(rows) == 1
    assert rows[0]["date"] == "2025-03-14"


@pytest.mark.parametrize("rac", [
    b"",
    b"day khong phai csv",
    b"\x00\x01\x02\x03",
    "Cột lạ,Cột lạ hơn\na,b\n".encode(),
])
def test_file_rac_tra_ve_rong_chu_khong_no(rac):
    assert momo.parse_csv(rac) == []


def test_moi_hang_muc_deu_co_nhan_va_mau():
    """Template đọc thẳng CATEGORIES[key][0] và [1] — thiếu là vỡ trang."""
    for key, (nhan, mau) in momo.CATEGORIES.items():
        assert nhan and mau.startswith("oklch(")
