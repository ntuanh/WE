"""Cấu hình chung cho test.

Điểm quan trọng nhất: đặt DATABASE_URL trỏ vào SQLite trong RAM **trước khi**
import app, để test không bao giờ chạm vào we.db thật. Mỗi test được một DB
trắng tinh, chạy xong là biến mất.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Phải đặt trước mọi `import app.*` — app/database.py đọc biến này lúc import.
os.environ["DATABASE_URL"] = "sqlite://"          # sqlite trong bộ nhớ
os.environ["SECRET_KEY"] = "khoa-rieng-cho-test"
os.environ["WE_USERS"] = "{}"     # khong dung tai khoan that cua may

from sqlalchemy import create_engine                       # noqa: E402
from sqlalchemy.orm import sessionmaker                     # noqa: E402
from sqlalchemy.pool import StaticPool                      # noqa: E402

from app import auth                                        # noqa: E402
from app.database import Base, get_db                       # noqa: E402
from app.main import app                                    # noqa: E402

# Mật khẩu thật của hai tài khoản không nằm trong repo, nên test tự dựng tài
# khoản riêng bằng chính hash_password() — vẫn đi qua đúng đường xác thực.
GOOD_PASSWORD = "mat-khau-dung-cua-test"
ADMIN = "test_admin"
MEMBER = "test_member"


@pytest.fixture(autouse=True)
def fake_users():
    """Thay USERS bằng hai tài khoản test, trả lại nguyên trạng sau mỗi test."""
    original, had_none = auth.USERS, auth.NO_ACCOUNTS
    auth.USERS = {
        ADMIN: {"hash": auth.hash_password(GOOD_PASSWORD), "role": "admin"},
        MEMBER: {"hash": auth.hash_password(GOOD_PASSWORD), "role": "user"},
    }
    auth.NO_ACCOUNTS = False
    auth.reset_failures()

    yield auth.USERS

    auth.USERS, auth.NO_ACCOUNTS = original, had_none
    auth.reset_failures()


@pytest.fixture
def db():
    """Một database SQLite trong RAM, riêng cho mỗi test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,          # giữ đúng một connection, nếu không DB bay mất
    )
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    """TestClient dùng chung database với fixture `db` ở trên."""
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def logged_in(client):
    """Client đã đăng nhập sẵn bằng tài khoản thường."""
    client.post("/login", data={"username": MEMBER, "password": GOOD_PASSWORD},
                follow_redirects=False)
    return client
