from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine, create_engine, text


def create_readonly_engine(readonly_url: str) -> Engine:
    return create_engine(
        readonly_url,
        isolation_level="SERIALIZABLE",
        execution_options={"read_only": True},
    )


@contextmanager
def read_only_session(engine: Engine) -> Generator[object, None, None]:
    with engine.connect() as conn:
        conn.execute(text("BEGIN READ ONLY"))
        try:
            yield conn
        finally:
            conn.execute(text("ROLLBACK"))
