"""FastAPI application: JSON API plus the Vue single-page front end."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.api import router as api_router
from app.auth import require_session
from app.auth import router as auth_router
from app.config import FRONTEND_DIST
from app.db import engine, init_db, load_settings
from app.scheduler import apply_schedule, scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO, which would leak the Telegram bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

SPA_ROUTES = ("/", "/settings", "/login")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize the database and start the scheduler for the app's lifetime."""
    init_db()
    with Session(engine) as session:
        apply_schedule(load_settings(session))
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


# The data API needs a session. The page shell, the login endpoints, the
# built JS/CSS bundle and /healthz (used by the hosting platform) stay public.
PROTECTED = [Depends(require_session)]

app = FastAPI(title="Toca na Lagoa", lifespan=lifespan)
# Vite builds the front end with base "/static/"; check_dir is off so the API
# still starts (and tests run) before the first front-end build.
app.mount("/static", StaticFiles(directory=FRONTEND_DIST, check_dir=False), name="static")
app.include_router(auth_router)
app.include_router(api_router, dependencies=PROTECTED)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    """Reply with the first validation problem as a single Portuguese sentence."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _validation_message(error.errors())},
    )


def _validation_message(errors: list[dict]) -> str:
    """Our validators raise Portuguese ValueErrors; other errors only name the field."""
    first = errors[0]
    if first["type"] == "value_error":
        return str(first["ctx"]["error"])
    field = ".".join(str(part) for part in first["loc"] if part != "body")
    return f"Valor inválido em {field}" if field else "Requisição inválida"


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


def serve_frontend() -> Response:
    """Serve the Vue app shell; client-side routing picks the page."""
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return PlainTextResponse(
            "Front-end não compilado. Rode `npm ci && npm run build` em frontend/ ou use o Docker.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return FileResponse(index)


for spa_route in SPA_ROUTES:
    app.add_api_route(spa_route, serve_frontend, methods=["GET"], include_in_schema=False)
