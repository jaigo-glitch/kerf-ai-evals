from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


CUSTOMERS = [
    (1, "Noah Williams", "San Jose", "2025-11-14"),
    (2, "Mia Garcia", "Santa Clara", "2025-12-02"),
    (3, "Ethan Brown", "Campbell", "2026-01-01"),
    (4, "Ava Thompson", "Los Gatos", "2025-10-21"),
    (5, "Liam Davis", "Milpitas", "2026-01-26"),
    (6, "Sophia Wilson", "San Jose", "2025-12-18"),
    (7, "Mateo Martinez", "Sunnyvale", "2026-02-01"),
    (8, "Isabella Anderson", "Cupertino", "2026-02-04"),
    (9, "Lucas Taylor", "San Jose", "2026-02-17"),
    (10, "Emma Thomas", "Morgan Hill", "2026-02-20"),
    (11, "James Moore", "Santa Clara", "2026-03-01"),
    (12, "Olivia Jackson", "Fremont", "2026-03-05"),
]

SERVICES = [
    (1, "Express Wash", "wash", 60.0, 45),
    (2, "Interior Reset", "interior", 150.0, 120),
    (3, "Full Detail", "detail", 300.0, 240),
    (4, "Paint Correction", "correction", 650.0, 480),
    (5, "Ceramic Coating", "coating", 1500.0, 720),
    (6, "Maintenance Detail", "maintenance", 200.0, 150),
]

TECHNICIANS = [
    (1, "Maya Chen", "lead detailer"),
    (2, "Luis Romero", "detailer"),
    (3, "Devon Patel", "detailer"),
]

# All names and transactions below are synthetic. Dates are ISO-8601 strings.
BOOKINGS = [
    (1, 1, 3, 1, "2026-01-05", "completed", 300.0, "google"),
    (2, 2, 2, 2, "2026-01-08", "completed", 150.0, "referral"),
    (3, 3, 1, 3, "2026-01-12", "no_show", 60.0, "instagram"),
    (4, 4, 5, 1, "2026-01-15", "completed", 1500.0, "google"),
    (5, 1, 6, 2, "2026-01-22", "completed", 200.0, "referral"),
    (6, 5, 3, 3, "2026-02-03", "completed", 300.0, "instagram"),
    (7, 6, 4, 1, "2026-02-07", "completed", 650.0, "google"),
    (8, 7, 1, 2, "2026-02-10", "completed", 60.0, "walk_in"),
    (9, 8, 2, 3, "2026-02-14", "cancelled", 150.0, "instagram"),
    (10, 2, 6, 1, "2026-02-20", "completed", 200.0, "referral"),
    (11, 9, 3, 2, "2026-02-25", "completed", 300.0, "google"),
    (12, 10, 5, 3, "2026-03-02", "completed", 1500.0, "google"),
    (13, 1, 3, 1, "2026-03-05", "completed", 300.0, "referral"),
    (14, 3, 2, 2, "2026-03-09", "completed", 150.0, "instagram"),
    (15, 11, 1, 3, "2026-03-13", "no_show", 60.0, "google"),
    (16, 6, 6, 1, "2026-03-18", "completed", 200.0, "referral"),
    (17, 12, 4, 2, "2026-03-22", "completed", 650.0, "google"),
    (18, 7, 1, 3, "2026-03-29", "completed", 60.0, "walk_in"),
    (19, 4, 6, 1, "2026-04-01", "completed", 200.0, "referral"),
    (20, 5, 3, 2, "2026-04-04", "completed", 300.0, "instagram"),
    (21, 8, 2, 3, "2026-04-08", "completed", 150.0, "instagram"),
    (22, 9, 4, 1, "2026-04-12", "completed", 650.0, "google"),
    (23, 10, 1, 2, "2026-04-18", "no_show", 60.0, "referral"),
    (24, 2, 3, 3, "2026-04-23", "completed", 300.0, "google"),
    (25, 12, 5, 1, "2026-04-27", "cancelled", 1500.0, "google"),
    (26, 1, 5, 2, "2026-05-03", "completed", 1500.0, "referral"),
    (27, 3, 3, 3, "2026-05-06", "completed", 300.0, "instagram"),
    (28, 6, 2, 1, "2026-05-10", "completed", 150.0, "google"),
    (29, 7, 6, 2, "2026-05-14", "completed", 200.0, "walk_in"),
    (30, 11, 1, 3, "2026-05-18", "completed", 60.0, "instagram"),
    (31, 4, 4, 1, "2026-05-22", "completed", 650.0, "google"),
    (32, 5, 3, 2, "2026-05-26", "cancelled", 300.0, "instagram"),
    (33, 8, 1, 3, "2026-05-30", "no_show", 60.0, "walk_in"),
    (34, 2, 5, 1, "2026-06-02", "completed", 1500.0, "google"),
    (35, 9, 4, 2, "2026-06-05", "completed", 650.0, "google"),
    (36, 10, 3, 3, "2026-06-09", "completed", 300.0, "referral"),
    (37, 12, 2, 1, "2026-06-12", "completed", 150.0, "instagram"),
    (38, 1, 6, 2, "2026-06-16", "completed", 200.0, "referral"),
    (39, 6, 3, 3, "2026-06-18", "completed", 300.0, "google"),
    (40, 7, 1, 1, "2026-06-20", "no_show", 60.0, "walk_in"),
    (41, 3, 3, 2, "2026-06-22", "completed", 300.0, "instagram"),
    (42, 11, 2, 3, "2026-06-24", "cancelled", 150.0, "google"),
    (43, 4, 5, 1, "2026-06-26", "completed", 1500.0, "referral"),
    (44, 5, 1, 2, "2026-06-28", "completed", 60.0, "walk_in"),
    (45, 8, 3, 3, "2026-06-30", "completed", 300.0, "instagram"),
]

