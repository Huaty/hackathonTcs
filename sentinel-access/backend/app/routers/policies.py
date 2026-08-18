from fastapi import APIRouter, Depends, HTTPException

from app.schemas.entities import PoliciesResponse, PolicyRule
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["policies"])


@router.get("/policies", response_model=PoliciesResponse)
def get_policies(store: Store = Depends(get_store)) -> PoliciesResponse:
    return PoliciesResponse(policies=store.get_policies())


@router.post("/policies/{title}/toggle", response_model=PolicyRule)
def toggle_policy(title: str, store: Store = Depends(get_store)) -> PolicyRule:
    policy = store.toggle_policy(title)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy '{title}' not found")
    return policy
