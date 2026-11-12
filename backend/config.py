"""환경 설정. 키 · 모델 · DB 경로는 모두 .env 또는 환경 변수에서만 읽는다."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

# 이미 설정된 환경 변수(테스트 등)는 덮어쓰지 않는다
load_dotenv(PROJECT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'meetingnote.db').as_posix()}")

SERVER_PORT = 8000

# 02-specs 9절: 25 × 1024 × 1024 바이트
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# 02-specs 7절: 본문이 이 길이보다 짧으면 구분을 부르지 않는다
MIN_BODY_LENGTH_FOR_CLASSIFY = 20

# 02-specs 9절: 429 · 503 이면 이 시간만큼 기다린 뒤 1번 다시 부른다
GEMINI_RETRY_DELAY_SECONDS = 2.0
