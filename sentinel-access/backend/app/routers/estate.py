from fastapi import APIRouter, Depends

from app.schemas.entities import EstateResponse
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["estate"])


@router.get("/estate", response_model=EstateResponse)
def get_estate(store: Store = Depends(get_store)) -> EstateResponse:
    sources, online = store.get_cloud_sources()
    return EstateResponse(sources=sources, sourcesOnline=online)
