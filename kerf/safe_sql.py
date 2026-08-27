from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class UnsafeQueryError(ValueError):
    """Raised when generated SQL violates the read-only policy."""


FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|"
    r"vacuum|reindex|analyze|load_extension|savepoint|release|rollback|commit|begin)\b",
    re.IGNORECASE,
)

ALLOWED_TABLES = {"customers", "services", "technicians", "bookings", "payments", "leads"}

DENIED_ACTION_NAMES = [
    "SQLITE_INSERT",
    "SQLITE_UPDATE",
    "SQLITE_DELETE",
    "SQLITE_ALTER_TABLE",
    "SQLITE_ATTACH",
    "SQLITE_DETACH",
    "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_TEMP_INDEX",
    "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_TEMP_VIEW",
    "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_VIEW",
    "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE",
    "SQLITE_DROP_TEMP_INDEX",
    "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_TEMP_VIEW",
    "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_VIEW",
    "SQLITE_PRAGMA",
    "SQLITE_REINDEX",
    "SQLITE_TRANSACTION",
]
DENIED_ACTIONS = {getattr(sqlite3, name) for name in DENIED_ACTION_NAMES if hasattr(sqlite3, name)}


def validate_read_only_sql(sql: str) -> str:
    if not isinstance(sql, str):
        raise UnsafeQueryError("SQL must be a string")
    normalized = sql.strip()
    if not normalized:
        raise UnsafeQueryError("SQL is empty")
    if len(normalized) > 4000:
        raise UnsafeQueryError("SQL exceeds the 4,000-character limit")
    if "\x00" in normalized:
        raise UnsafeQueryError("SQL contains a null byte")
    if any(marker in normalized for marker in ("--", "/*", "*/")):
        raise UnsafeQueryError("SQL comments are not allowed")
    normalized = normalized[:-1].strip() if normalized.endswith(";") else normalized
    if ";" in normalized:
        raise UnsafeQueryError("Only one SQL statement is allowed")
    if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
        raise UnsafeQueryError("Only SELECT statements and read-only CTEs are allowed")
    forbidden = FORBIDDEN_SQL.search(normalized)
    if forbidden:
        raise UnsafeQueryError(f"Forbidden SQL keyword: {forbidden.group(1).upper()}")
    return normalized


def _authorizer(action: int, arg1: str | None, _arg2: str | None, _db: str | None, _src: str | None) -> int:
    if action in DENIED_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ and arg1 and arg1 not in ALLOWED_TABLES:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


class SafeSQLExecutor:
    def __init__(self, database_path: Path, max_rows: int = 100, max_steps: int = 250_000):
        self.database_path = database_path.resolve()
        self.max_rows = max_rows
        self.max_steps = max_steps

    def execute(self, sql: str) -> list[dict[str, Any]]:
        query = validate_read_only_sql(sql)
        uri = f"file:{self.database_path.as_posix()}?mode=ro&immutable=1"
        connection = sqlite3.connect(uri, uri=True, timeout=2.0)
        connection.row_factory = sqlite3.Row
        steps = 0

        def progress_handler() -> int:
            nonlocal steps
            steps += 1000
            return 1 if steps > self.max_steps else 0

        try:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("PRAGMA trusted_schema = OFF")
            connection.set_authorizer(_authorizer)
            connection.set_progress_handler(progress_handler, 1000)
            wrapped = f"SELECT * FROM ({query}) AS kerf_result LIMIT {self.max_rows + 1}"
            rows = connection.execute(wrapped).fetchall()
            if len(rows) > self.max_rows:
                raise UnsafeQueryError(f"Query returned more than {self.max_rows} rows")
            return [dict(row) for row in rows]
        except sqlite3.DatabaseError as exc:
            message = str(exc)
            if "not authorized" in message.lower():
                raise UnsafeQueryError("Query attempted an unauthorized database operation") from exc
            if "interrupted" in message.lower():
                raise UnsafeQueryError("Query exceeded the execution step limit") from exc
            raise UnsafeQueryError(f"Query could not be executed: {message}") from exc
        finally:
            connection.set_authorizer(None)
            connection.close()


BUSINESS_SCHEMA = """
Synthetic company: Northstar Auto Detail. Currency: USD. Dates: YYYY-MM-DD.

customers(id, name, city, joined_at)
services(id, name, category, list_price, duration_minutes)
technicians(id, name, role)
bookings(id, customer_id, service_id, technician_id, scheduled_at, status, amount, source)
payments(id, booking_id, amount, status, paid_at)
leads(id, prospect_name, source, created_at, status, converted_booking_id)

Rules:
- Recognized revenue is payments.amount where payments.status = 'paid'.
- A completed booking can still be unpaid or refunded.
- Date functions must use SQLite syntax.
- Return exactly one read-only SELECT statement or WITH...SELECT CTE.
""".strip()

