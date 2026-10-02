from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class StartInterviewRequest(BaseModel):
    language: str = Field(default="vi", min_length=2, max_length=12)
    subject: str | None = Field(default=None, max_length=200)
    question_count: int = Field(default=5, ge=1, le=30)
    starting_difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=20_000)
    transcription_id: str | None = Field(default=None, max_length=64)


class AccountActiveRequest(BaseModel):
    active: bool


class ExamRoundCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    exam_code: str = Field(min_length=4, max_length=20)
    language: str = Field(min_length=2, max_length=12)
    subject: str = Field(min_length=1, max_length=200)
    question_count: int = Field(default=5, ge=1, le=30)
    starting_difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"
    answer_mode: Literal["text", "voice", "both"] = "text"
    starts_at: datetime
    ends_at: datetime


class ExamStatusRequest(BaseModel):
    status: Literal["open", "closed"]
