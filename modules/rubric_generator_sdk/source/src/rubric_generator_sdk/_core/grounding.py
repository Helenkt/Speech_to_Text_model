"""Select source IDs with the LLM; recover exact quotes with trusted code."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass
from typing import Annotated, Literal

from pydantic import Field, create_model

from .core import (CriterionDraft, InputSpec, Plan, QuestionType, StrictModel,
                   TaskDraft, Text)


@dataclass(frozen=True)
class SourceBlock:
    source: str
    quote: str
    start: int
    end: int


def source_catalog(spec: InputSpec) -> dict[str, SourceBlock]:
    catalog = {}
    for field, prefix in [("question", "Q"), ("reference_answer", "R")]:
        value = getattr(spec, field)
        catalog[prefix + "0"] = SourceBlock(field, value, 0, len(value))
        spans, cursor = [], 0
        for match in re.finditer(r"(?<=[.!?;。！？；])\s+|[\r\n]+", value):
            spans.append((cursor, match.start()))
            cursor = match.end()
        spans.append((cursor, len(value)))
        count = 1
        for start, end in spans:
            while start < end and value[start].isspace():
                start += 1
            while start < end and value[end - 1].isspace():
                end -= 1
            if start == end or (start == 0 and end == len(value)):
                continue
            catalog[prefix + str(count)] = SourceBlock(field, value[start:end], start, end)
            count += 1
    return catalog


def catalog_json(catalog: dict[str, SourceBlock]) -> dict:
    return {key: asdict(block) for key, block in catalog.items()}


def task_source_catalog(task, catalog: dict[str, SourceBlock]) -> dict[str, SourceBlock]:
    """Allow only reference blocks assigned to this task, or their exact subspans."""
    selected = [block for block in catalog.values()
                if block.source == "reference_answer" and block.quote in task.reference_quotes]
    result = {key:block for key,block in catalog.items()
              if block.source == "question" or any(
                  origin.start <= block.start and block.end <= origin.end
                  for origin in selected if block.source == "reference_answer")}
    if not any(block.source == "reference_answer" for block in result.values()):
        raise ValueError(f"No assigned reference source blocks for task {task.id}")
    return result


def selection_contracts(catalog: dict[str, SourceBlock]):
    """Constrain choices to existing IDs in both JSON schema and validation."""
    question_ids = tuple(key for key, value in catalog.items() if value.source == "question")
    reference_ids = tuple(key for key, value in catalog.items() if value.source == "reference_answer")
    QuestionID = Literal[question_ids]
    ReferenceID = Literal[reference_ids]
    task = create_model("TaskSourceSelection", __base__=StrictModel,
        text=(Text, ...), question_source_id=(QuestionID, ...),
        primary_type=(QuestionType, ...), secondary_types=(list[QuestionType], ...),
        reference_source_ids=(list[ReferenceID], ...),
        importance=(Annotated[int, Field(ge=1, le=10)], ...),
        coverage=(Literal["COMPLETE", "INCOMPLETE", "CONFLICT"], ...),
        coverage_note=(Text, ...))
    plan = create_model("PlanSourceSelection", __base__=StrictModel,
        tasks=(Annotated[list[task], Field(max_length=5)], ...),
        needs_review=(bool, ...), concerns=(list[Text], ...))
    fields = {name: (info.annotation, copy.deepcopy(info))
              for name, info in CriterionDraft.model_fields.items()
              if name not in {"id", "task_id", "requirement_quote", "sources"}}
    fields["requirement_source_id"] = (QuestionID, ...)
    fields["reference_source_ids"] = (Annotated[list[ReferenceID], Field(min_length=1)], ...)
    criterion = create_model("CriterionSourceSelection", __base__=StrictModel, **fields)
    draft = create_model("TaskDraftSourceSelection", __base__=StrictModel,
        criteria=(Annotated[list[criterion], Field(min_length=1, max_length=8)], ...))
    return plan, draft


def _get(catalog, key, source):
    if key not in catalog or catalog[key].source != source:
        raise ValueError(f"Unknown {source} source ID: {key}")
    return catalog[key].quote


def materialize_plan(choice, catalog: dict[str, SourceBlock]) -> Plan:
    data = choice.model_dump(mode="json")
    for index, task in enumerate(data["tasks"], 1):
        task["id"] = f"T{index}"
        task["question_quote"] = _get(catalog, task.pop("question_source_id"), "question")
        task["reference_quotes"] = [_get(catalog, key, "reference_answer")
                                    for key in task.pop("reference_source_ids")]
    return Plan.model_validate_json(json.dumps(data, ensure_ascii=False))


def materialize_draft(choice, task_id: str, catalog: dict[str, SourceBlock]) -> TaskDraft:
    data = choice.model_dump(mode="json")
    for index, criterion in enumerate(data["criteria"], 1):
        criterion["id"] = f"{task_id}_C{index}"
        criterion["task_id"] = task_id
        criterion["requirement_quote"] = _get(catalog, criterion.pop("requirement_source_id"), "question")
        criterion["sources"] = [{"source": "reference_answer", "quote": _get(catalog, key, "reference_answer")}
                                 for key in criterion.pop("reference_source_ids")]
    return TaskDraft.model_validate_json(json.dumps({"task_id": task_id, **data}, ensure_ascii=False))
