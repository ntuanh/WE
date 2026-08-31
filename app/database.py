"""Kết nối database.

Thứ tự ưu tiên:
  1. DATABASE_URL  — Postgres thật (Neon/Supabase/Vercel Postgres). Dùng cái này
     khi deploy: dữ liệu sống qua mọi lần deploy lại.
  2. SQLITE_PATH   — trỏ file SQLite vào ổ đĩa gắn ngoài (Railway/Fly volume).
  3. we.db cạnh mã nguồn — chạy ở máy.
  4. /tmp/we.db    — chỗ duy nhất ghi được trên serverless. TẠM THỜI: mất sạch
     mỗi lần cold start. Có cảnh báo in ra log để khỏi tưởng là bug bí ẩn.
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .log import log

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# True khi dữ liệu nằm ở chỗ sẽ bị xoá — main.py đọc để cảnh báo lúc khởi động.
IS_EPHEMERAL = False

# True khi DATABASE_URL có mà dùng không được, phải lùi về SQLite.
BAD_DATABASE_URL = False


def _database_url() -> str:
    global IS_EPHEMERAL

    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        # Neon/Supabase/Heroku phát ra postgres://, SQLAlchemy đòi postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    path = os.environ.get("SQLITE_PATH", "").strip()
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        return "sqlite:///" + os.path.abspath(path)

    # Thử ghi thật chứ không đoán theo biến môi trường của nhà cung cấp:
    # $VERCEL có thể mang tên gì cũng được, còn quyền ghi thì không nói dối.
    if os.access(BASE_DIR, os.W_OK):
        return "sqlite:///" + os.path.join(BASE_DIR, "we.db")

    IS_EPHEMERAL = True
    return "sqlite:////tmp/we.db"


def _make_engine(url: str):
    """Dựng engine cho một chuỗi kết nối."""
    if url.startswith("sqlite"):
        engine = create_engine(
            url, connect_args={"check_same_thread": False, "timeout": 15}
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):
            """WAL + synchronous=NORMAL: ghi đồng thời không khoá nhau, và một
            cú tắt máy giữa chừng không làm hỏng file (mất DB kiểu khác)."""
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

        return engine

    # serverless: kết nối chết giữa hai lần gọi, nên kiểm tra trước khi tái dùng
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


SQLALCHEMY_DATABASE_URL = _database_url()

try:
    engine = _make_engine(SQLALCHEMY_DATABASE_URL)
except Exception as exc:
    # Gõ nhầm DATABASE_URL (hoặc thiếu driver) mà để nổ ở đây là cả app không
    # import được — trên Vercel thành 500 ở mọi trang, không nói lý do. Thà lùi
    # về SQLite tạm: site vẫn mở được và log nói rõ chuyện gì đã xảy ra.
    log(f"[database] khong dung duoc DATABASE_URL ({exc!r}) - tam lui ve SQLite")

    SQLALCHEMY_DATABASE_URL = ("sqlite:///" + os.path.join(BASE_DIR, "we.db")
                               if os.access(BASE_DIR, os.W_OK)
                               else "sqlite:////tmp/we.db")
    IS_EPHEMERAL = True
    BAD_DATABASE_URL = True
    engine = _make_engine(SQLALCHEMY_DATABASE_URL)

IS_SQLITE = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def describe() -> str:
    """Mô tả ngắn để in ra log — giấu mật khẩu trong chuỗi kết nối."""
    if IS_SQLITE:
        return f"sqlite -> {SQLALCHEMY_DATABASE_URL[10:]}"

    tail = SQLALCHEMY_DATABASE_URL.split("@")[-1]
    return f"postgres -> {tail}"


def get_db():
    """Dependency của FastAPI — phát một session và luôn đóng lại.

    Quan trọng hơn vẻ ngoài của nó khi chạy serverless: session quên đóng sẽ
    giữ một kết nối Postgres đến tận lúc lambda chết.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
