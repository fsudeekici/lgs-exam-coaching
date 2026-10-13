from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, admin_analytics, admin_meeting, admin_overview, admin_study, admin_users, auth, dashboards, parent, student
from app.core.config import settings

# The interactive API docs are a development tool; they are not served in production.
docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.is_production else {}
app = FastAPI(title="LGS Exam Coaching", **docs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(dashboards.router)
api.include_router(admin.router)
api.include_router(admin_users.router)
api.include_router(admin_analytics.router)
api.include_router(admin_study.router)
api.include_router(admin_overview.router)
api.include_router(admin_meeting.router)
api.include_router(student.router)
api.include_router(parent.router)
app.include_router(api)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
