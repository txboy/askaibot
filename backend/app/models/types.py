"""跨方言字符串类型：解决 Oracle 将空串视为 NULL 的问题。

Oracle 会把 ``''`` 当作 NULL，因此不能写入 NOT NULL 的 VARCHAR2/CLOB 列，
否则报 ORA-01400。这两个类型在写入时把空串统一转为 NULL，读取时把 NULL
归一化为 ``''``，从而在 SQLite / MySQL / PostgreSQL / MSSQL / Oracle 间保持
一致的"空串"语义，应用层无需关心数据库差异。
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator


class OrEmptyStr(TypeDecorator):
    """VARCHAR 变体：以 NULL 存空串，读取时返回 ''。"""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return None
        return value

    def process_result_value(self, value, dialect):
        return value if value is not None else ""


class OrEmptyText(TypeDecorator):
    """CLOB 变体：以 NULL 存空串，读取时返回 ''。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or value == "":
            return None
        return value

    def process_result_value(self, value, dialect):
        return value if value is not None else ""
