from pathlib import Path

import pytest

from kerf.db import initialize_business_database
from kerf.safe_sql import SafeSQLExecutor, UnsafeQueryError, validate_read_only_sql


@pytest.fixture()
def executor(tmp_path: Path) -> SafeSQLExecutor:
    database = tmp_path / "business.sqlite3"
    initialize_business_database(database)
    return SafeSQLExecutor(database)


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM bookings",
        "PRAGMA table_info(bookings)",
        "SELECT 1; SELECT 2",
        "SELECT * FROM bookings -- bypass",
        "WITH bad AS (UPDATE bookings SET amount=0 RETURNING *) SELECT * FROM bad",
    ],
)
def test_rejects_unsafe_sql(query: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate_read_only_sql(query)


def test_executes_read_only_select(executor: SafeSQLExecutor) -> None:
    rows = executor.execute("SELECT COUNT(*) AS count FROM bookings")
    assert rows == [{"count": 45}]


def test_executes_read_only_cte(executor: SafeSQLExecutor) -> None:
    rows = executor.execute(
        "WITH paid AS (SELECT amount FROM payments WHERE status='paid') "
        "SELECT ROUND(SUM(amount), 2) AS revenue FROM paid"
    )
    assert rows == [{"revenue": 14840.0}]


def test_authorizer_blocks_system_catalog(executor: SafeSQLExecutor) -> None:
    with pytest.raises(UnsafeQueryError):
        executor.execute("SELECT name FROM sqlite_master")


def test_row_limit_is_enforced(executor: SafeSQLExecutor) -> None:
    limited = SafeSQLExecutor(executor.database_path, max_rows=5)
    with pytest.raises(UnsafeQueryError, match="more than 5"):
        limited.execute("SELECT * FROM bookings")

