import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.entities import ReportPrepareResponse, ReportsResponse
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["reports"])


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
