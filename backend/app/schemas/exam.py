from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    short_name: str
    session: str
    question_count: int
    topics: list[TopicOut]


class ExamCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    exam_date: date
    publisher: str | None = Field(default=None, max_length=255)

    @field_validator("publisher")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None


class ExamOut(BaseModel):
    id: int
    name: str
    exam_date: date
    publisher: str | None
    student_count: int


class ResultIn(BaseModel):
    subject_id: int
    correct: int = Field(ge=0)
    wrong: int = Field(ge=0)
    blank: int = Field(ge=0)
    mistake_topic_ids: list[int] = []


class StudentResultsIn(BaseModel):
    results: list[ResultIn]


class ResultOut(BaseModel):
    subject_id: int
    correct: int
    wrong: int
    blank: int
    net: float
    mistake_topic_ids: list[int]


class StudentResultsOut(BaseModel):
    student_id: int
    full_name: str
    total_net: float
    results: list[ResultOut]


class ExamDetail(ExamOut):
    students: list[StudentResultsOut]
