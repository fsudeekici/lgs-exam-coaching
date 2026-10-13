from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def check_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Şifre en az 8 karakter olmalıdır")
    # bcrypt only accepts up to 72 bytes.
    if len(password.encode()) > 72:
        raise ValueError("Şifre çok uzun")
    return password


def not_in_future(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("Veli onay tarihi ileri bir tarih olamaz")
    return value


Name = Annotated[str, Field(min_length=1, max_length=255)]
ConsentDate = Annotated[date | None, AfterValidator(not_in_future)]
Password = Annotated[str, AfterValidator(check_password)]


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class StudentOut(UserRef):
    email: str
    school: str | None
    class_name: str | None
    # Empty until the admin records the parent's consent; the student cannot log in before that.
    parent_consent_date: date | None
    is_active: bool
    # Too many wrong passwords: logins for this email are blocked for now.
    login_blocked: bool = False
    parents: list[UserRef]


class ParentOut(UserRef):
    email: str
    is_active: bool
    login_blocked: bool = False
    students: list[UserRef]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name
    email: EmailStr
    password: Password
    school: str | None = Field(default=None, max_length=255)
    class_name: str | None = Field(default=None, max_length=50)
    parent_consent_date: ConsentDate = None


class ParentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name
    email: EmailStr
    password: Password
    student_ids: list[int] = []


class StudentUpdate(BaseModel):
    """Fields left out (or null) stay unchanged. An empty school or class clears it."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None
    school: str | None = Field(default=None, max_length=255)
    class_name: str | None = Field(default=None, max_length=50)
    # Unlike the other fields, sending null here clears the consent; leave it out to keep it.
    parent_consent_date: ConsentDate = None
    is_active: bool | None = None


class ParentUpdate(BaseModel):
    """Fields left out (or null) stay unchanged. `student_ids` replaces the linked students."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None
    is_active: bool | None = None
    student_ids: list[int] | None = None
