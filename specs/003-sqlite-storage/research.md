# Phase 0 Research: SQLite In-Memory Storage & Additive Dataset Uploads

## 1. Is an in-memory `sqlite3` connection compatible with constitution Principle III?

**Decision**: Yes, under the reading already staked out in `plan.md`'s
Complexity Tracking: Python's stdlib `sqlite3` connected to `:memory:` is
treated as an internal data-structure choice, not "infrastructure." It
requires no separate process, no file on disk, no network port, no driver
installation beyond what ships with Python, no ORM, no migrations, and no
auth. It is created once per server run and discarded on process exit,
matching the existing "in-memory state seeded at startup" language in the
constitution almost exactly — the only literal deviation is the word "SQL."

**Rationale**: The constitution's stated concern (Principle III rationale)
is "this is a hackathon/demo project; added infrastructure increases setup
cost and failure surface without a corresponding requirement." An in-memory
`sqlite3` connection adds zero setup cost (stdlib, no install step) and zero
new failure surface (no external process to be unreachable, no credentials,
no network). The user explicitly requested this technology for this
feature, so the practical question is "does this violate the *purpose*
behind Principle III," and the answer is no.

**Alternatives considered**:
- *Keep plain Python lists, skip SQLite entirely*: Rejected — the user
  specifically asked for SQLite; append/count semantics are achievable
  either way, so this isn't a case where SQLite is technically necessary,
  but it's what was asked for and it's compatible with the constitution's
  underlying rationale (see Decision above).
- *SQLite to a file on disk*: Rejected — would add a persistence guarantee
  and a cleanup/reset concern (stale `.db` file across runs) that neither
  the spec nor the constitution asks for; `:memory:` matches today's
  "resets on restart" behavior exactly (spec Edge Cases).
- *An ORM (SQLAlchemy, etc.)*: Rejected — adds a dependency and an
  abstraction layer the current scale (a handful of tables, <10k rows)
  doesn't need; raw `sqlite3` + small mapping helpers in `db.py` is
  sufficient and keeps Principle III's "no ORM" spirit intact.
- **Recommendation to user**: if this project expects to keep SQLite
  long-term (beyond this one feature), consider a small constitution
  amendment to Principle III's wording so future contributors don't have to
  re-derive this same justification. Out of scope for this plan to decide.

## 2. How should the SQLite schema map to the existing Pydantic entities?

**Decision**: One table per entity currently held by `Store`, with columns
matching each Pydantic model's fields 1:1 (JSON-encoded as `TEXT` for
list-valued fields like `Finding.signals`, since SQLite has no native array
type). `Store`'s public methods read rows and construct Pydantic model
instances (or accept a Pydantic model and write out its fields) so no router
or schema code needs to know SQL exists. `activity_log` gets an
auto-incrementing `id` primary key (not exposed in the API) purely so rows
have stable identity for insertion order and counting; the existing
`ActivityEvent` schema itself is unchanged.

**Rationale**: Matches Principle II (preserve data shapes) — the API-facing
shape never changes, only the storage representation. Keeping a 1:1 table
mapping (rather than a fully normalized relational schema) matches the
existing flat, denormalized JSON seed structure and avoids introducing
relationships/foreign keys the feature doesn't need.

**Alternatives considered**:
- *Fully normalized schema (e.g. separate `signals` table for `Finding`)*:
  Rejected — no requirement needs relational integrity between entities;
  adds complexity (joins) for zero behavior gain given the JSON-blob
  seed source.
- *Single generic key-value/JSON-blob table for everything*: Rejected —
  loses the ability to do `SELECT COUNT(*) FROM activity_log`
  efficiently/idiomatically for the live `activitiesChecked` requirement
  (FR-009), which is the main reason SQLite was chosen for this feature.

## 3. How does dataset upload move from replace to append?

**Decision**: `Store.replace_activity_log(events, source)` is replaced by
`Store.append_activity_events(events) -> int` (returns count inserted) plus
a separate accessor for the log's current `source` label. Rows are
`INSERT`ed (not preceded by a `DELETE`); the whole insert for one upload
happens inside a single SQLite transaction, so a mid-parse failure (already
handled upstream in `datasets.py` via validation before any `Store` call)
cannot partially append. `datasets.py`'s existing validation flow (parse →
validate → build `ActivityEvent` list → error out before touching `Store`
if zero accepted) already guarantees this ordering; only the final
`Store` call changes from replace to append.

**Rationale**: Directly satisfies spec FR-005/FR-007/FR-008. No change to
the parsing/normalization logic in `datasets.py` (`_coerce_record`,
`FIELD_ALIASES`, etc.) — only the final persistence call changes.

