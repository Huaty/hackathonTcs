import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.ai_client import AIServiceError, call_chat_completions
from app.schemas.entities import ReportPrepareResponse, ReportsResponse
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["reports"])


def _generate_narrative(store: Store, report_title: str) -> str | None:
    findings = store.get_findings()
    events, _source = store.get_activity_log()
    finding_lines = "\n".join(f"- {f.title} ({f.severity}, {f.service}, score {f.score}, status {f.status or 'open'})" for f in findings[:15])
    activity_count = len(events)
    prompt = (
        f"Write a short (3-5 sentence) plain-language narrative for a security "
        f"report titled '{report_title}', summarizing the current findings and "
        f"activity below. Do not invent data beyond what is given.\n\n"
        f"Findings ({len(findings)} total, showing up to 15):\n{finding_lines or '(none)'}\n\n"
        f"Activity log: {activity_count} events currently recorded.\n"
    )
    try:
        message = call_chat_completions([{"role": "user", "content": prompt}])
        narrative = (message.get("content") or "").strip()
        return narrative or None
    except AIServiceError:
        return None


@router.get("/reports", response_model=ReportsResponse)
def get_reports(store: Store = Depends(get_store)) -> ReportsResponse:
    return ReportsResponse(reports=store.get_reports())


@router.post("/reports/{title}/prepare", response_model=ReportPrepareResponse)
def prepare_report(title: str, store: Store = Depends(get_store)) -> ReportPrepareResponse:
    report = store.get_report(title)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report '{title}' not found")
    return ReportPrepareResponse(
        title=report.title,
        status="ready",
        preparedAt=datetime.now(timezone.utc).isoformat(),
        narrative=_generate_narrative(store, report.title),
    )


@router.get("/reports/export.csv")
def export_activity_csv(store: Store = Depends(get_store)) -> StreamingResponse:
    events, _source = store.get_activity_log()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Time", "Actor", "Action", "Source", "System", "Status"])
    for event in events:
        writer.writerow([event.time, event.actor, event.action, event.source, event.system, event.status])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity-export.csv"},
    )
