from fastapi import APIRouter, Depends, HTTPException

from app.schemas.entities import IdentitiesResponse, IdentityTimelineResponse
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["identities"])


@router.get("/identities", response_model=IdentitiesResponse)
def get_identities(store: Store = Depends(get_store)) -> IdentitiesResponse:
    return IdentitiesResponse(identities=store.get_identities())


@router.get("/identities/{name}/timeline", response_model=IdentityTimelineResponse)
def get_identity_timeline(name: str, store: Store = Depends(get_store)) -> IdentityTimelineResponse:
    identity = next((i for i in store.get_identities() if i.name == name), None)
    if identity is None:
        raise HTTPException(status_code=404, detail=f"Identity '{name}' not found")

    events, _source = store.get_activity_log()
    matching = [e for e in events if e.actor == name]
    return IdentityTimelineResponse(events=matching)
