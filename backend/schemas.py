"""요청 · 응답 스키마."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def to_utc_naive(value: datetime) -> datetime:
    """시간대가 있으면 UTC 로 바꾸고, 없으면 UTC 로 본다. DB 에는 시간대 없이 넣는다."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    return value.replace(tzinfo=None)


class NoteIn(BaseModel):
    """POST · PUT 입력. 스펙 외 필드는 422 로 거른다."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    met_at: datetime
    attendees: str = ""
    body: str = Field(min_length=1)

    @field_validator("title", "body")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 값은 받지 않는다")
        return value

    @field_validator("met_at")
    @classmethod
    def normalize_met_at(cls, value: datetime) -> datetime:
        return to_utc_naive(value)


class NoteSummary(BaseModel):
    """목록 응답. body 를 뺀다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    met_at: datetime
    attendees: str
    summary: str
    decisions: str
    todos: str

    @field_serializer("met_at")
    def serialize_met_at(self, value: datetime) -> str:
        # DB 의 UTC 값을 Z 를 붙여 내보낸다
        return value.replace(tzinfo=None).isoformat() + "Z"


class NoteDetail(NoteSummary):
    """단건 응답. body 를 넣는다."""

    body: str


class TodoItem(BaseModel):
    what: str
    who: str
    when: str
    note_id: int
    note_title: str


class UploadResult(BaseModel):
    text: str
