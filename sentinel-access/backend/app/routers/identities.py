from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.entities import IdentitiesResponse, IdentityProfileResponse, IdentityTimelineResponse, SecurityEvent
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["identities"])


@router.get("/identities", response_model=IdentitiesResponse)
def get_identities(store: Store = Depends(get_store)) -> IdentitiesResponse:
    return IdentitiesResponse(identities=store.get_identities())


@router.get("/identities/{identity_id}", response_model=IdentityProfileResponse)
def get_identity_profile(
    identity_id: str,
    eventLimit: int = Query(25, ge=1, le=100),
    assessmentLimit: int = Query(10, ge=1, le=100),
    store: Store = Depends(get_store),
) -> IdentityProfileResponse:
    profile = store.build_identity_profile(identity_id, eventLimit, assessmentLimit)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Identity '{identity_id}' not found")
    return profile


@router.post("/identities/{identity_id}/simulated-events", response_model=SecurityEvent)
def simulate_identity_event(identity_id: str, store: Store = Depends(get_store)) -> SecurityEvent:
    if store.get_identity_by_id(identity_id) is None:
        raise HTTPException(status_code=404, detail=f"Identity '{identity_id}' not found")
    return store.simulate_event_for_identity(identity_id)


@router.get("/identities/{identity_id}/timeline", response_model=IdentityTimelineResponse)
def get_identity_timeline(identity_id: str, store: Store = Depends(get_store)) -> IdentityTimelineResponse:
    identity = store.get_identity_by_id(identity_id)
    if identity is None:
        # Deprecated legacy fallback: match by display name, but only when
        # it resolves to exactly one identity (contracts/identities.md).
        matches = [i for i in store.get_identities() if i.name == identity_id]
        if len(matches) == 1:
            identity = matches[0]
    if identity is None:
        raise HTTPException(status_code=404, detail=f"Identity '{identity_id}' not found")

    events, _source = store.get_activity_log()
    matching = [e for e in events if e.actor == identity.name]
    return IdentityTimelineResponse(events=matching)
