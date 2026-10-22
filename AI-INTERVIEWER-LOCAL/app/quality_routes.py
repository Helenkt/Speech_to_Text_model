from __future__ import annotations

import json
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings
from app.database import database
from app.services.grading_quality import export_corpus, labeling_task, review_triage, save_point_labels
from app.services.interview_engine import _row_to_question
from app.services.rubric_contract import publish_contract, rubric_draft, validate_contract
from app.services.rubric_guidance import grading_guidance
from app.services.teacher_review import review_cache_key


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriterionBody(StrictBody):
    id: str = Field(min_length=1, max_length=40)
    claim: str = Field(min_length=3, max_length=1000)
    weight: float = Field(gt=0, le=100, allow_inf_nan=False, strict=True)
    credit_policy: Literal["binary"] = "binary"
    source_field: Literal["reference_answer", "key_points"]
    source_quote: str = Field(min_length=1, max_length=4000)


class ContractBody(StrictBody):
    schema_version: Literal["atomic-rubric-v3"]
    question_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    criteria: list[CriterionBody] = Field(min_length=1, max_length=30)


class PublishBody(StrictBody):
    contract: ContractBody
    attestation: str = Field(min_length=10, max_length=2000)


class PointLabelBody(StrictBody):
    point: str = Field(min_length=1, max_length=4000)
    status: Literal["met", "partial", "missing", "contradicted"]
    evidence_quote: str = Field(default="", max_length=8000)


class LabelsBody(StrictBody):
    transcript_source: Literal["original", "strong"]
    expected_transcript_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_rubric_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    annotation_mode: Literal["independent", "assisted"]
    labels: list[PointLabelBody] = Field(min_length=1, max_length=30)


def quality_router(settings: Settings, teacher_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/teacher", tags=["backend-quality"])

    @router.get("/rubrics/{question_uid}")
    def get_rubric(question_uid: str, _: dict[str, Any] = Depends(teacher_dependency)):
        with database(settings.database_path) as connection:
            row = connection.execute("SELECT * FROM questions WHERE uid = ? AND active = 1", (question_uid,)).fetchone()
            if not row:
                raise HTTPException(404, "Question not found")
            question = _row_to_question(row)
            draft = rubric_draft(question)
            _, warnings = validate_contract(question, draft)
            history = connection.execute(
                """SELECT revision_id, contract_sha256, question_fingerprint, approved_by,
                          attestation, created_at, contract_json FROM rubric_revisions
                   WHERE question_uid = ? ORDER BY revision_id DESC LIMIT 100""", (question_uid,),
            ).fetchall()
        revisions = []
        for row in history:
            revision = dict(row)
            revision["contract"] = json.loads(revision.pop("contract_json"))
            revisions.append(revision)
        return {"question": question, "draft": draft, "draft_status": "needs_teacher_review",
                "warnings": warnings, "revisions": revisions, "grading_guidance": grading_guidance(question)}

    @router.post("/rubrics/{question_uid}/publish", status_code=201)
    def publish_rubric(question_uid: str, body: PublishBody,
                       user: dict[str, Any] = Depends(teacher_dependency)):
        with database(settings.database_path) as connection:
            # Serialize source checks and publication against concurrent bank imports.
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM questions WHERE uid = ? AND active = 1", (question_uid,)).fetchone()
            if not row:
                raise HTTPException(404, "Question not found")
            try:
                return publish_contract(connection, _row_to_question(row), body.contract.model_dump(),
                                        user["user_id"], body.attestation)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc

    @router.get("/answers/{answer_id}/labeling-task")
    def get_labeling_task(answer_id: int, transcript_source: Literal["original", "strong"] = "original",
                          _: dict[str, Any] = Depends(teacher_dependency)):
        try:
            return labeling_task(settings.database_path, answer_id, transcript_source)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/answers/{answer_id}/point-labels", status_code=201)
    def label_points(answer_id: int, body: LabelsBody, user: dict[str, Any] = Depends(teacher_dependency)):
        try:
            payload = body.model_dump()
            return save_point_labels(settings.database_path, answer_id=answer_id, teacher_id=user["user_id"], **payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/quality/corpus")
    def corpus(_: dict[str, Any] = Depends(teacher_dependency)):
        return export_corpus(settings.database_path)

    @router.get("/quality/triage")
    def triage(limit: int = Query(default=1000, ge=1, le=10000),
               _: dict[str, Any] = Depends(teacher_dependency)):
        return review_triage(settings.database_path, limit,
                             expected_review_cache_key=review_cache_key(settings))

    return router
