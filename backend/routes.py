"""REST API 7개. 경로는 모두 /api/ 로 시작한다 (02-specs 4절)."""

import logging
from datetime import date, datetime, time, timedelta
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import gemini
from config import MAX_UPLOAD_BYTES
from database import get_session
from models import Meeting
from schemas import NoteDetail, NoteIn, NoteSummary, TodoItem, UploadResult, to_utc_naive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# 확장자 → Gemini 에 넘길 MIME 타입
AUDIO_MIME_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


def _get_meeting_or_404(session: Session, note_id: int) -> Meeting:
    meeting = session.get(Meeting, note_id)
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회의록이 없습니다")
    return meeting


def _apply_classified(meeting: Meeting, classified: gemini.Classified) -> None:
    meeting.summary = classified.summary
    meeting.decisions = classified.decisions
    meeting.todos = classified.todos


def _local_day_start_utc(day: date) -> datetime:
    """서버 PC 시간대의 그날 0시를 UTC 로 바꾼다 (02-specs 9절)."""
    return to_utc_naive(datetime.combine(day, time.min).astimezone())


@router.post("/notes", status_code=status.HTTP_201_CREATED, response_model=NoteDetail)
def create_note(note: NoteIn, session: SessionDep) -> Meeting:
    meeting = Meeting(**note.model_dump())
    _apply_classified(meeting, gemini.classify(note.body))
    session.add(meeting)
    session.commit()
    return meeting


@router.get("/notes", response_model=list[NoteSummary])
def list_notes(
    session: SessionDep,
    q: str | None = None,
    from_: Annotated[str | None, Query(alias="from", pattern=DATE_PATTERN)] = None,
    to: Annotated[str | None, Query(pattern=DATE_PATTERN)] = None,
) -> list[Meeting]:
    stmt = select(Meeting)
    if q:
        # 제목과 참석자만 부분 일치. 본문은 검색하지 않는다
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Meeting.title.like(pattern), Meeting.attendees.like(pattern)))
    try:
        if from_:
            stmt = stmt.where(Meeting.met_at >= _local_day_start_utc(date.fromisoformat(from_)))
        if to:
            # 양끝 포함: to 다음 날 0시 전까지 (그날 23:59:59 까지)
            next_day = date.fromisoformat(to) + timedelta(days=1)
            stmt = stmt.where(Meeting.met_at < _local_day_start_utc(next_day))
    except ValueError as exc:
        # 2026-02-30 처럼 모양은 맞지만 없는 날짜
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="날짜가 올바르지 않습니다") from exc
    stmt = stmt.order_by(Meeting.met_at.desc(), Meeting.id.desc())
    return list(session.scalars(stmt))


@router.get("/notes/{note_id}", response_model=NoteDetail)
def get_note(note_id: int, session: SessionDep) -> Meeting:
    return _get_meeting_or_404(session, note_id)


@router.put("/notes/{note_id}", response_model=NoteDetail)
def update_note(note_id: int, note: NoteIn, session: SessionDep) -> Meeting:
    meeting = _get_meeting_or_404(session, note_id)
    body_changed = meeting.body != note.body
    for field, value in note.model_dump().items():
        setattr(meeting, field, value)
    # body 가 바뀌었을 때만 다시 구분한다 (02-specs 9절)
    if body_changed:
        _apply_classified(meeting, gemini.classify(note.body))
    session.commit()
    return meeting


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, session: SessionDep) -> Response:
    meeting = _get_meeting_or_404(session, note_id)
    session.delete(meeting)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/todos", response_model=list[TodoItem])
def list_todos(session: SessionDep) -> list[TodoItem]:
    meetings = session.scalars(select(Meeting).where(Meeting.todos != "").order_by(Meeting.met_at, Meeting.id))
    items = []
    for meeting in meetings:
        for line in meeting.todos.splitlines():
            if not line.strip():
                continue
            what, who, when = ([part.strip() for part in line.split("|")] + ["", ""])[:3]
            items.append(TodoItem(what=what, who=who, when=when, note_id=meeting.id, note_title=meeting.title))
    return items


@router.post("/upload", response_model=UploadResult)
async def upload_audio(file: UploadFile) -> UploadResult:
    mime_type = AUDIO_MIME_TYPES.get(PurePath(file.filename or "").suffix.lower())
    if mime_type is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="mp3, wav 만 받습니다")

    # 한도보다 1바이트 더 읽어 넘는지만 본다
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="25MB 이하만 받습니다")

    try:
        text = gemini.transcribe(data, mime_type)
    except Exception as exc:
        logger.exception("받아쓰기 실패")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="받아쓰기에 실패했습니다") from exc
    return UploadResult(text=text)
