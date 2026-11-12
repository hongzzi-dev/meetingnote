# 05. 코딩 규칙

## 1. 명명

| 대상 | 규칙 | 예 |
|---|---|---|
| 백엔드 (Python) | snake_case | `met_at`, `create_note()` |
| 프론트 (JS) | camelCase | `metAt`, `loadNotes()` |
| 컴포넌트 · 클래스 | PascalCase | `Meeting`, `NoteCreate` |

- 식별자는 영어로 짓는다. **주석만 한국어**로 쓴다

## 2. 금지 6개

| 금지 | 이유 | 대안 |
|---|---|---|
| `print` 디버깅 | 노이즈 | `logging` 모듈 |
| bare `except` | 예외 삼킴 | `except SpecificError` |
| API 키 하드코딩 | 키 유출 | `.env` + `os.getenv` |
| `any` 타입 (TS) | 의미 상실 | 명시적 타입 |
| `!important` | 우선순위 꼬임 | 셀렉터 개선 |
| Gemini 클라이언트를 한 줄로 만들어 바로 호출 | 호출 도중 회수되어 `Cannot send a request, as the client has been closed` 오류 | 모듈에 한 번 만들어 재사용 |

## 3. .gitignore

아래 항목을 반드시 넣는다.

```
__pycache__/
.pytest_cache/
.venv/
*.db
*.log
.env
.claude/todo-guard/
```

## 4. 테스트

### 테스트 매트릭스

**MVP 기준 13케이스.** 뒤에 결함이 나오면 케이스를 늘리고 이 숫자도 같이 고친다.

| # | 케이스 | 요청 | 기대 응답 |
|---|---|---|---|
| 1 | 정상 생성 | `POST /api/notes` title + met_at + body | 201 |
| 2 | 목록 | `GET /api/notes` | 200, `body` 없음 |
| 3 | 단건 | `GET /api/notes/{id}` | 200, `body` 있음 |
| 4 | 수정 | `PUT /api/notes/{id}` 전 필드 | 200 |
| 5 | 삭제 | `DELETE /api/notes/{id}` | 204 |
| 6 | 검색 | `GET /api/notes?q=기획` | 200, 제목 · 참석자 일치만 |
| 7 | 할 일 | `GET /api/todos` | 200 |
| 8 | title 누락 | `POST /api/notes` title 없이 | 400 |
| 9 | met_at 형식 오류 | `POST /api/notes` met_at 이 날짜 형식 아님 | 400 |
| 10 | 없는 id | `GET /api/notes/{없는 id}` | 404 |
| 11 | 스펙 외 필드 | `POST /api/notes` 모르는 필드 포함 | 422 |
| 12 | 업로드 mp4 파일 | `POST /api/upload` mp4 | 415 |
| 13 | 업로드 30MB 파일 | `POST /api/upload` 30MB | 413 |

### 실제 Gemini 호출

- **테스트도 실제 Gemini 를 부른다. 대역(mock)으로 바꾸지 않는다.**
  받아쓰기와 세 갈래 구분이 진짜 되는지는 실제로 불러 봐야 알 수 있다
- 한도에 걸리지 않게, Gemini 를 부르는 테스트는 **호출 사이를 1초쯤 띄운다**

## 5. git 커밋 규칙

`<타입>: <한국어 요약>`

| 타입 | 쓰임 |
|---|---|
| `feat` | 기능 추가 |
| `fix` | 결함 수정 |
| `docs` | 문서 |
| `refactor` | 동작을 바꾸지 않는 코드 정리 |
| `test` | 테스트 |
| `chore` | 설정 · 의존성 · 기타 |

예: `feat: 회의록 목록 검색 추가`
