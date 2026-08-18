from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import activity, command_center, configuration, datasets, estate, identities, policies, reports
from app.store import get_store


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store = get_store()
    print(
        "Sentinel Access API seeded: "
        f"{len(store.findings)} findings, "
        f"{len(store.identities)} identities, "
        f"{len(store.policies)} policies"
    )
    yield


app = FastAPI(title="Sentinel Access API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(command_center.router)
app.include_router(activity.router)
app.include_router(identities.router)
app.include_router(estate.router)
app.include_router(policies.router)
app.include_router(reports.router)
app.include_router(configuration.router)
app.include_router(datasets.router)
