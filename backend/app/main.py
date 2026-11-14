import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.routers import auth, dashboard, gpus, hosts, sessions, wallets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("labhya")

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Bring the database schema up to date before serving. FastAPI Cloud has no separate
    # release step, so this is where migrations run (see migrations/env.py for the lock).
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["configure_logging"] = False
    command.upgrade(cfg, "head")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Labhya Compute API",
    version="1.0.0",
    # The interactive docs are for development; production doesn't advertise its schema.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # auth is a bearer header, not cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    path = request.url.path
    if path.startswith("/_next/static/"):  # file names contain a content hash
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif not path.startswith(("/downloads/", "/favicon")) and "." not in path.rsplit("/", 1)[-1]:
        response.headers["Cache-Control"] = "no-store"  # API responses and HTML pages
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Log the details; never send them to the client.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on our side. Try again."}, status_code=500)


for module in (auth, gpus, hosts, wallets, sessions, dashboard):
    app.include_router(module.router)


@app.get("/health", include_in_schema=False)
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


# The web app, exported by `pnpm build:api` in frontend/. API routes above take priority.
STATIC = Path(__file__).resolve().parents[1] / "static"
if STATIC.is_dir():
    app.frontend("/", directory=STATIC)
elif settings.is_production:
    log.warning("No web app build in %s; only the API is served.", STATIC)
