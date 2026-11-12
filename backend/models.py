"""Meeting 모델. 필드 8개의 순서 · 타입은 02-specs 1절 그대로."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Meeting(Base):
    __tablename__ = "meetings"
    # SQLite 는 PK 만 주면 지운 id 를 다시 쓴다. AUTOINCREMENT 를 테이블에 넣는다
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # UTC 로 저장한다 (시간대 정보 없이 UTC 값)
    met_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attendees: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decisions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 한 줄에 하나씩 "내용 | 담당자 | 기한"
    todos: Mapped[str] = mapped_column(Text, nullable=False, default="")