PAYMENT_OVERRIDES = {
    11: "unpaid",
    21: "refunded",
    31: "unpaid",
    41: "unpaid",
}

LEADS = [
    (1, "Lead 001", "google", "2025-12-29", "converted", 1),
    (2, "Lead 002", "referral", "2026-01-02", "converted", 2),
    (3, "Lead 003", "google", "2026-01-07", "converted", 4),
    (4, "Lead 004", "instagram", "2026-01-28", "converted", 6),
    (5, "Lead 005", "google", "2026-01-31", "converted", 7),
    (6, "Lead 006", "referral", "2026-02-14", "converted", 10),
    (7, "Lead 007", "google", "2026-02-24", "converted", 12),
    (8, "Lead 008", "instagram", "2026-03-01", "converted", 14),
    (9, "Lead 009", "google", "2026-03-14", "converted", 17),
    (10, "Lead 010", "instagram", "2026-03-30", "converted", 20),
    (11, "Lead 011", "google", "2026-04-03", "converted", 22),
    (12, "Lead 012", "referral", "2026-04-17", "converted", 24),
    (13, "Lead 013", "referral", "2026-04-27", "converted", 26),
    (14, "Lead 014", "instagram", "2026-05-29", "converted", 37),
    (15, "Lead 015", "walk_in", "2026-06-24", "converted", 44),
    (16, "Lead 016", "google", "2026-01-16", "lost", None),
    (17, "Lead 017", "instagram", "2026-02-12", "lost", None),
    (18, "Lead 018", "walk_in", "2026-03-10", "lost", None),
    (19, "Lead 019", "google", "2026-04-20", "lost", None),
    (20, "Lead 020", "referral", "2026-05-04", "lost", None),
    (21, "Lead 021", "instagram", "2026-06-20", "open", None),
    (22, "Lead 022", "google", "2026-06-22", "open", None),
    (23, "Lead 023", "walk_in", "2026-06-25", "open", None),
    (24, "Lead 024", "instagram", "2026-06-29", "open", None),
]


