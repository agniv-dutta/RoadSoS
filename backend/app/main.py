"""
RoadSoS — FastAPI entry point.
Registers all routers. Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.triage  import router as triage_router
from app.routers.nearby  import router as nearby_router
from app.routers.sos     import router as sos_router
from app.routers.health  import router as health_router
from app.routers.admin   import router as admin_router
from app.routers.feedback import router as feedback_router
from app.routers.demo import router as demo_router
from app.config import get_settings
from app.dialogue.session_store import SessionStore
from app.nlu.pipeline import load_classifier
import asyncio
import logging
from statistics import median

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm the ONNX-backed NLU engine on startup so first request isn't slow.
    app.state.nlu_engine = load_classifier()
    try:
        warm_latencies = app.state.nlu_engine.warm_up()
        p50_ms = median(warm_latencies) if warm_latencies else 0.0
        message = f"NLU engine ready (p50: {p50_ms:.1f}ms)"
        logger.info(message)
        print(message)
    except Exception:
        pass
    # start session cleanup task
    app.state.session_store = SessionStore()

    async def _cleanup_loop():
        while True:
            try:
                app.state.session_store.cleanup_expired()
            except Exception:
                pass
            await asyncio.sleep(60)

    app.state._session_cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    # cancel cleanup
    app.state._session_cleanup_task.cancel()


app = FastAPI(
    title="RoadSoS — Emergency NLU API",
    description=(
        "PS #9: Multilingual Emergency Intent Parsing & Triage Slot Filling (CAP v1.2)\n\n"
        "Core endpoint: `POST /api/triage` — accepts raw panic text, returns structured CAP v1.2 incident report.\n"
        "Support endpoints: `/nearby`, `/sos`, `/health`, `/admin/sync`."
    ),
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage_router)
app.include_router(nearby_router, prefix="/api")
app.include_router(sos_router, prefix="/api")
app.include_router(health_router)
app.include_router(health_router, prefix="/api")
app.include_router(admin_router)
app.include_router(admin_router, prefix="/api")
app.include_router(feedback_router)
app.include_router(feedback_router, prefix="/api")
app.include_router(demo_router)
app.include_router(demo_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "RoadSoS NLU",
        "ps": "Problem #9 — Multilingual Emergency Triage",
        "docs": "/docs",
        "endpoints": {
            "triage":  "POST /api/triage",
            "nearby":  "GET  /api/nearby",
            "sos":     "POST /api/sos",
            "health":  "GET  /api/health",
        },
    }
