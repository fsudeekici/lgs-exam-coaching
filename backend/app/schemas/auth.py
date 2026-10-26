from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Role
from app.schemas.user import Password


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    # The main admin, who manages the other admins and sees every student.
    is_superadmin: bool
    # Empty until the user accepts the KVKK privacy notice.
    kvkk_consent_at: datetime | None


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password
