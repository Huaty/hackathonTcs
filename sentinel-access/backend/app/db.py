import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    entity TEXT NOT NULL,
    role TEXT NOT NULL,
    source TEXT NOT NULL,
    region TEXT NOT NULL,
    service TEXT NOT NULL,
    score INTEGER NOT NULL,
    time TEXT NOT NULL,
    description TEXT NOT NULL,
    signals TEXT NOT NULL,
    baseline TEXT NOT NULL,
    recommended TEXT NOT NULL,
    status TEXT
);

CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    time TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    source TEXT NOT NULL,
    system TEXT NOT NULL,
    status TEXT NOT NULL,
    tone TEXT NOT NULL
);

CREATE TABLE identities (
    identity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    initials TEXT NOT NULL,
    role TEXT NOT NULL,
    activity TEXT NOT NULL,
    score INTEGER NOT NULL,
    color TEXT NOT NULL,
    description TEXT NOT NULL,
    identity_type TEXT NOT NULL DEFAULT 'human',
    status TEXT NOT NULL DEFAULT 'active',
    home_timezone TEXT NOT NULL DEFAULT 'UTC',
    principal_name TEXT,
    last_seen_at TEXT
);

CREATE UNIQUE INDEX identities_principal_name_idx
ON identities(principal_name) WHERE principal_name IS NOT NULL;

CREATE TABLE security_events (
    event_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    source_ip TEXT,
    location TEXT,
    cloud_service TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    outcome TEXT NOT NULL,
    session_id TEXT,
    correlation_id TEXT,
    raw_payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(identity_id) REFERENCES identities(identity_id)
);

CREATE INDEX security_events_identity_time_idx
ON security_events(identity_id, timestamp_utc);

CREATE TABLE identity_baselines (
    baseline_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL,
    window_start_utc TEXT NOT NULL,
    window_end_utc TEXT NOT NULL,
    usual_hours TEXT NOT NULL,
    usual_source_ips TEXT NOT NULL,
    usual_locations TEXT NOT NULL,
    usual_services TEXT NOT NULL,
    usual_actions TEXT NOT NULL,
    frequency_p95 REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    active_day_count INTEGER NOT NULL,
    confidence TEXT NOT NULL,
    unknown_fields TEXT NOT NULL,
    baseline_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(identity_id) REFERENCES identities(identity_id)
);

CREATE INDEX identity_baselines_identity_created_idx
ON identity_baselines(identity_id, created_at DESC);

CREATE TABLE cloud_sources (
    name TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    eventsToday INTEGER NOT NULL,
    health TEXT NOT NULL,
    icon TEXT NOT NULL,
    color TEXT NOT NULL,
    dataFreshnessMin INTEGER NOT NULL
);

