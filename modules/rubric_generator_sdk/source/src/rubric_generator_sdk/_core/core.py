"""Validated contracts and deterministic scoring. No semantic judgment in this file."""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class QuestionType(str, Enum):
    DEFINITION = "DEFINITION"
    COMPARISON = "COMPARISON"
    EXPLANATION = "EXPLANATION"
    PROCEDURE = "PROCEDURE"
    ENUMERATION = "ENUMERATION"
    APPLICATION = "APPLICATION"
    ANALYSIS = "ANALYSIS"


Identifier = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]
Text = Annotated[str, Field(min_length=1)]
PositiveUnits = Annotated[int, Field(ge=1)]


class InputSpec(StrictModel):
    question: Annotated[str, Field(min_length=1, max_length=6000)]
    reference_answer: Annotated[str, Field(min_length=1, max_length=6000)]
    question_id: Identifier = "Q001"
    total_units: Annotated[int, Field(ge=100, le=100000)] = 1000
    units_per_point: Literal[100] = 100
    task_budgets_units: dict[Identifier, PositiveUnits] | None = None

    @model_validator(mode="after")
    def valid_text(self):
        if not self.question.strip() or not self.reference_answer.strip():
            raise ValueError("Question and reference answer must not be blank")
        return self


class Task(StrictModel):
    id: Identifier
    text: Text
    question_quote: Text
    primary_type: QuestionType
    secondary_types: list[QuestionType]
    reference_quotes: list[Text]
    importance: Annotated[int, Field(ge=1, le=10)]
    coverage: Literal["COMPLETE", "INCOMPLETE", "CONFLICT"]
    coverage_note: Text


class Plan(StrictModel):
    tasks: Annotated[list[Task], Field(max_length=5)]
    needs_review: bool
    concerns: list[Text]


class SourceQuote(StrictModel):
    source: Literal["question", "reference_answer"]
    quote: Text


class Relation(StrictModel):
    subject: Text
    predicate: Text
    object: Text
    negated: bool
    conditions: list[Text]


class Edge(StrictModel):
    before: Text
    after: Text


class Verification(StrictModel):
    method: Literal["SEMANTIC_ENTAILMENT", "RELATION", "CAUSAL", "DEPENDENCY", "SET_MATCH", "DOMAIN_RULE", "ARGUMENT"]
    relations: list[Relation]
    causal_edges: list[Edge]
    required_steps: list[Text]
    precedence_edges: list[Edge]
    expected_items: list[Text]
    rule_description: str
    argument_requirements: list[Text]


class DraftLevel(StrictModel):
    id: Identifier
    percent: Annotated[int, Field(ge=0, le=100)]
    descriptor: Text


class CriterionDraft(StrictModel):
    id: Identifier
    task_id: Identifier
    fact_key: Identifier
    expected_claim: Text
    requirement_quote: Text
    sources: Annotated[list[SourceQuote], Field(min_length=1)]
    importance: Annotated[int, Field(ge=1, le=10)]
    accepted_meanings: list[Text]
    misconceptions: list[Text]
    evidence_requirement: Text
    verification: Verification
    levels: Annotated[list[DraftLevel], Field(min_length=2, max_length=5)]
    critical: bool


class TaskDraft(StrictModel):
    task_id: Identifier
    criteria: Annotated[list[CriterionDraft], Field(min_length=1, max_length=8)]


class Issue(StrictModel):
    code: Text
    message: Text
    criterion_ids: list[Identifier]


class Audit(StrictModel):
    verdict: Literal["PASS", "REVIEW"]
    issues: list[Issue]

    @model_validator(mode="after")
    def consistent(self):
        if (self.verdict == "PASS") != (len(self.issues) == 0):
            raise ValueError("PASS requires no issues; REVIEW requires an issue")
        return self


class Level(StrictModel):
    id: Identifier
    points_units: Annotated[int, Field(ge=0)]
    descriptor: Text


class Criterion(CriterionDraft):
    max_points_units: PositiveUnits
    levels: Annotated[list[Level], Field(min_length=2, max_length=5)]


class ScoredTask(Task):
    max_points_units: PositiveUnits


