from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import TopicStatus


class QuestionLogIn(BaseModel):
    log_date: date
    subject_id: int
    topic_id: int | None = None
    solved: int = Field(gt=0, le=1000)
    correct: int = Field(ge=0)
    wrong: int = Field(ge=0)

    @model_validator(mode="after")
    def counts_fit(self) -> "QuestionLogIn":
        if self.correct + self.wrong > self.solved:
            raise ValueError("Doğru ve yanlış toplamı çözülen soru sayısını geçemez")
        return self


class QuestionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_date: date
    subject_id: int
    topic_id: int | None
    solved: int
    correct: int
    wrong: int


class TopicProgressIn(BaseModel):
    status: TopicStatus


class TopicProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    status: TopicStatus