CREATE TABLE policies (
    rule_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    category TEXT NOT NULL,
    condition_key TEXT NOT NULL,
    points INTEGER NOT NULL,
    severity_floor TEXT,
    policy_version TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE policy_evaluations (
    policy_evaluation_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    baseline_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    policy_snapshot TEXT NOT NULL,
    policy_snapshot_hash TEXT NOT NULL,
    rule_results TEXT NOT NULL,
    policy_score INTEGER NOT NULL,
    severity_floor TEXT,
    severity_floor_minimum INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(event_id, baseline_id, policy_snapshot_hash),
    FOREIGN KEY(event_id) REFERENCES security_events(event_id),
    FOREIGN KEY(baseline_id) REFERENCES identity_baselines(baseline_id)
);

CREATE TABLE ai_context_decisions (
    ai_decision_id TEXT PRIMARY KEY,
    cache_key TEXT NOT NULL,
    refresh_sequence INTEGER NOT NULL DEFAULT 0,
    event_id TEXT NOT NULL,
    policy_evaluation_id TEXT NOT NULL,
    adjustment_requested INTEGER,
    adjustment_applied INTEGER NOT NULL,
    confidence REAL,
    status TEXT NOT NULL,
    risk_factors TEXT NOT NULL,
    mitigating_factors TEXT NOT NULL,
    evidence_event_ids TEXT NOT NULL,
    explanation TEXT NOT NULL,
    validation_errors TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(cache_key, refresh_sequence),
    FOREIGN KEY(event_id) REFERENCES security_events(event_id),
    FOREIGN KEY(policy_evaluation_id) REFERENCES policy_evaluations(policy_evaluation_id)
);

CREATE TABLE risk_assessments (
    assessment_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    policy_evaluation_id TEXT NOT NULL,
    ai_decision_id TEXT NOT NULL,
    policy_score INTEGER NOT NULL,
    ai_adjustment_applied INTEGER NOT NULL,
    pre_floor_score INTEGER NOT NULL,
    severity_floor TEXT,
    severity_floor_minimum INTEGER NOT NULL,
    final_risk_score INTEGER NOT NULL,
    severity TEXT NOT NULL,
    scoring_version TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(event_id, policy_evaluation_id, ai_decision_id, scoring_version),
    FOREIGN KEY(event_id) REFERENCES security_events(event_id),
    FOREIGN KEY(policy_evaluation_id) REFERENCES policy_evaluations(policy_evaluation_id),
    FOREIGN KEY(ai_decision_id) REFERENCES ai_context_decisions(ai_decision_id)
);

CREATE TABLE reports (
    title TEXT PRIMARY KEY,
    detail TEXT NOT NULL,
    period TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE access_trend (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    events INTEGER NOT NULL,
    anomalies INTEGER NOT NULL
);

CREATE TABLE service_risk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    risk INTEGER NOT NULL,
    events INTEGER NOT NULL
);

CREATE TABLE finding_explanations (
    finding_id TEXT PRIMARY KEY,
    explanation TEXT NOT NULL
);

CREATE TABLE model_rationale (
    top_finding_id TEXT NOT NULL,
    explanation TEXT NOT NULL,
    signals TEXT NOT NULL
);

CREATE TABLE service_risk_summary (
    highest_risk_service TEXT NOT NULL,
    sensitive_assets INTEGER NOT NULL,
    coverage TEXT NOT NULL
);

CREATE TABLE configuration (
    notifications_enabled INTEGER NOT NULL,
    plain_language_explanations INTEGER NOT NULL
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Return the process-wide in-memory SQLite connection, creating and
    schema-initializing it on first access.

    The connection is opened with check_same_thread=False because FastAPI
    dispatches synchronous route handlers to a worker threadpool by
    default, so even sequential-looking single-user requests can reach
    this connection from different OS threads. Sharing one sqlite3
    connection across threads is only safe when every access is
    serialized — see execute()/query()/query_one() below, which are the
    only sanctioned way to touch this connection. No other module should
    call conn.execute(...) or open a cursor directly.
    """
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(":memory:", check_same_thread=False)
        init_schema(_conn)
    return _conn


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Run an INSERT/UPDATE/DELETE (or DDL) statement, serialized via the
    module lock, and commit. Returns the cursor (e.g. for lastrowid)."""
    conn = get_connection()
    with _lock:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor


def executemany(sql: str, seq_of_params: list[tuple]) -> None:
    """Run the same INSERT/UPDATE statement for many rows in one
    lock-serialized transaction."""
    conn = get_connection()
    with _lock:
        conn.executemany(sql, seq_of_params)
        conn.commit()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Yield the shared connection inside one serialized atomic transaction."""
    conn = get_connection()
    with _lock:
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a SELECT, serialized via the module lock, returning all rows."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    with _lock:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Run a SELECT expected to return at most one row."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    with _lock:
        return conn.execute(sql, params).fetchone()


def reset_for_tests() -> None:
    """Drop the process-wide connection so the next get_connection() call
    creates a fresh, unseeded in-memory database. Test-only helper."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None
