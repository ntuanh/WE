"""Tự động vá schema — chạy mỗi lần khởi động, an toàn khi chạy lại nhiều lần.

Vì sao cần: `Base.metadata.create_all` chỉ tạo *bảng* còn thiếu, nó **không bao
giờ** thêm cột vào bảng đã tồn tại. Nên trước đây mỗi lần thêm một trường mới
vào models.py là trang đó lỗi "no such column", và cách chữa quen tay là xoá
we.db — mất sạch dữ liệu. Đó chính là chuyện "database tự reset".

Giờ thì danh sách cột không còn viết tay nữa: đọc thẳng từ models.py, so với
schema thật trong DB, thiếu cột nào thì ALTER TABLE thêm cột đó. Thêm trường
mới vào model → khởi động lại → cột tự xuất hiện, dữ liệu cũ giữ nguyên.
"""

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateIndex

from .database import Base, engine
from .log import log
from . import models  # noqa: F401 - nap model de Base.metadata co du bang

# Kiểu cột mà SQLite không cho ALTER TABLE ADD COLUMN kèm default động.
# Ta chỉ thêm default là hằng số nên không vướng, nhưng chặn trước cho chắc.
_UNSAFE_DEFAULTS = ("CURRENT_TIMESTAMP", "now()")


def _sql_default(column):
    """Giá trị DEFAULT viết vào DDL, hoặc None nếu cột không có default tĩnh."""
    default = column.default

    if default is None or not getattr(default, "is_scalar", False):
        return None

    value = default.arg

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if value in _UNSAFE_DEFAULTS:
            return None
        return "'" + value.replace("'", "''") + "'"

    return None


def _add_column(conn, table, column):
    """ALTER TABLE ... ADD COLUMN, dịch kiểu Python sang DDL của DB đang dùng."""
    ddl_type = column.type.compile(dialect=engine.dialect)
    sql = f'ALTER TABLE "{table}" ADD COLUMN "{column.name}" {ddl_type}'

    default = _sql_default(column)
    if default is not None:
        sql += f" DEFAULT {default}"

    # Cột thêm sau luôn để NULL được: hàng cũ chưa có giá trị cho nó.
    conn.execute(text(sql))

    # Điền sẵn cho các hàng cũ để template khỏi phải xử lý None khắp nơi.
    if default is not None:
        conn.execute(
            text(f'UPDATE "{table}" SET "{column.name}" = {default} '
                 f'WHERE "{column.name}" IS NULL')
        )


def run() -> list:
    """Đồng bộ schema thật với models.py. Trả về danh sách việc đã làm."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    applied = []

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue  # create_all vừa tạo với đủ cột rồi

        present = {c["name"] for c in inspector.get_columns(table_name)}
        missing = [c for c in table.columns
                   if c.name not in present and not c.primary_key]

        if not missing:
            continue

        with engine.begin() as conn:
            for column in missing:
                _add_column(conn, table_name, column)
                applied.append(f"{table_name}.{column.name}")

    # Index khai báo trong model (index=True) cũng có thể thiếu ở DB cũ.
    inspector = inspect(engine)
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue

        have = {ix["name"] for ix in inspector.get_indexes(table_name)}

        for index in table.indexes:
            if index.name in have:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(CreateIndex(index, if_not_exists=True))
                applied.append(f"index {index.name}")
            except Exception as exc:  # index thiếu không làm chết app
                log(f"[migrations] bo qua index {index.name}: {exc!r}")

    return applied
