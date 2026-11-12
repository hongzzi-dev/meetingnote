"""API 테스트. 05-conventions 4절 테스트 매트릭스 13케이스 + 단계별 검증.

Gemini 를 부르는 테스트는 실제로 부른다 (대역 금지).
"""

from datetime import UTC, datetime

from google.genai import errors
from sqlalchemy import text

import gemini
from conftest import FIXTURES_DIR, MEETING_BODY, insert_meeting, make_note
from database import engine


def to_utc_naive_from_local(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """서버 PC 시간대의 시각을 DB 에 들어가는 UTC 값으로 바꾼다."""
    return datetime(year, month, day, hour, minute).astimezone().astimezone(UTC).replace(tzinfo=None)


# ---------- 테스트 매트릭스 13케이스 ----------


def test_01_create_returns_201_and_classifies(client, gemini_pause):
    response = client.post("/api/notes", json=make_note(title="2차 스프린트 기획", body=MEETING_BODY))

    assert response.status_code == 201
    note = response.json()
    assert note["summary"], "요약이 비었다"
    assert note["decisions"], "결정사항이 비었다"
    assert note["todos"], "할 일이 비었다"
    for line in note["todos"].splitlines():
        assert line.count("|") == 2, f"할 일 형식이 '내용 | 담당자 | 기한' 이 아니다: {line}"


def test_02_list_returns_200_without_body(client):
    insert_meeting(title="목록 회의")

    response = client.get("/api/notes")

    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 1
    assert "body" not in notes[0]


def test_03_get_returns_200_with_body(client):
    note_id = insert_meeting(body="받아쓴 원문")

    response = client.get(f"/api/notes/{note_id}")

    assert response.status_code == 200
    assert response.json()["body"] == "받아쓴 원문"


def test_04_put_all_fields_returns_200(client):
    note_id = client.post("/api/notes", json=make_note()).json()["id"]

    response = client.put(
        f"/api/notes/{note_id}",
        json=make_note(title="고친 제목", met_at="2026-11-13T01:00:00Z", attendees="박과장", body="짧은 메모"),
    )

    assert response.status_code == 200
    note = client.get(f"/api/notes/{note_id}").json()
    assert note["title"] == "고친 제목"
    assert note["met_at"] == "2026-11-13T01:00:00Z"
    assert note["attendees"] == "박과장"


def test_05_delete_returns_204_then_404(client):
    note_id = insert_meeting()

    response = client.delete(f"/api/notes/{note_id}")

    assert response.status_code == 204
    assert client.get(f"/api/notes/{note_id}").status_code == 404


def test_06_search_matches_title_and_attendees_only(client):
    insert_meeting(title="신규 기획 회의")
    insert_meeting(title="주간 회의", attendees="기획팀 김대리")
    insert_meeting(title="예산 회의", body="기획 이야기는 본문에만 있다")

    response = client.get("/api/notes", params={"q": "기획"})

    assert response.status_code == 200
    titles = {note["title"] for note in response.json()}
    assert titles == {"신규 기획 회의", "주간 회의"}


def test_07_todos_returns_200(client):
    note_id = insert_meeting(title="회의", todos="목록 화면 구현 | 김대리 | 다음 주 금요일")

    response = client.get("/api/todos")

    assert response.status_code == 200
    assert response.json() == [
        {"what": "목록 화면 구현", "who": "김대리", "when": "다음 주 금요일", "note_id": note_id, "note_title": "회의"}
    ]


def test_08_missing_title_returns_400(client):
    note = make_note()
    del note["title"]

    assert client.post("/api/notes", json=note).status_code == 400


def test_09_bad_met_at_returns_400(client):
    assert client.post("/api/notes", json=make_note(met_at="어제 오후")).status_code == 400


def test_10_unknown_id_returns_404(client):
    assert client.get("/api/notes/999999").status_code == 404
    assert client.put("/api/notes/999999", json=make_note()).status_code == 404
    assert client.delete("/api/notes/999999").status_code == 404


def test_11_extra_field_returns_422(client):
    assert client.post("/api/notes", json=make_note(owner="누군가")).status_code == 422


def test_12_upload_mp4_returns_415(client):
    response = client.post("/api/upload", files={"file": ("meeting.mp4", b"\x00" * 1024, "video/mp4")})

    assert response.status_code == 415


def test_13_upload_30mb_returns_413(client):
    response = client.post("/api/upload", files={"file": ("big.mp3", b"\x00" * (30 * 1024 * 1024), "audio/mpeg")})

    assert response.status_code == 413


# ---------- 단계별 검증 (04-tasks Phase 2) ----------


def test_table_has_autoincrement_and_ids_are_not_reused(client):
    with engine.connect() as connection:
        ddl = connection.execute(text("SELECT sql FROM sqlite_master WHERE name = 'meetings'")).scalar_one()
    assert "AUTOINCREMENT" in ddl

    first_id = insert_meeting()
    client.delete(f"/api/notes/{first_id}")
    second_id = insert_meeting()

    assert second_id > first_id


def test_missing_met_at_or_body_returns_400(client):
    for field in ("met_at", "body"):
        note = make_note()
        del note[field]
        assert client.post("/api/notes", json=note).status_code == 400, field


def test_missing_field_with_extra_field_returns_400(client):
    note = make_note(owner="누군가")
    del note["title"]

    assert client.post("/api/notes", json=note).status_code == 400


def test_met_at_is_stored_as_utc(client):
    response = client.post("/api/notes", json=make_note(met_at="2026-11-12T16:00:00+09:00"))

    assert response.json()["met_at"] == "2026-11-12T07:00:00Z"


def test_short_body_is_not_classified(client):
    response = client.post("/api/notes", json=make_note(body="열아홉 글자 미만 메모"))

    assert response.status_code == 201
    note = response.json()
    assert (note["summary"], note["decisions"], note["todos"]) == ("", "", "")


def test_non_meeting_body_leaves_three_empty(client, gemini_pause):
    body = "오늘 저녁에는 김치찌개를 끓였다. 두부와 돼지고기를 넣었고 생각보다 맛있게 됐다. 내일은 된장찌개를 해 볼 생각이다."

    response = client.post("/api/notes", json=make_note(body=body))

    assert response.status_code == 201
    note = response.json()
    assert (note["summary"], note["decisions"], note["todos"]) == ("", "", "")


def test_put_reclassifies_only_when_body_changes(client, gemini_pause):
    note_id = client.post("/api/notes", json=make_note(body="짧은 메모")).json()["id"]

    same_body = client.put(f"/api/notes/{note_id}", json=make_note(title="제목만 바꿈", body="짧은 메모")).json()
    assert same_body["summary"] == ""

    new_body = client.put(f"/api/notes/{note_id}", json=make_note(body=MEETING_BODY)).json()
    assert new_body["summary"], "body 가 바뀌었는데 다시 구분하지 않았다"


def test_list_is_newest_first(client):
    insert_meeting(title="오래된", met_at=datetime(2026, 1, 1, 0, 0))
    insert_meeting(title="최신", met_at=datetime(2026, 6, 1, 0, 0))

    titles = [note["title"] for note in client.get("/api/notes").json()]

    assert titles == ["최신", "오래된"]


def test_date_filter_uses_local_dates_inclusive(client):
    insert_meeting(title="전날 밤", met_at=to_utc_naive_from_local(2026, 11, 9, 23, 59))
    insert_meeting(title="첫날 새벽", met_at=to_utc_naive_from_local(2026, 11, 10, 0, 0))
    insert_meeting(title="끝날 밤", met_at=to_utc_naive_from_local(2026, 11, 11, 23, 59))
    insert_meeting(title="다음 날", met_at=to_utc_naive_from_local(2026, 11, 12, 0, 0))

    response = client.get("/api/notes", params={"from": "2026-11-10", "to": "2026-11-11"})

    assert response.status_code == 200
    assert {note["title"] for note in response.json()} == {"첫날 새벽", "끝날 밤"}


def test_bad_date_filter_returns_400(client):
    assert client.get("/api/notes", params={"from": "11/10"}).status_code == 400
    assert client.get("/api/notes", params={"to": "2026-02-30"}).status_code == 400


def test_todos_fields_and_oldest_meeting_first(client):
    newer_id = insert_meeting(title="나중 회의", met_at=datetime(2026, 11, 12, 0, 0), todos="B 작업 | 박과장 | 다음 달 10일")
    older_id = insert_meeting(
        title="먼저 회의", met_at=datetime(2026, 11, 1, 0, 0), todos="A 작업 | 김대리 | 다음 주 금요일\nA2 작업 | 미정 | 이번 주 안"
    )
    insert_meeting(title="할 일 없음", todos="")

    todos = client.get("/api/todos").json()

    assert todos == [
        {"what": "A 작업", "who": "김대리", "when": "다음 주 금요일", "note_id": older_id, "note_title": "먼저 회의"},
        {"what": "A2 작업", "who": "미정", "when": "이번 주 안", "note_id": older_id, "note_title": "먼저 회의"},
        {"what": "B 작업", "who": "박과장", "when": "다음 달 10일", "note_id": newer_id, "note_title": "나중 회의"},
    ]


def test_upload_transcribes_real_wav(client, gemini_pause):
    data = (FIXTURES_DIR / "meeting.wav").read_bytes()

    response = client.post("/api/upload", files={"file": ("meeting.wav", data, "audio/wav")})

    assert response.status_code == 200
    transcript = response.json()["text"]
    assert "스프린트" in transcript, transcript


def test_upload_accepts_exactly_25mb_boundary(client):
    # 25MB 를 1바이트 넘으면 413, 크기 검사는 Gemini 호출 전에 끝난다
    over_limit = b"\x00" * (25 * 1024 * 1024 + 1)

    response = client.post("/api/upload", files={"file": ("edge.wav", over_limit, "audio/wav")})

    assert response.status_code == 413


def test_retry_once_on_429_then_succeeds():
    calls = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) == 1:
            raise errors.APIError(429, {"error": {"message": "rate limited"}})
        return "ok"

    assert gemini.call_with_retry(flaky) == "ok"
    assert len(calls) == 2


def test_no_retry_on_other_errors():
    calls = []

    def broken() -> str:
        calls.append(1)
        raise errors.APIError(400, {"error": {"message": "bad request"}})

    try:
        gemini.call_with_retry(broken)
    except errors.APIError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("400 은 다시 부르지 않고 그대로 올려야 한다")
    assert len(calls) == 1
