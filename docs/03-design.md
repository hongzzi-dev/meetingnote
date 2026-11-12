# 03. 설계

## 기술 결정

| # | 항목 | 선택 | 대안 | 근거 | 트레이드오프 |
|---|---|---|---|---|---|
| 1 | 백엔드 | FastAPI | Django, Express | 타입 힌트와 Pydantic 으로 입력 검증 · 문서화가 한 곳에서 끝난다. 작은 API 7개에 맞는 가벼운 크기 | Django 의 관리 화면 · 인증 같은 기본 기능이 없어 확장(JWT 등) 때 직접 붙여야 한다 |
| 2 | 프론트 | Vanilla JS + Tailwind CDN. 백엔드가 같은 오리진에서 제공하고, `file://` 로 직접 열지 않는다 | React, Vue | 빌드 도구 없이 `index.html` · `app.js` 2개로 끝난다. 같은 오리진이라 CORS 설정이 필요 없다 | 화면이 커지면 DOM 갱신 코드가 늘어난다. 컴포넌트 재사용이 어렵다 |
| 3 | DB | SQLite (SQLAlchemy ORM, 추후 PostgreSQL 전환 고려) | PostgreSQL 즉시 도입 | 파일 하나라 설치 · 운영이 없다. ORM 을 거치므로 나중에 연결 문자열만 바꿔 옮길 수 있다 | 동시 쓰기에 약하다. 팀 공유(확장) 단계에서는 전환이 필요하다 |
| 4 | CSS | Tailwind 만. styled-components 금지 | styled-components | 클래스만으로 스타일이 끝나 별도 CSS 파일 · 빌드가 없다. 스타일 방식이 하나로 고정된다 | HTML 의 class 가 길어진다. CDN 판이라 사용하지 않는 클래스를 걸러내지 못한다 |
| 5 | 받아쓰기 | Gemini API (`gemini-3.1-flash-lite`). 키는 `.env` 로만 읽고, 저장소에 올리지 않는다 | Whisper 자체 구동, 브라우저 음성 인식 | 받아쓰기와 세 갈래 구분을 한 API 로 처리한다. GPU · 모델 설치가 필요 없다 | 외부 호출이라 네트워크 · 요금 · 호출 한도(429)에 묶인다. 녹취가 외부로 나간다 |
| 6 | 상태관리 | 모듈 변수 + DOM 직접 갱신 | 상태관리 라이브러리 | 화면 4종 · 상태 몇 개뿐이라 라이브러리가 필요 없다. 의존성이 늘지 않는다 | 상태와 화면이 어긋나지 않게 갱신 함수를 직접 관리해야 한다 |
| 7 | 디자인 시스템 | macOS UI 톤 | Material, Ant | 둥근 모서리 · 부드러운 그림자 · 반투명 카드 · 시스템 폰트로, 개발자가 아닌 실무자에게 익숙하다 | 정해진 컴포넌트 묶음이 없어 Tailwind 클래스로 직접 만든다 |
| 8 | 테마 | 라이트 / 다크 토글, localStorage 에 저장, 초기값은 시스템 설정 | - | 저장한 선택이 새로고침 뒤에도 남고, 처음에는 OS 설정을 따른다 | 색을 두 벌 관리해야 한다 |

## 화면

### 배치

화면 배치는 **`docs/화면구성.pdf`** 를 따른다. 이 문서에 옮겨 적지 않는다.

### 화면 요소 이름

`docs/화면구성.pdf` 5쪽 id 표를 그대로 옮긴다.
**한 번 정하면 바꾸지 않는다.** 바꿔야 하면 이 문서에 사유를 먼저 적는다.

| 요소 | id | 자리 |
|---|---|---|
| 검색 입력 | `q` · `from` · `to` | 목록 화면 상단 |
| 목록 칸 | `cards` | 카드 배치 구역 |
| 넣기 폼 | `title` · `metAt` · `attendees` | 제목 · 일시 · 참석자 |
| 파일 · 본문 | `file` · `body` | 녹취 파일과 받아쓴 본문 |
| 버튼 | `btnUp` · `btnSave` | 받아쓰기 · 정리 |
| 결과 세 칸 | `result` | 요약 · 결정사항 · 할 일 |
| 상세 창 | `modal` | 카드를 누르면 뜨는 겹침 창 |
| 제목 수정칸 | `mTitle` | 상세 창 안에서 제목을 고치는 칸 |
| 할 일 표 | `todoBody` | 표의 본문 행 |

## 의존성 추가 정책

**이 문서에 사유를 적기 전에는 새 의존성을 도입할 수 없다.**

### 사전 승인 목록

| 패키지 | 쓰임 |
|---|---|
| `fastapi` | 백엔드 웹 프레임워크, `/api/` 라우팅과 입력 검증 |
| `uvicorn` | FastAPI 를 띄우는 ASGI 서버 |
| `sqlalchemy` | SQLite ORM. 추후 PostgreSQL 전환 대비 |
| `pytest` | 테스트 |
| `httpx` | 테스트에서 API 를 부르는 클라이언트 (FastAPI `TestClient` 가 쓴다) |
| `google-genai` | Gemini API 호출 (받아쓰기 · 세 갈래 구분) |
| `python-multipart` | 녹취 파일 업로드(`multipart/form-data`) 처리 |
| `python-dotenv` | `.env` 에서 `GEMINI_API_KEY` · `GEMINI_MODEL` 읽기 |
