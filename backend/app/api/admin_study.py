from fastapi import APIRouter, Depends

from app.api.admin_users import get_user_or_404
from app.api.deps import DbSession, require_role
from app.api.student import Days, list_question_logs, list_topic_progress
from app.models import Role
from app.schemas.study import QuestionLogOut, TopicProgressOut

# Read-only admin views of what a student records in the student panel.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.admin))])


@router.get("/students/{student_id}/question-logs", response_model=list[QuestionLogOut])
def student_question_logs(student_id: int, db: DbSession, days: Days = 30):
    return list_question_logs(db, get_user_or_404(db, student_id, Role.student).id, days)


@router.get("/students/{student_id}/topic-progress", response_model=list[TopicProgressOut])
def student_topic_progress(student_id: int, db: DbSession):
    return list_topic_progress(db, get_user_or_404(db, student_id, Role.student).id)
