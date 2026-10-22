from __future__ import annotations

from app.context.contracts import LABELS


def classification_metrics(truth: list[str], predicted: list[str]) -> dict:
    if len(truth) != len(predicted) or not truth:
        raise ValueError("Need nonempty equally sized truth/prediction arrays")
    matrix = {a: {b: 0 for b in LABELS} for a in LABELS}
    for a, b in zip(truth, predicted):
        matrix[a][b] += 1
    per_label = {}
    for label in LABELS:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        pcount = sum(matrix[x][label] for x in LABELS)
        precision = tp / pcount if pcount else 0
        recall = tp / support if support else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    negatives = sum(t in {"contradicted", "missing"} for t in truth)
    return {"accuracy": sum(a == b for a, b in zip(truth, predicted)) / len(truth),
            "macro_f1": sum(x["f1"] for x in per_label.values()) / len(LABELS),
            "false_met_on_wrong_rate": sum(t in {"contradicted", "missing"} and p == "met" for t, p in zip(truth, predicted)) / negatives if negatives else None,
            "per_label": per_label, "confusion_matrix": matrix}
