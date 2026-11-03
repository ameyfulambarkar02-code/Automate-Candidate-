import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import models
from app.api import auth, candidates, dashboard, forms
from app.config import get_settings
from app.database import Base, engine

settings = get_settings()
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine, tables=[
        models.User.__table__,
        models.ConnectedForm.__table__,
        models.Candidate.__table__,
    ])
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="candidate_session",
    same_site="none" if settings.is_production else "lax",
    https_only=settings.cookie_secure or settings.is_production,
    max_age=60 * 60 * 24 * 7,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(forms.router, prefix=settings.api_prefix)
app.include_router(candidates.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Candidate Automation API is running"}


@app.get(f"{settings.api_prefix}/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