def initialize_business_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                joined_at TEXT NOT NULL
            );
            CREATE TABLE services (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                list_price REAL NOT NULL,
                duration_minutes INTEGER NOT NULL
            );
            CREATE TABLE technicians (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE bookings (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                service_id INTEGER NOT NULL REFERENCES services(id),
                technician_id INTEGER NOT NULL REFERENCES technicians(id),
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('completed','no_show','cancelled')),
                amount REAL NOT NULL,
                source TEXT NOT NULL
            );
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY,
                booking_id INTEGER NOT NULL UNIQUE REFERENCES bookings(id),
                amount REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('paid','unpaid','refunded')),
                paid_at TEXT
            );
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY,
                prospect_name TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('converted','lost','open')),
                converted_booking_id INTEGER REFERENCES bookings(id)
            );
            CREATE INDEX idx_bookings_date ON bookings(scheduled_at);
            CREATE INDEX idx_bookings_status ON bookings(status);
            CREATE INDEX idx_payments_status ON payments(status);
            """
        )
        connection.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS)
        connection.executemany("INSERT INTO services VALUES (?, ?, ?, ?, ?)", SERVICES)
        connection.executemany("INSERT INTO technicians VALUES (?, ?, ?)", TECHNICIANS)
        connection.executemany("INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?, ?)", BOOKINGS)
        payment_rows = []
        for booking in BOOKINGS:
            booking_id, _, _, _, scheduled_at, booking_status, amount, _ = booking
            status = PAYMENT_OVERRIDES.get(booking_id)
            if status is None:
                status = "paid" if booking_status == "completed" else "unpaid"
            paid_at = scheduled_at if status in {"paid", "refunded"} else None
            payment_rows.append((booking_id, booking_id, amount, status, paid_at))
        connection.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?)", payment_rows)
        connection.executemany("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?)", LEADS)
        connection.commit()
    finally:
        connection.close()


def initialize_history_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                reasoning_effort TEXT NOT NULL DEFAULT 'low',
                status TEXT NOT NULL,
                case_count INTEGER NOT NULL DEFAULT 0,
                passed_count INTEGER NOT NULL DEFAULT 0,
                average_score REAL NOT NULL DEFAULT 0,
                average_latency_ms REAL NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                cached_input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                reasoning_tokens INTEGER NOT NULL DEFAULT 0,
                estimated_cost_usd REAL NOT NULL DEFAULT 0,
                error TEXT
            );
            CREATE TABLE IF NOT EXISTS case_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                case_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_case_results_run ON case_results(run_id);
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                tester_alias TEXT NOT NULL,
                role TEXT NOT NULL,
                rating INTEGER NOT NULL,
                feedback TEXT NOT NULL,
                consent_to_quote INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
            );
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                released_at TEXT NOT NULL,
                notes TEXT NOT NULL
            );
            INSERT OR IGNORE INTO releases(version, released_at, notes)
            VALUES ('0.1.0', '2026-08-27', 'Initial local MVP: 20 eval cases, safe SQL, scoring, history, comparison, and reports.');
            INSERT OR IGNORE INTO releases(version, released_at, notes)
            VALUES ('0.2.0', '2026-08-29', 'Repeatable live two-profile evaluation workflow with reasoning, cached-token, response, latency, and cost evidence.');
            """
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(runs)").fetchall()
        }
        migrations = {
            "reasoning_effort": "TEXT NOT NULL DEFAULT 'low'",
            "cached_input_tokens": "INTEGER NOT NULL DEFAULT 0",
            "reasoning_tokens": "INTEGER NOT NULL DEFAULT 0",
        }
        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE runs ADD COLUMN {column} {definition}")
        connection.commit()
    finally:
        connection.close()


class HistoryStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def create_run(
        self,
        provider: str,
        model: str,
        case_count: int,
        reasoning_effort: str,
    ) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs(
                    created_at, provider, model, reasoning_effort, status, case_count
                )
                VALUES (?, ?, ?, ?, 'running', ?)
                """,
                (utc_now(), provider, model, reasoning_effort, case_count),
            )
            return int(cursor.lastrowid)

    def complete_run(self, run_id: int, results: list[dict[str, Any]]) -> None:
        case_count = len(results)
        passed_count = sum(1 for result in results if result["passed"])
        average_score = sum(result["score"] for result in results) / case_count if case_count else 0
        average_latency = (
            sum(result["latency_ms"] for result in results) / case_count if case_count else 0
        )
        input_tokens = sum(result["input_tokens"] for result in results)
        cached_input_tokens = sum(result["cached_input_tokens"] for result in results)
        output_tokens = sum(result["output_tokens"] for result in results)
        reasoning_tokens = sum(result["reasoning_tokens"] for result in results)
        cost = sum(result["estimated_cost_usd"] for result in results)
        with self.connection() as connection:
            connection.executemany(
                "INSERT INTO case_results(run_id, case_id, payload_json) VALUES (?, ?, ?)",
                [
                    (run_id, result["case_id"], json.dumps(result, separators=(",", ":")))
                    for result in results
                ],
            )
            connection.execute(
                """
                UPDATE runs
                SET completed_at=?, status='completed', passed_count=?, average_score=?,
                    average_latency_ms=?, input_tokens=?, cached_input_tokens=?,
                    output_tokens=?, reasoning_tokens=?, estimated_cost_usd=?
                WHERE id=?
                """,
                (
                    utc_now(),
                    passed_count,
                    round(average_score, 2),
                    round(average_latency, 2),
                    input_tokens,
                    cached_input_tokens,
                    output_tokens,
                    reasoning_tokens,
                    round(cost, 8),
                    run_id,
                ),
            )

    def fail_run(self, run_id: int, error: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE runs SET completed_at=?, status='failed', error=? WHERE id=?",
                (utc_now(), error[:2000], run_id),
            )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.connection() as connection:
            run = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                return None
            result_rows = connection.execute(
                "SELECT payload_json FROM case_results WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        payload = dict(run)
        payload["results"] = [json.loads(row["payload_json"]) for row in result_rows]
        return payload

    def add_feedback(self, payload: dict[str, Any]) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO feedback(created_at, tester_alias, role, rating, feedback, consent_to_quote)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now(), payload["tester_alias"], payload["role"], payload["rating"],
                    payload["feedback"], int(payload["consent_to_quote"]),
                ),
            )
            return int(cursor.lastrowid)

    def add_issue(self, payload: dict[str, Any]) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO issues(created_at, title, description, severity)
                VALUES (?, ?, ?, ?)
                """,
                (utc_now(), payload["title"], payload["description"], payload["severity"]),
            )
            return int(cursor.lastrowid)

    def tracker_metrics(self) -> dict[str, Any]:
        with self.connection() as connection:
            run_metrics = connection.execute(
                """
                SELECT COUNT(*) AS runs_completed,
                       COUNT(DISTINCT CASE WHEN provider != 'fixture' THEN model END) AS model_versions_compared,
                       COALESCE(SUM(case_count - passed_count), 0) AS incorrect_outputs_detected,
                       COALESCE(AVG(CASE WHEN provider != 'fixture' THEN average_latency_ms END), 0) AS average_latency_ms,
                       COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd
                FROM runs WHERE status='completed'
                """
            ).fetchone()
            beta_users = connection.execute(
                "SELECT COUNT(DISTINCT tester_alias) AS count FROM feedback"
            ).fetchone()["count"]
            releases = connection.execute("SELECT COUNT(*) AS count FROM releases").fetchone()["count"]
            issues = connection.execute(
                "SELECT COUNT(*) AS total, SUM(status='open') AS open FROM issues"
            ).fetchone()
        metrics = dict(run_metrics)
        metrics.update(
            {
                "evaluation_cases_created": 20,
                "beta_users": beta_users,
                "product_releases": releases,
                "issues_total": issues["total"],
                "issues_open": issues["open"] or 0,
            }
        )
        return metrics

    def list_releases(self) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT version, released_at, notes FROM releases ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]