class Rubric(StrictModel):
    schema_version: Literal["1.0"]
    rubric_version: Text
    question_id: Identifier
    question: Text
    reference_answer: Text
    question_types: Annotated[list[QuestionType], Field(min_length=1)]
    is_composite: bool
    total_units: PositiveUnits
    units_per_point: Literal[100]
    weight_source: Literal["AUTO_PROPOSED", "TEACHER_CONFIGURED"]
    tasks: Annotated[list[ScoredTask], Field(min_length=1)]
    criteria: Annotated[list[Criterion], Field(min_length=1)]
    policy: Literal["EVIDENCE_REQUIRED_NO_KEYWORD_SCORING_NO_DOUBLE_COUNT_UNCERTAIN_REVIEW"]


def _unique(values, name):
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {name}")


def validate_plan(spec: InputSpec, plan: Plan):
    _unique([t.id for t in plan.tasks], "task ID")
    if not plan.tasks and not plan.needs_review:
        raise ValueError("Empty plan must require review")
    for t in plan.tasks:
        if t.question_quote not in spec.question:
            raise ValueError(f"Question quote not found: {t.id}")
        if any(q not in spec.reference_answer for q in t.reference_quotes):
            raise ValueError(f"Reference quote not found: {t.id}")
        if t.coverage == "COMPLETE" and not t.reference_quotes:
            raise ValueError(f"COMPLETE task has no reference evidence: {t.id}")
        _unique([t.primary_type.value] + [x.value for x in t.secondary_types], "type within task")


def _validate_verification(v: Verification):
    if v.method == "RELATION" and not v.relations:
        raise ValueError("RELATION requires structured relations")
    if v.method == "CAUSAL" and not v.causal_edges:
        raise ValueError("CAUSAL requires a causal edge")
    if v.method == "SET_MATCH" and not v.expected_items:
        raise ValueError("SET_MATCH requires expected items")
    if v.method == "DOMAIN_RULE" and not v.rule_description.strip():
        raise ValueError("DOMAIN_RULE requires a rule description")
    if v.method == "ARGUMENT" and not v.argument_requirements:
        raise ValueError("ARGUMENT requires argument requirements")
    if v.method == "DEPENDENCY":
        if not v.required_steps:
            raise ValueError("DEPENDENCY requires steps")
        _unique(v.required_steps, "step")
        graph = {x: [] for x in v.required_steps}
        for e in v.precedence_edges:
            if e.before not in graph or e.after not in graph:
                raise ValueError("Unknown dependency endpoint")
            graph[e.before].append(e.after)
        seen, active = set(), set()
        def visit(node):
            if node in active:
                raise ValueError("Cyclic dependency graph")
            if node in seen:
                return
            active.add(node)
            for nxt in graph[node]:
                visit(nxt)
            active.remove(node)
            seen.add(node)
        for node in graph:
            visit(node)


def validate_drafts(spec: InputSpec, plan: Plan, drafts: list[TaskDraft]):
    validate_plan(spec, plan)
    if plan.needs_review or not plan.tasks or any(t.coverage != "COMPLETE" for t in plan.tasks):
        raise ValueError("Incomplete or conflicting plan cannot compile")
    _unique([d.task_id for d in drafts], "task draft")
    if {d.task_id for d in drafts} != {t.id for t in plan.tasks}:
        raise ValueError("Draft coverage does not match tasks")
    all_c = [c for d in drafts for c in d.criteria]
    _unique([c.id for c in all_c], "criterion ID")
    _unique([c.fact_key for c in all_c], "scored fact key")
    _unique([" ".join(c.expected_claim.casefold().split()) for c in all_c], "exact scored claim")
    for draft in drafts:
        for c in draft.criteria:
            if c.task_id != draft.task_id:
                raise ValueError("Criterion assigned to wrong task")
            if c.requirement_quote not in spec.question:
                raise ValueError("Requirement quote not found")
            if not any(s.source == "reference_answer" for s in c.sources):
                raise ValueError("Criterion needs reference-answer evidence")
            for s in c.sources:
                if s.quote not in getattr(spec, s.source):
                    raise ValueError("Source quote not found")
            _unique([l.id for l in c.levels], "level ID")
            percents = [l.percent for l in c.levels]
            if percents != sorted(set(percents)) or percents[0] != 0 or percents[-1] != 100:
                raise ValueError("Levels must ascend uniquely from 0 to 100")
            _validate_verification(c.verification)


