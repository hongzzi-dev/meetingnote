# 04. 작업 목록

MVP 를 3개 Phase 로 진행한다.

## 진행 규칙

- **Phase 이름과 개수는 아래 3개 그대로 고정한다. 변경 금지**
- 단계 수도 고정한다: Phase 1 - 10단계 / Phase 2 - 10단계 / Phase 3 - 8단계
- **순서대로만** 진행한다. **병렬 금지**
- **단계별 검증 필수.** 검증 방법을 통과해야 완료 열을 `[x]` 로 바꾼다
- 지시 약속
  - `backend 진행해` = Phase 2 전체
  - `frontend 진행해` = Phase 3 전체

---

## Phase 1 (설계) - CLAUDE.md + docs/ 6종 작성

| 단계 | 검증 방법 | 완료 |
|---|---|---|
| 1.1 Git 저장소 · GitHub 연결, `.env` · `.gitignore` 준비 | `git check-ignore .env` 가 `.env` 를 출력 | [x] |
| 1.2 `CLAUDE.md` - 역할 · 기술 스택 | 두 섹션이 있고 기존 내용이 남아 있음 | [x] |
| 1.3 `CLAUDE.md` - 작업 시작 전 절차 · 절대 규칙 6개 | docs 파일명 · 순서가 `docs/` 6개와 같음 | [x] |
| 1.4 `docs/` 6종 파일 생성, `docs/화면구성.pdf` 배치 | `ls docs` 에 6개 + PDF | [x] |
| 1.5 `00-overview.md` | 매핑표 · 읽는 순서 · 관심사 분리 설명이 있음 | [x] |
| 1.6 `01-product.md` | 목표 · 페르소나 · MVP 범위 · 성공 기준이 있음 | [x] |
| 1.7 `02-specs.md` | 모델 8필드 · API 7개 · 검증 · 실패 처리가 있음 | [x] |
| 1.8 `03-design.md` | 기술 결정 표 8행 · id 표 · 의존성 정책이 있음 | [x] |
| 1.9 `04-tasks.md` | Phase 3개, 단계 수 10 / 10 / 8 | [x] |
| 1.10 `05-conventions.md` + 첫 커밋 | 파일이 비어 있지 않고, 커밋이 `origin/main` 에 올라감 | [x] |

---

## Phase 2 (백엔드) - backend/ FastAPI > API 7개 + 받아쓰기

- **서버 포트는 8000 으로 고정한다**
- **의존성은 아래 8개로 한정한다. 이 목록 밖은 추가하지 않는다**
  `fastapi` · `uvicorn` · `sqlalchemy` · `pytest` · `httpx` · `google-genai` · `python-multipart` · `python-dotenv`
- pytest 실행 시 httpx2 설치 권고가 떠도 무시한다

| 단계 | 검증 방법 | 완료 |
|---|---|---|
| 2.1 `backend/` 폴더 · 가상환경 · 의존성 8개 설치 | `pip freeze` 의 직접 의존성이 8개 목록과 같음 | [ ] |
| 2.2 앱 골격 - `.env` 읽기, `/api/` 라우터, `frontend/` 같은 오리진 제공, 포트 8000 | `uvicorn` 을 8000 으로 띄워 응답 확인. 키가 코드에 없음 | [ ] |
| 2.3 Meeting 모델 8필드 (SQLAlchemy, `sqlite_autoincrement`) | pytest - 지운 id 를 다시 쓰지 않음, 테이블 DDL 에 AUTOINCREMENT | [ ] |
| 2.4 입력 스키마 (`extra="forbid"`) + 검증 실패 400 예외 핸들러 | pytest - 필수 누락 400, 스펙 외 필드 422 | [ ] |
| 2.5 세 갈래 구분 (Gemini, 02-specs 기준 프롬프트, 20자 미만 생략, 실패 시 빈 값, 429 · 503 1회 재시도) | pytest - 실제 Gemini 를 불러 세 갈래 구분 확인, 20자 미만은 호출 없이 빈 값 | [ ] |
| 2.6 `POST /api/notes` 201 · `GET /api/notes/{id}` 200 · 없는 id 404 | pytest - 저장 후 단건에 `body` 와 세 갈래 포함, `met_at` UTC 저장 | [ ] |
| 2.7 `GET /api/notes` 목록 · 검색 (`q`, `from`, `to`) | pytest - 목록에 `body` 없음, `q` 는 제목 · 참석자만, `to` 당일 포함 | [ ] |
| 2.8 `PUT /api/notes/{id}` 200 · `DELETE /api/notes/{id}` 204 | pytest - 수정 반영, 삭제 후 404 | [ ] |
| 2.9 `GET /api/todos` | pytest - 응답 필드 `what` / `who` / `when` / `note_id` / `note_title`, 회의 날짜 오래된 순 | [ ] |
| 2.10 `POST /api/upload` 받아쓰기 (415 · 413 · 502) + 전체 테스트 | pytest 전체 통과 + 실제 녹취 파일 1개로 본문 반환 확인 | [ ] |

---

## Phase 3 (프론트) - frontend/ HTML+JS+Tailwind > 화면 4종 > API 연결

- 파일은 `frontend/index.html` · `frontend/app.js` 2개만 둔다
- 화면 4종은 `02-specs.md` 화면 명세와 `03-design.md` 표대로 만든다. 배치는 `docs/화면구성.pdf`
- 백엔드(포트 8000)가 같은 오리진에서 제공한다. `file://` 로 열지 않는다

| 단계 | 검증 방법 | 완료 |
|---|---|---|
| 3.1 골격 - Tailwind CDN, 상단 고정 헤더(제목 · 탭 3개 · 테마 버튼), `max-w-6xl` 가운데, 라이트 / 다크 토글 | `http://localhost:8000` 에서 열림. 테마가 새로고침 뒤에도 유지, 처음엔 시스템 설정 | [ ] |
| 3.2 목록 화면 - 검색 입력, 카드 2열 (360px 에서 1열) | 화면구성.pdf 1쪽과 배치가 같음 | [ ] |
| 3.3 넣기 화면 - 폼 · 파일 · 본문 · 버튼 · 결과 세 칸 | 화면구성.pdf 2쪽과 배치가 같음 | [ ] |
| 3.4 상세 창 - 겹침 창, 제목 수정칸, 삭제 두 번 누르기, 본문 접기 | 화면구성.pdf 3쪽과 배치가 같음. 바깥을 누르면 닫힘 | [ ] |
| 3.5 할 일 화면 - 표 (내용 · 담당자 · 기한 · 회의) | 화면구성.pdf 4쪽과 같음. 좁은 화면에서 표만 가로 스크롤 | [ ] |
| 3.6 요소 이름 확인 | HTML 의 id 가 `03-design.md` 표와 하나씩 대조해 모두 같음 | [ ] |
| 3.7 API 연결 - 7개 호출, `met_at` 로컬 ↔ UTC 변환, 구분 실패 표시 | 화면에서 추가 · 목록 · 수정 · 삭제 · 검색 · 할 일 · 받아쓰기가 동작 | [ ] |
| 3.8 통합 확인 - `01-product.md` 성공 기준 4개 | 세 갈래 저장 · 새로고침 유지 · 360px 안 깨짐 · 검색으로 지난 회의 찾기 | [ ] |
