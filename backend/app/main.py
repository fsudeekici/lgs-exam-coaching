from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, admin_analytics, admin_users, auth, dashboards
from app.core.config import settings

app = FastAPI(title="LGS Exam Coaching")

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
app.include_router(api)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
