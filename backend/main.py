"""MeetingNote 백엔드. 실행: backend/ 에서 `uvicorn main:app --port 8000`"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIR
from database import init_db
from routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MeetingNote", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """검증 실패는 400. 스펙 외 필드만 있는 경우만 422 로 남긴다 (02-specs 3절)."""
    errors = exc.errors()
    only_extra_fields = bool(errors) and all(error["type"] == "extra_forbidden" for error in errors)
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT if only_extra_fields else status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=status_code, content={"detail": jsonable_errors(errors)})


def jsonable_errors(errors: list[dict]) -> list[dict]:
    # ctx 안의 예외 객체는 JSON 으로 못 바꾸므로 뺀다
    return [{key: value for key, value in error.items() if key in ("type", "loc", "msg")} for error in errors]


app.include_router(router)

# 프론트는 같은 오리진에서 제공한다. API 라우터 뒤에 붙여야 /api 가 가려지지 않는다
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logging.getLogger(__name__).warning("frontend/ 가 없어 화면 없이 API 만 제공합니다: %s", FRONTEND_DIR)