def allocate(total: int, weights: list[int]) -> list[int]:
    """Hamilton allocation, stable tie-breaking, integer hundredths of a point."""
    if type(total) is not int or total <= 0 or not weights or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError("Allocation needs positive integers")
    denominator = sum(weights)
    parts = [total * w // denominator for w in weights]
    order = sorted(range(len(weights)), key=lambda i: (-(total * weights[i] % denominator), i))
    for i in order[:total - sum(parts)]:
        parts[i] += 1
    if any(p <= 0 for p in parts):
        raise ValueError("Budget too small for all criteria")
    return parts


def compile_rubric(spec: InputSpec, plan: Plan, drafts: list[TaskDraft], audit: Audit) -> Rubric:
    if audit.verdict != "PASS":
        raise ValueError("Semantic audit requires review")
    return compile_candidate(spec, plan, drafts)


def compile_candidate(spec: InputSpec, plan: Plan, drafts: list[TaskDraft]) -> Rubric:
    """Assemble a structurally valid draft. This grants no semantic approval."""
    validate_drafts(spec, plan, drafts)
    if spec.task_budgets_units is not None:
        budgets = spec.task_budgets_units
        if set(budgets) != {t.id for t in plan.tasks} or sum(budgets.values()) != spec.total_units:
            raise ValueError("Teacher budgets must cover tasks and sum to total")
    else:
        budgets = dict(zip([t.id for t in plan.tasks], allocate(spec.total_units, [t.importance for t in plan.tasks])))
    tasks = [ScoredTask(**t.model_dump(), max_points_units=budgets[t.id]) for t in plan.tasks]
    criteria = []
    by_task = {d.task_id: d for d in drafts}
    for t in tasks:
        cs = by_task[t.id].criteria
        maxima = allocate(t.max_points_units, [c.importance for c in cs])
        for c, maximum in zip(cs, maxima):
            levels = [Level(id=l.id, points_units=(maximum * l.percent + 50) // 100, descriptor=l.descriptor) for l in c.levels]
            if len({l.points_units for l in levels}) != len(levels):
                raise ValueError("Budget resolution collapses distinct scoring levels")
            data = c.model_dump(exclude={"levels"})
            criteria.append(Criterion(**data, levels=levels, max_points_units=maximum))
    labels = sorted({x for t in tasks for x in [t.primary_type] + t.secondary_types}, key=lambda x: x.value)
    rubric = Rubric(schema_version="1.0", rubric_version="1.0.0", question_id=spec.question_id,
        question=spec.question, reference_answer=spec.reference_answer, question_types=labels,
        is_composite=len(tasks) > 1, total_units=spec.total_units, units_per_point=100,
        weight_source="TEACHER_CONFIGURED" if spec.task_budgets_units is not None else "AUTO_PROPOSED",
        tasks=tasks, criteria=criteria,
        policy="EVIDENCE_REQUIRED_NO_KEYWORD_SCORING_NO_DOUBLE_COUNT_UNCERTAIN_REVIEW")
    validate_rubric(rubric)
    return rubric


def validate_rubric(rubric: Rubric):
    """Check structural invariants again when importing an existing rubric."""
    spec = InputSpec(question=rubric.question, reference_answer=rubric.reference_answer,
        question_id=rubric.question_id, total_units=rubric.total_units)
    plan = Plan(tasks=[Task(**t.model_dump(exclude={"max_points_units"})) for t in rubric.tasks], needs_review=False, concerns=[])
    drafts = []
    for t in rubric.tasks:
        cs = []
        for c in rubric.criteria:
            if c.task_id != t.id:
                continue
            data = c.model_dump(exclude={"max_points_units", "levels"})
            # Original percentages are not needed when importing; validate points separately.
            data["levels"] = [DraftLevel(id=l.id, percent=(100 if i == len(c.levels)-1 else 0 if i == 0 else i), descriptor=l.descriptor) for i,l in enumerate(c.levels)]
            cs.append(CriterionDraft(**data))
        drafts.append(TaskDraft(task_id=t.id, criteria=cs))
    validate_drafts(spec, plan, drafts)
    if {c.task_id for c in rubric.criteria} != {t.id for t in rubric.tasks}:
        raise ValueError("Unknown or uncovered rubric task")
    if sum(t.max_points_units for t in rubric.tasks) != rubric.total_units:
        raise ValueError("Task budgets do not sum to total")
    if sum(c.max_points_units for c in rubric.criteria) != rubric.total_units:
        raise ValueError("Criterion budgets do not sum to total")
    for t in rubric.tasks:
        if sum(c.max_points_units for c in rubric.criteria if c.task_id == t.id) != t.max_points_units:
            raise ValueError("Task criterion sum mismatch")
    for c in rubric.criteria:
        points = [l.points_units for l in c.levels]
        if points != sorted(set(points)) or points[0] != 0 or points[-1] != c.max_points_units:
            raise ValueError("Invalid criterion points")
    expected_types = {x for t in rubric.tasks for x in [t.primary_type] + t.secondary_types}
    if set(rubric.question_types) != expected_types or len(rubric.question_types) != len(expected_types):
        raise ValueError("Question types disagree with tasks")
    if rubric.is_composite != (len(rubric.tasks) > 1):
        raise ValueError("Composite flag disagrees with task count")


def digest(rubric: Rubric) -> str:
    return hashlib.sha256(json.dumps(rubric.model_dump(mode="json"), ensure_ascii=False,
        sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class Evaluation(StrictModel):
    criterion_id: Identifier
    status: Literal["SUPPORTED", "PARTIAL", "MISSING", "CONTRADICTED", "UNRELATED", "UNCERTAIN"]
    level_id: Identifier | None
    evidence_quotes: list[Text]
    explanation: Text


class EvaluationBatch(StrictModel):
    rubric_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    evaluations: list[Evaluation]


def score(rubric: Rubric, student_answer: str, batch: EvaluationBatch) -> dict:
    """Only sums already verified levels. Does not implement an LLM/NLI grader."""
    validate_rubric(rubric)
    if batch.rubric_sha256 != digest(rubric):
        raise ValueError("Rubric digest mismatch")
    _unique([e.criterion_id for e in batch.evaluations], "evaluation")
    if {e.criterion_id for e in batch.evaluations} != {c.id for c in rubric.criteria}:
        raise ValueError("Evaluations must cover every criterion exactly once")
    lookup = {e.criterion_id: e for e in batch.evaluations}
    lower = upper = 0
    details, pending = [], []
    for c in rubric.criteria:
        e = lookup[c.id]
        if any(q not in student_answer for q in e.evidence_quotes):
            raise ValueError("Student evidence quote not found")
        if e.status in {"SUPPORTED", "PARTIAL", "CONTRADICTED", "UNRELATED"} and not e.evidence_quotes:
            raise ValueError("Positive or content-based judgment requires evidence")
        if e.status == "UNCERTAIN":
            if e.level_id is not None:
                raise ValueError("UNCERTAIN cannot select a score level")
            upper += c.max_points_units
            pending.append(c.id)
            details.append({"criterion_id": c.id, "status": e.status, "points_units": None})
            continue
        if e.status == "MISSING" and e.evidence_quotes:
            raise ValueError("MISSING must not cite affirmative evidence")
        levels = {l.id: l.points_units for l in c.levels}
        if e.level_id not in levels:
            raise ValueError("Unknown level")
        points = levels[e.level_id]
        if e.status == "SUPPORTED" and points != c.max_points_units:
            raise ValueError("SUPPORTED must select full points")
        if e.status == "PARTIAL" and not 0 < points < c.max_points_units:
            raise ValueError("PARTIAL must select an explicit partial level")
        if e.status in {"MISSING", "CONTRADICTED", "UNRELATED"} and points != 0:
            raise ValueError("Missing, false or unrelated evidence must score zero")
        lower += points
        upper += points
        details.append({"criterion_id": c.id, "status": e.status, "points_units": points})
    return {"status": "REVIEW" if pending else "SCORED", "score_units": None if pending else lower,
        "score": None if pending else lower / 100, "score_interval": [lower / 100, upper / 100],
        "max_score": rubric.total_units / 100, "pending_criteria": pending,
        "rubric_sha256": digest(rubric), "details": details}
