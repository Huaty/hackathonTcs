from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.entities import ActivityResponse
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["activity"])


@router.get("/activity", response_model=ActivityResponse)
def get_activity(
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    store: Store = Depends(get_store),
) -> ActivityResponse:
    events, source = store.get_activity_log()

    if search:
        query = search.lower()
        events = [
            e
            for e in events
            if query in e.actor.lower() or query in e.action.lower() or query in e.source.lower()
        ]

    if status:
        events = [e for e in events if e.status == status]

    return ActivityResponse(events=events, source=source)
