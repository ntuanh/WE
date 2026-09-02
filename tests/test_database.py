"""Test cho phần database — nhất là chuyện "cứ thêm hàm mới là mất dữ liệu".

Kịch bản gây mất dữ liệu trước đây:
  1. thêm một cột mới vào models.py
  2. khởi động lại — create_all() không đụng gì tới bảng đã tồn tại
  3. mở trang đó ra: "no such column"
  4. chữa bằng cách xoá we.db → schema đúng trở lại, dữ liệu thì bay sạch

Test dưới đây dựng lại đúng kịch bản đó và đòi hỏi dữ liệu phải còn nguyên.
"""

import os

import pytest
from sqlalchemy import Column, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud, database, migrations, models
from tests.conftest import ROOT
from app.database import Base


def _engine_moi(tmp_path, ten="thu.db"):
    """Một file SQLite thật (không phải RAM) để mô phỏng we.db."""
    return create_engine(
        f"sqlite:///{tmp_path / ten}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_them_cot_moi_khong_lam_mat_du_lieu_cu(tmp_path, monkeypatch):
    """Đây là bài test quan trọng nhất của file này."""
    engine = _engine_moi(tmp_path)
    Session = sessionmaker(bind=engine)

    # --- "phiên bản cũ" của app: bảng plans chưa có cột nào mới ---
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE plans (id INTEGER PRIMARY KEY, title VARCHAR, script VARCHAR)"
        ))
        conn.execute(text(
            "INSERT INTO plans (title, script) VALUES ('Đi Đà Lạt', 'nhớ mang áo ấm')"
        ))

    # --- deploy "phiên bản mới": models.py đã có priority / deadline / done ---
    monkeypatch.setattr(migrations, "engine", engine)
    monkeypatch.setattr(database, "engine", engine)

    Base.metadata.create_all(bind=engine)
    applied = migrations.run()

    # cột mới đã được thêm...
    cot = {c["name"] for c in inspect(engine).get_columns("plans")}
    assert {"priority", "deadline", "done"} <= cot
    assert any("plans.priority" in a for a in applied)

    # ...và kế hoạch cũ vẫn còn nguyên, có giá trị mặc định cho cột mới
    session = Session()
    try:
        plan = session.query(models.Plan).one()

        assert plan.title == "Đi Đà Lạt"
        assert plan.script == "nhớ mang áo ấm"
        assert plan.priority == "normal"     # default lấy thẳng từ models.py
        assert plan.done == 0
    finally:
        session.close()
        engine.dispose()


def test_chay_migration_nhieu_lan_van_khong_sao(tmp_path, monkeypatch):
    """Migration chạy mỗi lần khởi động, nên chạy lại phải là không-làm-gì."""
    engine = _engine_moi(tmp_path)
    monkeypatch.setattr(migrations, "engine", engine)

    Base.metadata.create_all(bind=engine)

    assert migrations.run() == []      # schema đã đúng ngay từ create_all
    assert migrations.run() == []      # lần hai cũng vậy

    engine.dispose()


def test_cot_moi_kieu_gi_cung_tu_them_duoc(tmp_path, monkeypatch):
    """Cột mới không cần khai báo tay ở migrations.py nữa — đây là điểm mấu chốt.

    Trước kia NEW_COLUMNS là một dict viết tay: quên cập nhật là lại "no such
    column". Giờ danh sách cột đọc thẳng từ model.
    """
    engine = _engine_moi(tmp_path)
    monkeypatch.setattr(migrations, "engine", engine)

    Base.metadata.create_all(bind=engine)

    # giả lập lập trình viên vừa thêm hai trường vào models.py
    bang = Base.metadata.tables["study_places"]
    them = [
        Column("wifi_password", String, default=""),
        Column("do_on_ao", Integer, default=3),
    ]
    for col in them:
        bang.append_column(col)

    try:
        applied = migrations.run()

        cot = {c["name"] for c in inspect(engine).get_columns("study_places")}
        assert "wifi_password" in cot
        assert "do_on_ao" in cot
        assert len(applied) == 2
    finally:
        # trả models.py về nguyên trạng, không thì rò sang test khác
        for col in them:
            bang._columns.remove(col)
        engine.dispose()


def test_hang_cu_duoc_dien_gia_tri_mac_dinh(tmp_path, monkeypatch):
    """Cột thêm sau mà để NULL thì template phải xử lý None khắp nơi."""
    engine = _engine_moi(tmp_path)
    monkeypatch.setattr(migrations, "engine", engine)

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE food_places (id INTEGER PRIMARY KEY, name VARCHAR, "
            "address VARCHAR, note VARCHAR, status VARCHAR)"
        ))
        conn.execute(text("INSERT INTO food_places (name, status) VALUES ('Quán cũ', 'da_an')"))

    Base.metadata.create_all(bind=engine)
    migrations.run()

    with engine.begin() as conn:
        rating, image = conn.execute(
            text("SELECT rating, image FROM food_places")).one()

    assert rating == 0        # không phải None
    assert image == ""

    engine.dispose()


