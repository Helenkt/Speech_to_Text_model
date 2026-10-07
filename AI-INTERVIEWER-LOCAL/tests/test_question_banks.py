from collections import Counter

from app.services.question_importer import parse_question_bank


def test_supplied_demo_banks_are_structurally_valid(project_root):
    banks = {}
    for language in ("vi", "en"):
        path = project_root / "data" / f"question_bank_{language}.json"
        questions, digest = parse_question_bank(path.read_bytes(), filename=path.name)
        banks[language] = questions

        assert len(questions) == 900
        assert len(digest) == 64
        assert len({item["uid"] for item in questions}) == 900
        assert len({item["subject"] for item in questions}) == 4
        assert Counter(item["difficulty"] for item in questions) == {
            "Easy": 300,
            "Medium": 300,
            "Hard": 300,
        }
        assert all(len(item["key_points"]) >= 1 for item in questions)

    assert {item["id"] for item in banks["vi"]} == {
        item["id"] for item in banks["en"]
    }
