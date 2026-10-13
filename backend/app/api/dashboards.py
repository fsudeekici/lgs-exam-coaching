from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.models import Role, User

# Placeholder endpoints: one per role, empty until real dashboard data exists.
router = APIRouter(tags=["dashboards"])


@router.get("/admin/dashboard")
def admin_dashboard(user: Annotated[User, Depends(require_role(Role.admin))]) -> dict:
    return {"role": user.role}


@router.get("/student/dashboard")
def student_dashboard(user: Annotated[User, Depends(require_role(Role.student))]) -> dict:
    return {"role": user.role}


@router.get("/parent/dashboard")
def parent_dashboard(user: Annotated[User, Depends(require_role(Role.parent))]) -> dict:
    return {"role": user.role}
