"""Tiny hand-rolled migrations.

`Base.metadata.create_all` creates missing *tables* but never adds columns to a
table that already exists — so a `we.db` from before the redesign is missing
`image` and `rating` on food_places. This adds them in place, on SQLite and
Postgres alike, and is safe to run on every boot.
"""

from sqlalchemy import inspect, text

from .database import engine

# table -> column -> DDL type + default
NEW_COLUMNS = {
    "food_places": {
        "image": "VARCHAR DEFAULT ''",
        "rating": "INTEGER DEFAULT 0",
    },
    "plans": {
        "priority": "VARCHAR DEFAULT 'normal'",
        "deadline": "VARCHAR DEFAULT ''",
        "done": "INTEGER DEFAULT 0",
    },
}


def run():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table, columns in NEW_COLUMNS.items():
        if table not in existing_tables:
            continue  # create_all just made it with the full schema

        present = {c["name"] for c in inspector.get_columns(table)}

        with engine.begin() as conn:
            for name, ddl in columns.items():
                if name in present:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
