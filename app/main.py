"""
Cost Allocations API – main application entry point.

Run with:
    uvicorn app.main:app --reload

Interactive docs:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from uvicorn import run

from app.config import settings
from app.routers import (
    actual,
    auth,
    budget,
    reference,
    step1_assignments,
    step2_distributions,
    step3_labels,
    step4_review,
)
from app import seed  # runs seed data on import  # noqa: F401


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed data is already loaded via `import app.seed`
    yield
    # Shutdown: nothing to clean up for in-memory store


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Track and distribute financial costs across business Cost Centres.\n\n"
        "## Workflow\n"
        "1. **Step 1 – Assignments**: Assign expense percentages to activities.\n"
        "2. **Step 2 – Distributions**: Distribute each activity's cost across "
        "Cost Centres / Legal Entities.\n"
        "3. **Step 3 – Labels**: Classify activities with categories, tags and notes.\n"
        "4. **Step 4 – Review & Submit**: Review visualisation data and submit.\n\n"
        "## Modes\n"
        "- **Budget**: Plan future allocations.\n"
        "- **Actual**: Analyse historical spend.\n\n"
        "## Authentication\n"
        "Use `/auth/token` (form: `username` + `password`) to obtain a Bearer token.\n"
        "Seed credentials: `admin/admin123`, `analyst/analyst123`, `viewer/viewer123`."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request ID + timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred.", "type": type(exc).__name__},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(reference.router)
app.include_router(step1_assignments.router)
app.include_router(step2_distributions.router)
app.include_router(step3_labels.router)
app.include_router(step4_review.router)
app.include_router(budget.router)
app.include_router(actual.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"], summary="Health check")
def health():
    from app import db
    return {
        "status": "ok",
        "version": settings.app_version,
        "store": {
            "users": len(db.users),
            "cost_centres": len(db.cost_centres),
            "legal_entities": len(db.legal_entities),
            "periods": len(db.periods),
            "expenses": len(db.expenses),
            "activities": len(db.activities),
        },
    }

if __name__ == '__main__':
    run(
        'main:app',
        port=80,
        reload=True,
    )
