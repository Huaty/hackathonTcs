from fastapi import APIRouter, Depends

from app.schemas.entities import Configuration
from app.store import Store, get_store

router = APIRouter(prefix="/api", tags=["configuration"])


@router.get("/configuration", response_model=Configuration)
def get_configuration(store: Store = Depends(get_store)) -> Configuration:
    return store.get_configuration()


@router.put("/configuration", response_model=Configuration)
def set_configuration(config: Configuration, store: Store = Depends(get_store)) -> Configuration:
    return store.set_configuration(config)