def test_quan_chua_an_duoc_don_sang_muon_an(tmp_path, monkeypatch):
    """Cột "Chưa ăn" đã bỏ: hàng cũ mang trạng thái đó phải được dồn sang
    "Muốn ăn", nếu không nó không hiện ở cột nào cả — nhìn như mất dữ liệu."""
    engine = _engine_moi(tmp_path)
    monkeypatch.setattr(migrations, "engine", engine)

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO food_places (name, status) VALUES ('Quán treo', 'chua_an')"))
        conn.execute(text(
            "INSERT INTO food_places (name, status) VALUES ('Quán quen', 'da_an')"))

    applied = migrations.run()

    with engine.begin() as conn:
        con_lai = dict(conn.execute(text("SELECT name, status FROM food_places")).all())

    assert con_lai == {"Quán treo": "muon_an", "Quán quen": "da_an"}
    assert any("chua_an" in viec for viec in applied)

    # chạy lại lần nữa: không còn gì để đổi, cũng không được báo đã làm gì
    assert not [viec for viec in migrations.run() if "chua_an" in viec]

    engine.dispose()


def test_du_lieu_song_qua_lan_khoi_dong_lai(tmp_path, monkeypatch):
    """Ghi → đóng hẳn → mở lại: dữ liệu phải còn. Kiểm tra rằng chỗ lưu là
    file thật chứ không phải RAM."""
    duong_dan = tmp_path / "we.db"

    engine = _engine_moi(tmp_path, "we.db")
    monkeypatch.setattr(migrations, "engine", engine)
    Base.metadata.create_all(bind=engine)

    session = sessionmaker(bind=engine)()
    crud.create_study(session, "Thư viện Tạ Quang Bửu", "Bách Khoa", "yên tĩnh")
    session.close()
    engine.dispose()                       # "tắt app"

    engine2 = _engine_moi(tmp_path, "we.db")   # "bật lại app"
    monkeypatch.setattr(migrations, "engine", engine2)
    Base.metadata.create_all(bind=engine2)
    migrations.run()

    session2 = sessionmaker(bind=engine2)()
    try:
        assert duong_dan.exists()
        assert crud.get_studies(session2)[0].name == "Thư viện Tạ Quang Bửu"
    finally:
        session2.close()
        engine2.dispose()


# ---------- chọn chỗ lưu database ----------

def test_uu_tien_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert database._database_url() == "postgresql://u:p@host/db"


def test_doi_postgres_scheme_cho_sqlalchemy(monkeypatch):
    """Neon/Supabase phát ra postgres://, SQLAlchemy 2 không hiểu scheme đó."""
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert database._database_url().startswith("postgresql://")


def test_sqlite_path_tro_ra_o_dia_gan_ngoai(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "data" / "we.db"))

    url = database._database_url()

    assert url.startswith("sqlite:///")
    assert "data" in url
    assert (tmp_path / "data").is_dir()      # tự tạo thư mục giúp


def test_describe_khong_lo_mat_khau(monkeypatch):
    monkeypatch.setattr(database, "IS_SQLITE", False)
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL",
                        "postgresql://user:sieu-bi-mat@host/db")

    assert "sieu-bi-mat" not in database.describe()
    assert "host/db" in database.describe()


# ---------- chuỗi kết nối hỏng không được giết cả site ----------

@pytest.mark.parametrize("url_hong", [
    "postgresql+khongcodriver://u:p@h/db",   # sai tên driver
    "khong-phai-url-gi-ca",                  # không phải URL
    "postgres://u:p@h:notaport/db",          # cổng không phải số
])
def test_database_url_hong_thi_lui_ve_sqlite_chu_khong_no(url_hong, tmp_path):
    """create_engine chạy lúc import. Nếu để nó nổ thì cả app không import
    được — trên Vercel là 500 ở mọi trang mà không nói lý do."""
    import subprocess
    import sys

    ket_qua = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, r'%s');"
         "from app.main import app; print('ROUTES', len(app.routes))" % ROOT],
        env={**os.environ, "DATABASE_URL": url_hong, "SECRET_KEY": "x",
             "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, timeout=120,
    )

    assert "ROUTES" in ket_qua.stdout, ket_qua.stderr[-800:]
    assert "khong dung duoc DATABASE_URL" in ket_qua.stdout