**Alternatives considered**:
- *Upsert/de-dup on (time, actor, action)*: Rejected per spec Assumptions —
  de-duplication is explicitly out of scope for this feature.
- *Track "source" per upload batch*: Considered for a future "which upload
  did this row come from" feature; not required by any FR here, so not
  built. The existing single `activity_source: Literal["seed","imported"]`
  field is kept, updated to `"imported"` once at least one upload has
  occurred (first append), consistent with today's semantics for that
  field (it already only has these two values and existing tests/consumers
  don't rely on multiple distinct "imported" sources).

## 4. How does `activitiesChecked` become live?

**Decision**: `Store.compute_summary_metrics()` replaces
`self._seed.activities_checked_base` with a live
`SELECT COUNT(*) FROM activity_log` (or equivalent `Store` method,
`count_activity_events()`), computed on every call — same pattern already
used for `needsAttention`/`mostUrgentCase` in that method today (per
`001`'s `data-model.md`, those are already computed live from `findings`).

**Rationale**: Direct requirement (FR-009); keeps a single computation
pattern (derive-on-read) for all KPI fields that can change during a run,
consistent with the existing codebase style rather than introducing a new
"cached counter" pattern that could drift.

**Alternatives considered**:
- *Maintain a running counter incremented on each insert*: Rejected —
  `COUNT(*)` on an in-memory SQLite table of this size is effectively free,
  and a derived-on-read value can't drift out of sync the way a
  hand-maintained counter could (e.g. if a future code path inserts rows
  without going through the counter-increment call).

## 5. SQLite thread-safety under FastAPI's request threadpool

**Decision**: All reads and writes against the shared `:memory:` connection
go through a small set of helper functions in `app/db.py`
(`execute(sql, params)`, `query(sql, params)`, `query_one(sql, params)`)
that acquire a single module-level `threading.Lock()` for the duration of
each call. The connection itself is opened with
`sqlite3.connect(":memory:", check_same_thread=False)` so it can be reused
across threads at all, and the lock is what actually makes that safe.
`store.py`'s methods call only these helpers — no method opens its own
cursor or talks to `db.py`'s connection directly.

**Rationale**: FastAPI runs synchronous `def` route handlers (all of this
project's routers today) in a worker threadpool by default, so even
strictly sequential, single-user traffic can hit the shared connection from
different OS threads across requests. `sqlite3` connections are not safe
for concurrent use from multiple threads without either
`check_same_thread=False` *and* external serialization, or a
connection-per-thread pattern. Given the tiny data volume here (tens to
low-thousands of rows) a single global lock around every DB call is
effectively free and removes the risk entirely, rather than relying on an
unenforced assumption that requests "probably" won't overlap.

**Alternatives considered**:
- *Leave `check_same_thread=False` with no lock (original tasks.md draft)*:
  Rejected after review — this is the actual bug class it was silently
  exposed to: two overlapping requests on different threadpool threads
  could interleave a write and a read (or two writes) against the same
  connection with no serialization, risking `sqlite3.OperationalError:
  database is locked` or, in the worst case, an inconsistent read. This
  was flagged during `/speckit-analyze` (finding F1) and is why this
  section exists.
- *One SQLite connection per thread (thread-local storage)*: Rejected —
  each thread would see its own private `:memory:` database, defeating the
  point of a shared in-memory store; writes from one request's thread
  wouldn't be visible to reads on another.
- *Run Uvicorn with a single worker and force all routes through the
  asyncio event loop thread (no threadpool)*: Rejected — would require
  converting every router to `async def` and auditing for accidental
  blocking calls, a much larger change than this feature's scope for no
  benefit over a simple lock at this data scale.

## 6. Test strategy for the storage swap

**Decision**: Existing `tests/contract/*` and `tests/integration/*` keep
their assertions about API-visible behavior unchanged; only test *setup*
code that reaches into `Store` internals (if any) is updated to match the
new internals. New tests: (a) a "fresh seed matches spec SC-001" parity
test comparing every read endpoint's response immediately after startup
against fixed expected values; (b) an accumulation test performing 3
sequential uploads and asserting the activity log count and
`activitiesChecked` grow monotonically by each upload's accepted count;
(c) a failed-upload test asserting no change to log size or
`activitiesChecked`.

**Rationale**: Directly exercises spec SC-001 through SC-005 without
requiring new test infrastructure — `pytest` + `TestClient` already used
throughout the project.

**Alternatives considered**: None — this follows the existing project's
established testing pattern from `001-fastapi-backend-migration`.

## Outstanding NEEDS CLARIFICATION

None. All Technical Context unknowns from `plan.md` are resolved above.
