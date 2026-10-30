from typing import Any, Literal
from pydantic import Field
from ._core.core import StrictModel


class ErrorInfo(StrictModel):
    code: str
    message: str


class Metrics(StrictModel):
    model_calls_total: int = 0
    new_model_calls: int = 0


class GenerationResponse(StrictModel):
    api_schema_version: Literal['1.0'] = '1.0'
    package_version: Literal['1.0.0'] = '1.0.0'
    engine_version: Literal['1.5.0-task-source-scope'] = '1.5.0-task-source-scope'
    status: Literal['DRAFT_READY','NEEDS_REVIEW','INVALID_INPUT','ERROR','BUSY','INTERRUPTED']
    question_id: str | None = None
    job_id: str | None = None
    rubric: dict[str, Any] | None = None
    rubric_sha256: str | None = None
    quality_report: dict[str, Any] | None = None
    review_status: Literal['PENDING','NOT_AVAILABLE'] = 'NOT_AVAILABLE'
    human_approved: Literal[False] = False
    production_ready: Literal[False] = False
    model_tag: str
    model_digest: str | None = None
    metrics: Metrics = Field(default_factory=Metrics)
    artifacts: dict[str,str] = Field(default_factory=dict)
    error: ErrorInfo | None = None
