from tools.finetune_rubricguard import augment_training, metrics, normalize, split_rows


def synthetic_rows():
    return [{"question_id": f"topic{topic}-q{index}", "source": f"topic{topic}.json",
             "student_answer": f"answer {topic} {index} {label}",
             "reference_claim": f"claim {topic} {index}",
             "criterion": f"criterion {topic} {index}", "label": label}
            for topic in range(4) for index in range(10) for label in range(3)]


def test_split_keeps_question_answers_and_claims_together():
    rows = synthetic_rows()
    splits = split_rows(rows, 123)
    assert {name: len(data) for name, data in splits.items()} == {
        "train": 72, "validation": 24, "test": 24}
    for field in ("question_id", "student_answer", "reference_claim"):
        sets = [{normalize(row[field]) for row in data} for data in splits.values()]
        assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])


def test_augmentation_uses_only_train_claims_and_preserves_originals():
    rows = [{"question_id": "q1", "source": "topic.json", "label": 0,
             "reference_claim": "Stack là LIFO", "criterion": "Stack LIFO",
             "student_answer": "Stack hoạt động theo LIFO."}]
    augmented = augment_training(rows)
    assert rows[0] in augmented
    assert any(row["label"] == 2 and row["student_answer"] == "Stack không phải là LIFO"
               for row in augmented)
    assert {row["reference_claim"] for row in augmented} == {"Stack là LIFO", "Stack LIFO"}


def test_metrics_explicitly_counts_wrong_answers_rewarded_as_met():
    result = metrics([0, 0, 1, 1, 2, 2], [0, 0, 1, 1, 2, 0])
    assert result["false_met_on_wrong"] == 0.5
    assert result["contradiction_recall"] == 0.5
    assert result["confusion_matrix"][2][0] == 1
