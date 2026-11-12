"""Gemini 호출: 받아쓰기와 세 갈래 구분.

클라이언트는 모듈에서 한 번만 만들어 재사용한다 (05-conventions 금지 6번).
"""

import io
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RETRY_DELAY_SECONDS, MIN_BODY_LENGTH_FOR_CLASSIFY

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 503}

# 02-specs 2절 기준. 문구를 바꾸지 않는다
CLASSIFY_CRITERIA = """\
요약 - 회의 전체를 3~5줄로. 새로운 사실을 지어내지 말 것
결정사항 - 「하기로 했다 / 확정 / 승인」 처럼 합의가 끝난 것만. 논의만 하고 안 정한 것은 넣지 말 것
할 일 - 담당자와 기한이 드러난 것만. 담당자가 없으면 미정으로 적을 것
셋 중 어디에도 안 들어가는 잡담은 버릴 것"""

CLASSIFY_PROMPT = f"""\
아래 본문을 요약 / 결정사항 / 할 일 세 갈래로 나눠라.

기준:
{CLASSIFY_CRITERIA}

본문이 회의 내용이 아니면 is_meeting 을 false 로 하고 세 목록을 비워라.
할 일의 기한은 회의에서 말한 그대로 적고 날짜로 바꾸지 마라.

본문:
"""

TRANSCRIBE_PROMPT = "이 녹취 파일의 말을 들리는 그대로 한국어 텍스트로 받아써라. 받아쓴 텍스트만 출력하라."


class ClassifiedTodo(BaseModel):
    what: str
    who: str
    when: str


class ClassifyResponse(BaseModel):
    is_meeting: bool
    summary: list[str]
    decisions: list[str]
    todos: list[ClassifiedTodo]


@dataclass(frozen=True)
class Classified:
    """DB 에 그대로 넣는 세 칸. 각 칸은 줄바꿈으로 구분한다."""

    summary: str = ""
    decisions: str = ""
    todos: str = ""


EMPTY_CLASSIFIED = Classified()

T = TypeVar("T")


@cache
def get_client() -> genai.Client:
    return genai.Client(api_key=GEMINI_API_KEY)


def call_with_retry(func: Callable[[], T]) -> T:
    """429 · 503 이면 잠시 뒤 1번 다시 부른다."""
    try:
        return func()
    except errors.APIError as exc:
        if exc.code not in RETRYABLE_STATUS_CODES:
            raise
        logger.warning("Gemini %s 응답, %.0f초 뒤 다시 부른다", exc.code, GEMINI_RETRY_DELAY_SECONDS)
        time.sleep(GEMINI_RETRY_DELAY_SECONDS)
        return func()


def _clean_cell(value: str) -> str:
    # 칸 구분자 · 줄바꿈이 값 안에 들어가면 저장 형식이 깨진다
    return " ".join(value.replace("|", "/").split())


def _join_lines(items: list[str]) -> str:
    return "\n".join(line for line in (_clean_cell(item) for item in items) if line)


def _format_todos(todos: list[ClassifiedTodo]) -> str:
    lines = []
    for todo in todos:
        what = _clean_cell(todo.what)
        if not what:
            continue
        who = _clean_cell(todo.who) or "미정"
        when = _clean_cell(todo.when)
        lines.append(f"{what} | {who} | {when}")
    return "\n".join(lines)


def classify(body: str) -> Classified:
    """본문을 세 갈래로 나눈다. 실패하면 빈 값을 돌려주고 logging 으로만 남긴다."""
    if len(body.strip()) < MIN_BODY_LENGTH_FOR_CLASSIFY:
        return EMPTY_CLASSIFIED

    try:
        response = call_with_retry(
            lambda: get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=CLASSIFY_PROMPT + body,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClassifyResponse,
                ),
            )
        )
        result = ClassifyResponse.model_validate_json(response.text or "")
    except Exception:
        # 구분 실패는 저장을 막지 않는다 (02-specs 7절)
        logger.exception("세 갈래 구분 실패")
        return EMPTY_CLASSIFIED

    if not result.is_meeting:
        return EMPTY_CLASSIFIED

    return Classified(
        summary=_join_lines(result.summary),
        decisions=_join_lines(result.decisions),
        todos=_format_todos(result.todos),
    )


def transcribe(data: bytes, mime_type: str) -> str:
    """녹취 파일을 받아쓴다. 실패하면 예외를 그대로 올린다 (호출한 쪽이 502 로 바꾼다)."""
    client = get_client()
    uploaded = call_with_retry(
        lambda: client.files.upload(file=io.BytesIO(data), config=types.UploadFileConfig(mime_type=mime_type))
    )
    try:
        response = call_with_retry(
            lambda: client.models.generate_content(model=GEMINI_MODEL, contents=[TRANSCRIBE_PROMPT, uploaded])
        )
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except errors.APIError:
            logger.warning("업로드한 녹취 파일 삭제 실패: %s", uploaded.name)
    return (response.text or "").strip()
