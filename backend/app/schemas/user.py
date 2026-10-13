from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def check_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Şifre en az 8 karakter olmalıdır")
    # bcrypt only accepts up to 72 bytes.
    if len(password.encode()) > 72:
        raise ValueError("Şifre çok uzun")
    return password


Name = Annotated[str, Field(min_length=1, max_length=255)]
Password = Annotated[str, AfterValidator(check_password)]


class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class StudentOut(UserRef):
    email: str
    school: str | None
    class_name: str | None
    is_active: bool
    parents: list[UserRef]


class ParentOut(UserRef):
    email: str
    is_active: bool
    students: list[UserRef]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name
    email: EmailStr
    password: Password
    school: str | None = Field(default=None, max_length=255)
    class_name: str | None = Field(default=None, max_length=50)


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
    is_active: bool | None = None


class ParentUpdate(BaseModel):
    """Fields left out (or null) stay unchanged. `student_ids` replaces the linked students."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Name | None = None
    email: EmailStr | None = None
    password: Password | None = None
    is_active: bool | None = None
    student_ids: list[int] | None = None
