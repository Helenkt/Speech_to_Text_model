from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import database
from app.services.rubric_contract import digest
from app.services.teacher_review import _evaluation_complete


STATUSES = {"met": 1.0, "partial": 0.5, "missing": 0.0, "contradicted": 0.0}


def rubric_hash(question: dict[str, Any]) -> str:
    snapshot = question.get("rubric_snapshot")
    if snapshot:
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("contract"), dict):
            raise ValueError("Malformed rubric snapshot")
        contract = snapshot["contract"]
        criteria = contract.get("criteria")
        if (not isinstance(criteria, list) or not criteria
                or any(not isinstance(item, dict) or not isinstance(item.get("claim"), str)
                       or not item["claim"].strip() for item in criteria)):
            raise ValueError("Malformed rubric snapshot criteria")
        claims = [item["claim"] for item in criteria]
        weights = {item["claim"]: item.get("weight") for item in criteria}
        if (len(set(claims)) != len(claims) or claims != question["key_points"]
                or weights != question.get("key_point_weights")
                or any(isinstance(w, bool) or not isinstance(w, (int, float))
                       or not math.isfinite(w) or w <= 0 for w in weights.values())
                or digest(contract) != snapshot.get("sha256")):
            raise ValueError("Rubric snapshot content does not match its integrity hash")
        return snapshot["sha256"]
    return digest({
        "points": question["key_points"], "weights": question.get("key_point_weights", {}),
        "reference": question.get("reference_answer", ""),
    })


