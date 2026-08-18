import csv
import io
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.schemas.entities import ActivityEvent, DatasetImportResult
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["datasets"])

MAX_RECORDS = 10_000

FIELD_ALIASES = {
    "time": ["timestamp", "eventTime", "time", "date"],
    "actor": ["user", "userName", "username", "identity", "principal", "email", "actor", "account"],
    "action": ["action", "eventName", "event", "activity", "operation", "message"],
    "source": ["sourceIp", "sourceIP", "ip", "location", "region", "country"],
    "system": ["service", "source", "provider", "product", "cloud", "system"],
}
STATUS_ALIASES = ["status", "result", "outcome", "severity", "risk"]
NEEDS_ATTENTION_PATTERN = re.compile(r"deny|fail|error|alert|high|critical|risk|anomal", re.I)
SENSITIVE_ACTION_PATTERN = re.compile(r"delete|admin|secret|permission|policy", re.I)


def _first_value(raw: dict, keys: list[str]) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return "—"


def _coerce_record(raw: dict, index: int) -> tuple[Optional[ActivityEvent], Optional[str]]:
    if not raw:
        return None, f"Row {index}: empty record"

    time = _first_value(raw, FIELD_ALIASES["time"])
    if time == "—":
        time = f"Record {index}"
    actor = _first_value(raw, FIELD_ALIASES["actor"])
    action = _first_value(raw, FIELD_ALIASES["action"])
    source = _first_value(raw, FIELD_ALIASES["source"])
    system = _first_value(raw, FIELD_ALIASES["system"])
    raw_status = _first_value(raw, STATUS_ALIASES).lower()

    needs_attention = bool(NEEDS_ATTENTION_PATTERN.search(raw_status)) or bool(
        SENSITIVE_ACTION_PATTERN.search(action.lower())
    )
    status = "Needs attention" if needs_attention else "Normal"
    tone = "high" if needs_attention else "normal"

    return ActivityEvent(time=time, actor=actor, action=action, source=source, system=system, status=status, tone=tone), None


def _extract_records(text: str, is_json: bool) -> list[dict]:
    if is_json:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

        if isinstance(parsed, list):
            candidate = parsed
        elif isinstance(parsed, dict):
            candidate = parsed.get("events") or parsed.get("records") or parsed.get("data")
        else:
            candidate = None

        if not isinstance(candidate, list) or not candidate:
            raise HTTPException(
                status_code=400,
                detail="JSON file must contain an array, or an events, records, or data array.",
            )
        return candidate

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file needs a header row.")
    return list(reader)


@router.post("/datasets", response_model=DatasetImportResult)
async def import_dataset(file: UploadFile = File(...), store: Store = Depends(get_store)) -> DatasetImportResult:
    raw_bytes = await file.read()
    filename = (file.filename or "").lower()
    is_json = filename.endswith(".json") or "json" in (file.content_type or "")

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.") from exc

    candidates = _extract_records(text, is_json)

    if len(candidates) > MAX_RECORDS:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {MAX_RECORDS:,} record limit (found {len(candidates):,}).",
        )

    accepted: list[ActivityEvent] = []
    errors: list[str] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            errors.append(f"Row {index}: not a record object")
            continue
        event, error = _coerce_record(item, index)
        if event is not None:
            accepted.append(event)
        else:
            errors.append(error or f"Row {index}: invalid record")

    if not accepted:
        raise HTTPException(status_code=400, detail="No usable records were found in the uploaded file.")

    store.replace_activity_log(accepted, "imported")

    return DatasetImportResult(acceptedCount=len(accepted), rejectedCount=len(errors), errors=errors[:20])
