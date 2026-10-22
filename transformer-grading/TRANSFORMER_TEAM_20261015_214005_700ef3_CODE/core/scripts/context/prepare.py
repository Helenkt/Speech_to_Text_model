from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import unicodedata

from app.context.contracts import LABELS, SCHEMA_VERSION


def canonical(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def normalize(row: dict, source: str, demo: bool) -> dict:
    for field in ("question", "criterion", "reference_claim", "student_answer", "answer_id", "question_id"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError(f"{source}: thiếu {field}")
    relation = row.get("relation_label")
    coverage = row.get("coverage_level")
    if relation in {"supported", "met"}:
        label = "partial" if coverage == "partial" else "met"
    elif relation in LABELS:
        label = relation
    else:
        raise ValueError(f"{source}: nhãn không hợp lệ {relation}")
    maximum = float(row["max_points"])
    points = float(row["teacher_points"])
    if not all(math.isfinite(x) for x in (maximum, points)) or not 0 <= points <= maximum or maximum <= 0:
        raise ValueError(f"{source}: điểm không hợp lệ")
    quote = str(row.get("evidence_quote") or "")
    if quote and quote not in row["student_answer"]:
        raise ValueError(f"{source}: evidence_quote không nguyên văn")
    if label in {"met", "partial", "contradicted"} and not quote:
        raise ValueError(f"{source}: thiếu dẫn chứng")
    expected = {"met": 1, "partial": 0.5, "missing": 0, "contradicted": 0, "uncertain": 0}[label]
    if abs(points / maximum - expected) > 0.001:
        raise ValueError(f"{source}: nhãn và mức điểm 1/0.5/0 không khớp; cần GV chuẩn hóa")
    origin = row.get("data_origin", "unknown")
    if not demo and (row.get("reviewer_status") != "approved" or origin != "human"):
        raise ValueError(f"{source}: chỉ dùng dữ liệu human/approved, hoặc --demo cho dữ liệu thử")
    group = hashlib.sha256(canonical(row["question"]).encode()).hexdigest()
    return {**row, "label": label, "group": group, "source": source}


def prepare(paths: list[Path], output: Path, *, demo: bool, seed: int = 42) -> dict:
    records, rejected = [], []
    original_split_labels = Counter()
    seen = {}
    for path in paths:
        for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            original_split_labels[(str(raw.get("split", "none")), str(raw.get("relation_label")))] += 1
            source = f"{path.name}:{line_no}"
            try:
                row = normalize(raw, source, demo)
            except (ValueError, KeyError, TypeError) as exc:
                rejected.append({"source": source, "reason": str(exc)})
                continue
            identity = tuple(canonical(row[k]) for k in ("question", "criterion", "reference_claim", "student_answer"))
            if identity in seen:
                if seen[identity] != row["label"]:
                    raise ValueError(f"Conflicting labels for duplicate input at {source}")
                continue
            seen[identity] = row["label"]
            records.append(row)
    if not records:
        raise ValueError("Không có dữ liệu hợp lệ. Dữ liệu đi kèm là synthetic: thêm --demo để thử pipeline.")
    # Use all reference claims for a question as teacher context, consistently across answers.
    references = defaultdict(set)
    for row in records:
        references[row["group"]].add(row["reference_claim"])
    for row in records:
        row["reference_answer"] = " ".join(sorted(references[row["group"]]))
    groups = sorted({row["group"] for row in records})
    if len(groups) < 10:
        raise ValueError("Cần ít nhất 10 nhóm câu hỏi để tách train/val/test")
    random.Random(seed).shuffle(groups)
    n_test = max(1, round(len(groups) * 0.15))
    n_val = max(1, round(len(groups) * 0.15))
    assignment = {g: "test" if i < n_test else "val" if i < n_test + n_val else "train" for i, g in enumerate(groups)}
    # Check duplicate answers across groups: connecting them is safer than leaking them.
    answer_groups = defaultdict(set)
    for row in records:
        answer_groups[canonical(row["student_answer"])].add(row["group"])
    crossing = [gs for gs in answer_groups.values() if len({assignment[g] for g in gs}) > 1]
    if crossing:
        raise ValueError("Câu trả lời trùng qua các nhóm khác split. Gộp nhóm paraphrase/duplicate trước khi train.")
    output.mkdir(parents=True, exist_ok=True)
    files, summary = {}, {}
    for split in ("train", "val", "test"):
        selected = [r for r in records if assignment[r["group"]] == split]
        content = "".join(json.dumps({**r, "split": split}, ensure_ascii=False) + "\n" for r in selected)
        (output / f"{split}.jsonl").write_bytes(content.encode("utf-8"))
        files[f"{split}.jsonl"] = hashlib.sha256(content.encode()).hexdigest()
        summary[split] = {"rows": len(selected), "questions": len({r["group"] for r in selected}),
                          "labels": dict(Counter(r["label"] for r in selected))}
    report = {"schema_version": SCHEMA_VERSION, "demo_only": demo, "seed": seed,
              "split_policy": "canonical-question-group-70-15-15; old split ignored",
              "summary": summary, "files_sha256": files, "rejected": rejected,
              "original_split_labels": {f"{s}/{l}": n for (s, l), n in original_split_labels.items()},
              "warnings": ["Dữ liệu tổng hợp không chứng minh độ chính xác trên sinh viên thật.",
                           "Các câu hỏi diễn đạt khác nhưng cùng mẫu/khái niệm cần được nhóm thủ công khi mở rộng dữ liệu."]}
    (output / "dataset_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", default=["data/training/rubric_labels", "data/context/context_cases.draft.jsonl"])
    parser.add_argument("--output", default="data/context/prepared")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    paths = []
    for value in args.input:
        p = Path(value)
        paths.extend(sorted(p.glob("*.jsonl")) if p.is_dir() else [p])
    report = prepare(paths, Path(args.output), demo=args.demo, seed=args.seed)
    print(json.dumps({"demo_only": report["demo_only"], "splits": report["summary"],
                      "rejected": len(report["rejected"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