def save_point_labels(database_path: Path, *, answer_id: int, teacher_id: int,
                      transcript_source: str, expected_transcript_sha256: str,
                      expected_rubric_sha256: str, labels: list[dict[str, Any]],
                      annotation_mode: str) -> dict[str, Any]:
    if transcript_source not in {"original", "strong"} or annotation_mode not in {"independent", "assisted"}:
        raise ValueError("Invalid transcript source or annotation mode")
    with database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """SELECT a.question_json, a.answer_text, t.review_transcript
               FROM interview_answers a LEFT JOIN speech_transcriptions t
               ON t.transcription_id = a.transcription_id WHERE a.answer_id = ?""", (answer_id,),
        ).fetchone()
        if not row:
            raise ValueError("Answer not found")
        text = row["answer_text"] if transcript_source == "original" else row["review_transcript"]
        if not text:
            raise ValueError("Requested transcript is not available")
        question = json.loads(row["question_json"])
        transcript_sha, rubric_sha = digest(text), rubric_hash(question)
        if transcript_sha != expected_transcript_sha256 or rubric_sha != expected_rubric_sha256:
            raise ValueError("Transcript or rubric changed; reload the labeling task")
        points = question["key_points"]
        if len(labels) != len(points) or len({item.get("point") for item in labels}) != len(points):
            raise ValueError("Label every rubric point exactly once")
        atomic = bool(question.get("rubric_snapshot"))
        validated = []
        for item in labels:
            point, status, quote = item.get("point"), item.get("status"), item.get("evidence_quote", "")
            if set(item) != {"point", "status", "evidence_quote"} or point not in points or status not in STATUSES:
                raise ValueError("Invalid point label")
            if atomic and status == "partial":
                raise ValueError("Split atomic criteria instead of assigning arbitrary half-credit")
            if not isinstance(quote, str) or len(quote) > 8000:
                raise ValueError("Invalid evidence quote")
            if status != "missing" and (not quote.strip() or quote not in text):
                raise ValueError("Teacher evidence must be an exact transcript excerpt")
            if status == "missing" and quote:
                raise ValueError("Missing evidence must have an empty quote")
            validated.append({**item, "credit": STATUSES[status]})
        cursor = connection.execute(
            """INSERT INTO grading_labels (answer_id, transcript_source, transcript_sha256,
               rubric_sha256, labels_json, annotation_mode, reviewed_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (answer_id, transcript_source, transcript_sha, rubric_sha, json.dumps(validated, ensure_ascii=False),
             annotation_mode, teacher_id, datetime.now(timezone.utc).isoformat()),
        )
        return {"label_id": cursor.lastrowid, "answer_id": answer_id,
                "changes_final_grade": False, "annotation_mode": annotation_mode}


def labeling_task(database_path: Path, answer_id: int, transcript_source: str = "original") -> dict[str, Any]:
    if transcript_source not in {"original", "strong"}:
        raise ValueError("Invalid transcript source")
    with database(database_path) as connection:
        row = connection.execute(
            """SELECT a.question_json, a.answer_text, t.review_transcript
               FROM interview_answers a LEFT JOIN speech_transcriptions t
               ON t.transcription_id = a.transcription_id WHERE a.answer_id = ?""", (answer_id,),
        ).fetchone()
    if not row:
        raise ValueError("Answer not found")
    question = json.loads(row["question_json"])
    text = row["answer_text"] if transcript_source == "original" else row["review_transcript"]
    if not text:
        raise ValueError("Requested transcript is not available")
    # Do not expose the AI score in this task. Independent annotation is still a teacher declaration.
    return {"answer_id": answer_id, "transcript_source": transcript_source, "transcript": text,
            "transcript_sha256": digest(text), "rubric_sha256": rubric_hash(question),
            "question": question, "annotation_mode_options": ["independent", "assisted"]}


def export_corpus(database_path: Path) -> dict[str, Any]:
    with database(database_path) as connection:
        rows = connection.execute(
            """SELECT l.*, a.question_json, a.answer_text, s.user_id, s.session_id,
                      t.review_transcript, t.audio_sha256
               FROM grading_labels l JOIN interview_answers a ON a.answer_id = l.answer_id
               JOIN interview_sessions s ON s.session_id = a.session_id
               LEFT JOIN speech_transcriptions t ON t.transcription_id = a.transcription_id
               ORDER BY l.label_id DESC""",
        ).fetchall()
    samples, latest, students, reviewers = {}, set(), {}, {}
    stale = 0
    for row in rows:
        text = row["answer_text"] if row["transcript_source"] == "original" else row["review_transcript"]
        question = json.loads(row["question_json"])
        if digest(text) != row["transcript_sha256"] or rubric_hash(question) != row["rubric_sha256"]:
            stale += 1
            continue
        key = (row["answer_id"], row["transcript_source"], row["reviewed_by"])
        if key in latest:
            continue
        latest.add(key)
        student = row["user_id"] if row["user_id"] is not None else row["session_id"]
        students.setdefault(student, f"student-{len(students) + 1}")
        reviewers.setdefault(row["reviewed_by"], f"rater-{len(reviewers) + 1}")
        sample_id = f"{row['answer_id']}:{row['transcript_source']}:{row['transcript_sha256'][:16]}"
        sample = samples.setdefault(sample_id, {
            "sample_id": sample_id, "question_id": question["uid"], "student_group": students[student],
            "student_identity_verified": row["user_id"] is not None,
            "subject": question["subject"], "language": question["language"], "answer": text,
            "answer_hash": row["transcript_sha256"], "rubric_sha256": row["rubric_sha256"],
            "question": question, "data_origin": "student_audio" if row["audio_sha256"] else "unverified",
            "split": "unassigned", "labels": [],
        })
        sample["labels"].append({"label_id": row["label_id"], "reviewer": reviewers[row["reviewed_by"]],
                                "mode": row["annotation_mode"], "created_at": row["created_at"],
                                "points": json.loads(row["labels_json"])})
    return {"schema_version": "grading-corpus-v1", "samples": list(samples.values()),
            "stale_labels_excluded": stale, "contains_personal_text": True,
            "notice": "Pseudonyms are local to this export. Free text may contain personal data. No audio or paths exported."}


def review_triage(database_path: Path, limit: int = 1000, *,
                  expected_review_cache_key: str | None = None) -> dict[str, Any]:
    with database(database_path) as connection:
        rows = connection.execute(
            """SELECT a.answer_id, a.question_json, a.assessment_json, a.review_required,
                      a.evaluator, a.review_ai_score, a.review_ai_at,
                      a.review_ai_evaluation_json, t.metadata_json,
                      t.review_metadata_json, t.review_processed_at
               FROM interview_answers a LEFT JOIN speech_transcriptions t
               ON t.transcription_id = a.transcription_id WHERE a.reviewed_at IS NULL
               ORDER BY a.answer_id DESC LIMIT ?""", (limit + 1,),
        ).fetchall()
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows[:limit]:
        question = json.loads(row["question_json"])
        reasons = []

        def parse_field(field: str, expected_type: type, default: Any) -> Any:
            try:
                value = json.loads(row[field]) if row[field] else default
                if not isinstance(value, expected_type):
                    raise ValueError("Unexpected stored JSON type")
                return value
            except (TypeError, ValueError):
                reasons.append(("invalid_review_data", "", "Reprocess malformed stored assessment data"))
                return default

        assessments = parse_field("assessment_json", list, [])
        metadata = parse_field("metadata_json", dict, {})
        strong = parse_field("review_ai_evaluation_json", dict, {})
        strong_metadata = parse_field("review_metadata_json", dict, {})
        strong_current = bool(
            expected_review_cache_key and row["review_processed_at"] and row["review_ai_at"]
            and row["review_ai_score"] is not None
            and strong_metadata.get("review_cache_key") == expected_review_cache_key
            and _evaluation_complete(strong, question.get("key_points", []), row["review_ai_score"])
        )
        if strong_current:
            assessments = strong["point_assessments"]
        elif strong:
            reasons.append(("stale_reanalysis", "", "Rerun strong STT/grading before using the old AI assessment"))
        metrics = metadata.get("metrics")
        quality_score = metrics.get("quality_score") if isinstance(metrics, dict) else None
        if quality_score is not None and (isinstance(quality_score, bool)
                or not isinstance(quality_score, (float, int)) or not math.isfinite(quality_score)):
            reasons.append(("invalid_review_data", "", "Reprocess malformed stored assessment data"))
            quality_score = None
        if metadata.get("quality_warnings") or (quality_score is not None and quality_score < 0.55):
            reasons.append(("stt_quality", "", "Check saved audio / strong STT before grading"))
        for item in assessments:
            if not isinstance(item, dict) or not isinstance(item.get("point"), str):
                reasons.append(("invalid_review_data", "", "Reprocess malformed stored assessment data"))
                continue
            if item.get("needs_review") or item.get("status") == "unresolved":
                reason = "model_disagreement" if item.get("evidence_verification") else "unresolved_meaning"
                reasons.append((reason, item["point"], "Inspect original evidence; clarify an atomic rubric if recurring"))
        if not reasons and row["review_required"]:
            reasons.append(("teacher_decision", "", "Teacher may accept verified AI result or grade manually"))
        if not reasons and int(digest(str(row["answer_id"]))[:8], 16) % 10 == 0:
            reasons.append(("confident_audit", "", "Audit sample; confidence is not proof of correctness"))
        for reason, point, action in set(reasons):
            key = (rubric_hash(question), point, reason)
            group = groups.setdefault(key, {"rubric_sha256": key[0], "point": point, "reason": reason,
                                           "recommended_action": action, "answer_ids": []})
            group["answer_ids"].append(row["answer_id"])
    return {"groups": sorted(groups.values(), key=lambda item: (-len(item["answer_ids"]), item["reason"], item["point"])),
            "scanned_answers": min(len(rows), limit), "truncated": len(rows) > limit,
            "changes_grades": False, "audit_sampling": "deterministic 10% of otherwise unflagged answers"}


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def evaluate_predictions(samples: list[dict[str, Any]], predictions: list[dict[str, Any]],
                         *, minimum_blind_samples: int = 100) -> dict[str, Any]:
    """Measure independent point labels. Never enable automatic grading from this report."""
    if minimum_blind_samples < 1:
        raise ValueError("minimum_blind_samples must be positive")
    predicted = {row["sample_id"]: row for row in predictions}
    if len(predicted) != len(predictions) or len({s["sample_id"] for s in samples}) != len(samples):
        raise ValueError("Duplicate sample IDs")
    groups: dict[str, set[str]] = defaultdict(set)
    excluded, scored, issues = [], [], []
    known_ids = {sample["sample_id"] for sample in samples}
    if set(predicted) - known_ids:
        issues.append("unknown_predictions")
    for sample in samples:
        sample_id = sample["sample_id"]
        for field in ("question_id", "student_group", "answer_hash"):
            if not sample.get(field):
                raise ValueError(f"Missing leakage group: {field}")
            groups[f"{field}:{sample[field]}"].add(sample.get("split", "unassigned"))
        independent = [label for label in sample.get("labels", []) if label.get("mode") == "independent"]
        reviewers = [label["reviewer"] for label in independent]
        if len(set(reviewers)) != len(reviewers):
            raise ValueError("Duplicate independent rater")
        if not independent:
            excluded.append({"sample_id": sample_id, "reason": "no_independent_human_labels"})
            continue
        question = sample["question"]
        points = question["key_points"]
        if not points or len(points) != len(set(points)):
            raise ValueError("Benchmark rubric points must be non-empty and unique")
        if digest(sample["answer"]) != sample["answer_hash"] or rubric_hash(question) != sample["rubric_sha256"]:
            raise ValueError("Corpus transcript/rubric content hash mismatch")
        normalized = []
        for label in independent:
            labels = label["points"]
            if len(labels) != len(points) or {item["point"] for item in labels} != set(points):
                raise ValueError("Incomplete or duplicate human point labels")
            if any(item["status"] not in STATUSES or item["credit"] != STATUSES[item["status"]] for item in labels):
                raise ValueError("Inconsistent human credit")
            normalized.append({item["point"]: (item["status"], item["credit"]) for item in labels})
        if any(labels != normalized[0] for labels in normalized[1:]):
            excluded.append({"sample_id": sample_id, "reason": "human_rater_disagreement"})
            continue
        prediction = predicted.get(sample_id)
        if prediction is None:
            excluded.append({"sample_id": sample_id, "reason": "missing_prediction"})
            continue
        if prediction.get("answer_hash") != sample["answer_hash"] or prediction.get("rubric_sha256") != sample["rubric_sha256"]:
            raise ValueError("Prediction transcript/rubric mismatch")
        assessments = prediction.get("point_assessments", [])
        if len(assessments) != len(points) or {item.get("point") for item in assessments} != set(points):
            raise ValueError("Prediction must cover all points exactly once")
        weights = [float(question.get("key_point_weights", {}).get(point, 1)) for point in points]
        if any(not math.isfinite(w) or w <= 0 for w in weights):
            raise ValueError("Invalid benchmark rubric weight")
        expected = normalized[0]
        actual = {}
        review = bool(prediction.get("review_required") or prediction.get("score_provisional"))
        for item in assessments:
            status = item["status"]
            if status not in {*STATUSES, "unresolved"}:
                raise ValueError("Invalid predicted status")
            actual[item["point"]] = STATUSES.get(status, 0.0)
            review = review or bool(item.get("needs_review") or status == "unresolved")
        gold_score = 100 * sum(w * expected[p][1] for p, w in zip(points, weights)) / sum(weights)
        score = 100 * sum(w * actual[p] for p, w in zip(points, weights)) / sum(weights)
        reported_score = float(prediction.get("score", score))
        if not math.isfinite(reported_score) or abs(reported_score - score) > 0.11:
            raise ValueError("Reported score does not match point credits")
        scored.append({"sample_id": sample_id, "subject": sample["subject"], "language": sample["language"],
                       "absolute_error": abs(score - gold_score), "review": review,
                       "false_credit": sum(actual[p] > expected[p][1] for p in points),
                       "unfair_loss": sum(actual[p] < expected[p][1] for p in points),
                       "point_count": len(points), "two_raters": len(independent) >= 2,
                       "blind_real": sample.get("split") == "blind_test" and sample.get("data_origin") == "student_audio"
                                     and sample.get("student_identity_verified") is True})
    leakage = [key for key, splits in groups.items() if len(splits) > 1]
    if leakage:
        issues.append("cross_split_leakage")
    if excluded:
        issues.append("excluded_or_missing_samples")
    blind = [row for row in scored if row["blind_real"]]
    if len(blind) < minimum_blind_samples:
        issues.append("insufficient_real_blind_samples")
    if not blind or not any(row["two_raters"] for row in blind):
        issues.append("no_double_rated_blind_subset")

    def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
        automatic = [row for row in rows if not row["review"]]
        return {"sample_count": len(rows), "mae": _mean([row["absolute_error"] for row in rows]),
                "review_rate": _mean([float(row["review"]) for row in rows]),
                "automatic_count": len(automatic),
                "automatic_mae": _mean([row["absolute_error"] for row in automatic]),
                "false_credit_points": sum(row["false_credit"] for row in rows),
                "unfair_loss_points": sum(row["unfair_loss"] for row in rows),
                "automatic_false_credit_points": sum(row["false_credit"] for row in automatic),
                "automatic_unfair_loss_points": sum(row["unfair_loss"] for row in automatic)}

    strata = sorted({(row["subject"], row["language"]) for row in scored})
    return {"schema_version": "grading-quality-v1", "overall": metrics(scored), "blind_real": metrics(blind),
            "by_subject_language": [{"subject": subject, "language": language,
                 **metrics([r for r in scored if r["subject"] == subject and r["language"] == language])}
                for subject, language in strata], "exclusions": excluded, "leakage_groups": leakage,
            "validation_issues": issues, "eligible_for_release_review": not issues,
            "production_certified": False, "automatically_changes_model_or_threshold": False,
            "notice": "Eligibility checks dataset hygiene, not model quality. Set acceptance limits before looking at blind results."}
