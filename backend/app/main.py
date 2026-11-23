from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .db import Base, engine
from .routers import fingerprints, verify
from .security import require_api_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Supabase deployments apply supabase/migrations; create_all is a no-op for existing tables
    # and makes local SQLite development zero-setup.
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Produces and verifies perceptual video fingerprints for dashcam footage submitted "
        "with insurance claims."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "version": __version__}


protected = [Depends(require_api_key)]
app.include_router(fingerprints.router, prefix="/api", dependencies=protected)
app.include_router(verify.router, prefix="/api", dependencies=protected)
