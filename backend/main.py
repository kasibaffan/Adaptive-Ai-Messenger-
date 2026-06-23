from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, JSONResponse
from dotenv import load_dotenv
from database import init_db
from services.scheduler import start_scheduler, stop_scheduler
from services.rate_limit import limiter
from routes import auth, documents, chat, reminders, gaps, billing
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from logging_config import configure_logging, init_sentry
import contextlib
import logging
import os
import time

load_dotenv()
configure_logging()
init_sentry()
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",") if o.strip()
]


# Dashboard-only sub-paths under /chat/ that must stay behind the origin
# allowlist, even though most of /chat/ is intentionally public (widget).
RESTRICTED_CHAT_PATHS = {"/chat/logs/all", "/chat/stats"}


def _is_public_widget_path(path: str) -> bool:
    """The chat-send and public-profile endpoints are the embeddable widget's
    API calls — by design they must be reachable from any company's
    customer-facing website, so they're exempt from the origin allowlist that
    protects every other endpoint."""
    return path.startswith("/chat/") and path not in RESTRICTED_CHAT_PATHS


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Adaptive AI Messenger",
    description="Multi-tenant AI assistant + reminder platform for businesses",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches anything that slips past route-level error handling so a bug
    returns a clean 500 instead of leaking a stack trace to the client — full
    traceback still goes to the logs (and Sentry, if configured)."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)")
    return response


@app.middleware("http")
async def scoped_cors(request: Request, call_next):
    origin = request.headers.get("origin")
    allow_any_origin = _is_public_widget_path(request.url.path)
    is_allowed = allow_any_origin or (origin in ALLOWED_ORIGINS)

    if request.method == "OPTIONS":
        headers = {}
        if origin and is_allowed:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"
            if not allow_any_origin:
                headers["Access-Control-Allow-Credentials"] = "true"
        return Response(status_code=200, headers=headers)

    response = await call_next(request)
    if origin and is_allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        if not allow_any_origin:
            response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(reminders.router)
app.include_router(gaps.router)
app.include_router(billing.router)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))


@app.get("/privacy")
def privacy():
    return FileResponse(os.path.join(FRONTEND_DIR, "privacy.html"))


@app.get("/terms")
def terms():
    return FileResponse(os.path.join(FRONTEND_DIR, "terms.html"))


@app.get("/health")
def health():
    return {"status": "ok"}
