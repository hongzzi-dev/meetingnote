"""테스트 공통 설정. 테스트 DB 는 임시 폴더에 따로 만든다."""

import os
import tempfile
import time
from pathlib import Path

# 앱을 불러오기 전에 DB 경로를 바꿔 둔다 (실제 DB 를 건드리지 않게)
_TEST_DB_DIR = tempfile.mkdtemp(prefix="meetingnote-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TEST_DB_DIR, 'test.db').as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from database import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models import Meeting  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# 실제 Gemini 를 부르는 테스트 사이 간격 (05-conventions 4절)
GEMINI_CALL_INTERVAL_SECONDS = 1.0

MEETING_BODY = (
    "2차 스프린트 기획 회의를 시작하겠습니다. 이번 스프린트에서는 회의록 목록 화면과 검색 기능을 만들기로 했습니다. "
    "목록 화면과 검색 기능 구현은 김대리가 맡아서 다음 주 금요일까지 끝내기로 했습니다. "
    "받아쓰기 오류 처리는 이주임이 이번 주 안에 하기로 했습니다. "
    "디자인은 맥 스타일로 확정했습니다. 점심은 뭐 먹을까요. 이상으로 회의를 마치겠습니다."
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    with SessionLocal() as session:
        session.execute(delete(Meeting))
        session.commit()


@pytest.fixture
def gemini_pause():
    """실제 Gemini 를 부르는 테스트 앞에 붙인다. 호출 한도에 걸리지 않게 쉰다."""
    time.sleep(GEMINI_CALL_INTERVAL_SECONDS)


def make_note(**overrides) -> dict:
    note = {"title": "주간 회의", "met_at": "2026-11-12T07:00:00Z", "attendees": "김대리, 이주임", "body": "짧은 메모"}
    note.update(overrides)
    return note


def insert_meeting(**fields) -> int:
    """Gemini 를 거치지 않고 DB 에 바로 넣는다 (목록 · 정렬 테스트의 준비용)."""
    from datetime import datetime

    values = {"title": "회의", "met_at": datetime(2026, 11, 12, 7, 0), "attendees": "", "body": "본문"}
    values.update(fields)
    with SessionLocal() as session:
        meeting = Meeting(**values)
        session.add(meeting)
        session.commit()
        return meeting.id
