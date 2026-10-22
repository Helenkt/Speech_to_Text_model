"""Closed-form course assertions, checked against the criterion, not a knowledge cache."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.fact_guard import FactCheck, plain_text, split_clauses


VERSION = "course-facts-v1"


@dataclass(frozen=True)
class CourseFact:
    kind: str
    subject: str
    value: str


def parse_course_fact(text: str, *, implicit_subject: str | None = None) -> CourseFact | None:
    value = plain_text(text).strip(" .")
    value = re.sub(r"^con\s+", "", value)
    value = re.sub(r"^(?:(?:theo\s+)?(?:em|toi)\s+(?:hieu|nghi)\s+(?:la\s+)?|theo em\s+(?:la\s+)?)", "", value)
    value = value.replace("thuoc tinh/phuong thuc", "thuoc tinh va phuong thuc")
    value = re.sub(r"\blifo\s*\(last in, first out\)", "lifo", value)
    value = re.sub(r"\bfifo\s*\(first in, first out\)", "fifo", value)
    value = re.sub(r"\blifo: phan tu them vao sau cung duoc lay ra dau tien\b", "lifo", value)
    value = re.sub(r"\bfifo: phan tu them vao dau tien duoc lay ra dau tien\b", "fifo", value)
    # Grammar is deliberately closed: a matching fragment inside a longer claim is not proof.
    discipline = re.fullmatch(
        r"(?:(?:a|the)\s+)?(stack|ngan xep|queue|hang doi)\s+(?:la\s+(?:cau truc\s+)?|"
        r"(?:hoat dong\s+)?theo\s+(?:nguyen (?:tac|ly)\s+)?|dung\s+|su dung\s+|"
        r"uses?\s+|follows?\s+|operates on the\s+|is\s+)?"
        r"(lifo|fifo|vao sau ra truoc|vao truoc ra truoc)"
        r"(?:\s*\((lifo|fifo)\))?(?:\s+principle)?", value)
    if discipline:
        subject, order, abbreviation = discipline.groups()
        subject = {"ngan xep": "stack", "hang doi": "queue"}.get(subject, subject)
        order = {"vao sau ra truoc": "lifo", "vao truoc ra truoc": "fifo"}.get(order, order)
        if abbreviation and abbreviation != order:
            return None
        return CourseFact("access_order", subject, order)

    explicit_order = re.fullmatch(
        r"(stack|ngan xep|queue|hang doi)\s+(?:se\s+)?(?:lay|lay ra)\s+"
        r"(?:cai|phan tu)\s+(?:duoc\s+)?(?:them\s+|dua\s+|bo\s+)?vao\s+"
        r"(dau tien|truoc|sau cung|sau)\s+(?:duoc\s+)?(?:lay\s+)?ra truoc", value)
    if explicit_order:
        subject = {"ngan xep": "stack", "hang doi": "queue"}.get(explicit_order[1], explicit_order[1])
        return CourseFact("access_order", subject, "fifo" if explicit_order[2] in {"dau tien", "truoc"} else "lifo")

    if implicit_subject:
        description = re.fullmatch(
            r"(?:em hinh dung no nhu chong (?:dia|sach),\s*)?"
            r"(?:cai|phan tu)\s+(moi\s+)?(?:dat len|dua vao|bo vao|them vao|vao)\s*"
            r"(sau cung|sau|dau tien|truoc)?\s+(?:thi|se duoc|duoc|se)\s+"
            r"(?:nhac|lay)\s+ra\s+truoc(?:,\s*giong (?:mot\s+)?chong (?:sach|dia))?", value)
        if description:
            new, position = description.groups()
            if (new and not position) or (not new and position):
                return CourseFact("access_order", implicit_subject,
                                  "lifo" if new or position in {"sau", "sau cung"} else "fifo")

    value = value.replace("lay cai tren cung ra va bo no khoi chong", "lay ra tu tren cung")
    operations = re.fullmatch(
        r"(?:hai thao tac co ban (?:nhat )?la\s+)?push\s*(?:\(|la\s+|de\s+)?"
        r"(them|lay|xoa)\s+(?:phan tu\s+)?(?:vao|len|ra tu|tu)\s+(dinh|tren cung)\)?"
        r"(?:\s*,?\s*(?:va|con|,)\s+|,\s*)pop\s*(?:\(|la\s+|de\s+)?"
        r"(lay ra|lay va xoa|lay va bo|lay|them)\s+(?:phan tu\s+)?(?:ra tu|tu|o|tren|len|vao)\s+(dinh|tren cung)\)?", value)
    if operations:
        first, _, second, _ = operations.groups()
        return CourseFact("stack_operations", "push/pop", first + ":" + ("remove" if second != "them" else "add"))

    inheritance = re.fullmatch(
        r"(lop con|lop cha|child class|parent class)\s+"
        r"(?:thua huong|ke thua|nhan(?: lai)?|tai su dung|su dung lai|dung lai|lay lai|inherits?)\s+(?:(?:cac|nhung)\s+)?"
        r"(?:(?:bien\s+)?thuoc tinh va (?:phuong thuc|ham)|attributes and methods)\s+"
        r"(?:(?:cua|tu|from)\s+)?(lop con|lop cha|child class|parent class)"
        r"(?:\s+da co,\s*nen khong phai viet lai het|,\s*do phai viet trung code)?", value)
    if inheritance:
        aliases = {"lop con": "child", "child class": "child", "lop cha": "parent", "parent class": "parent"}
        child, parent = map(aliases.get, inheritance.groups())
        if child != parent:
            return CourseFact("inheritance_direction", "attributes_and_methods", child + "<-" + parent)

    extension = re.fullmatch(
        r"(?:nhung theo em\s+)?lop con\s+"
        r"(?:(co the)\s+|(?:bat buoc giu nguyen tat ca hanh vi,\s*)?(khong duoc)\s+)"
        r"(?:bo sung|them chuc nang rieng)\s+(?:hoac|hay)\s+ghi de(?:\s+(?:hanh vi rieng|phuong thuc))?", value)
    if extension:
        return CourseFact("extension_permission", "child_class", "allowed" if extension[1] else "forbidden")

    null_value = re.fullmatch(
        r"null\s+(?:theo em\s+)?(?:dai dien cho\s+(?:gia tri\s+)?|chinh la\s+|la\s+)"
        r"(khong xac dinh/chua co du lieu|chua co du lieu hoac chua xac dinh duoc gia tri|"
        r"minh chua biet hoac chua co thong tin o o do, chu khong phai so khong hay chuoi rong|"
        r"so 0|so khong|chuoi rong)(?:,\s*tuc da co mot gia tri cu the)?", value)
    if null_value:
        meaning = null_value[1]
        meaning = "unknown" if meaning.startswith(("khong xac dinh", "chua co", "minh chua biet")) else (
            "zero" if meaning in {"so 0", "so khong"} else meaning)
        return CourseFact("null_meaning", "null", meaning)

    predicate = re.fullmatch(
        r"(?:(?:phai|khi kiem tra cot thi|muon loc thi)\s+)?dung is null\s*(?:/|hoac)\s*is not null,\s*"
        r"(?:khong dung\s+'?(?:=|bang) null'?|khong so sanh bang dau bang voi null)(?:\s+de kiem tra)?", value)
    if predicate:
        return CourseFact("null_predicate", "sql_null_check", "is_predicates_not_equals")
    if re.fullmatch(r"muon tim no thi cu viet cot bang null, khong can is null hay is not null", value):
        return CourseFact("null_predicate", "sql_null_check", "equals_not_is_predicates")

    nullability = re.fullmatch(
        r"(?:gia tri\s+(?:cua\s+)?)?(khoa chinh|primary key)\s+"
        r"(khong duoc|khong the|khong cho phep|duoc phep|cho phep|co the|"
        r"cannot be|can be|must not be|allows?|does not allow)\s+(?:la\s+)?null", value)
    if nullability:
        denial = nullability[2] in {"khong duoc", "khong the", "khong cho phep", "cannot be", "must not be", "does not allow"}
        return CourseFact("nullability", "primary_key", "forbidden" if denial else "allowed")

    gradient = re.fullmatch(
        r"(?:cac\s+)?(?:tham so|trong so|parameters?|weights?)\s+"
        r"(?:duoc\s+|are\s+|is\s+)?(?:cap nhat|updated)\s+"
        r"(?:theo\s+(?:huong\s+)?|in\s+the\s+)?"
        r"(nguoc|cung|opposite|same)\s+(?:huong\s+)?(?:voi\s+|as\s+|to\s+)?"
        r"(?:the\s+)?gradient(?:\s+direction)?", value)
    if gradient:
        direction = "opposite" if gradient[1] in {"nguoc", "opposite"} else "same"
        return CourseFact("update_direction", "parameters", direction)
    return None


def fact_examples(fact: CourseFact, language: str) -> list[str]:
    if fact.kind == "access_order":
        if language == "vi":
            order = "vào sau ra trước" if fact.value == "lifo" else "vào trước ra trước"
            return [f"{fact.subject.capitalize()} theo {fact.value.upper()}",
                    f"{fact.subject.capitalize()} theo nguyên tắc {order}"]
        return [f"{fact.subject.capitalize()} uses {fact.value.upper()}"]
    # Do not fabricate free-form paraphrases for meanings outside the closed grammar.
    return []


def check_course_point(answer: str, point: str, *, question: dict | None = None) -> FactCheck:
    expected = parse_course_fact(point)
    if expected is None:
        return FactCheck("unknown", 0)
    if re.search(r"['\"\u2018\u2019\u201c\u201d?]", answer):
        return FactCheck("unknown", 0)
    judgments = []
    ambiguous = False
    covered = True
    abstentions = []
    implicit_subject = None
    if question:
        context = plain_text(question.get("question", "") + " " + " ".join(question.get("key_points", [])) + " " + answer)
        subjects = set("stack" if word in {"stack", "ngan xep"} else "queue"
                       for word in re.findall(r"\b(?:stack|ngan xep|queue|hang doi)\b", context))
        if len(subjects) == 1:
            implicit_subject = next(iter(subjects))
    for original in split_clauses(answer):
        clause = plain_text(original).strip()
        if re.search(r"\b(neu|gia su|if|suppose|hypothetical|correction|sua lai|dinh chinh)\b", clause):
            ambiguous = True
            continue
        observed = parse_course_fact(original, implicit_subject=implicit_subject)
        abstention = re.fullmatch(
            r"(?:(?:phan (?:con lai|nay)|hai thao tac ten gi thi|con cach viet dieu kien sql thi)\s+)?"
            r"(?:em|toi)\s+(?:chua|khong)\s+(?:biet|nho|hieu)", clause)
        if abstention:
            abstentions.append(original)
            continue
        covered &= observed is not None
        if observed and (observed.kind, observed.subject) == (expected.kind, expected.subject):
            judgments.append((observed.value == expected.value, original))
        elif observed is None:
            # Never grant credit to one excerpt while silently ignoring an unparsed contrary tail.
            mentions = {
                "access_order": {"stack": r"\b(stack|ngan xep)\b", "queue": r"\b(queue|hang doi)\b"}[expected.subject]
                    if expected.kind == "access_order" else "",
                "inheritance_direction": (r"\b(thua huong|ke thua|nhan|tai su dung|su dung lai|dung lai|"
                                          r"lay lai|inherits?)\b.*\b(thuoc tinh|phuong thuc|ham|attributes|methods)\b"),
                "nullability": r"\b(khoa chinh|primary key)\b",
                "update_direction": r"\b(tham so|trong so|parameters?|weights?)\b",
                "stack_operations": r"\b(push|pop)\b",
                "extension_permission": r"\b(bo sung|ghi de|them chuc nang)\b",
                "null_meaning": r"\bnull\b.*\b(la|dai dien|nghia|meaning|represents?)\b",
                "null_predicate": r"\b(is null|is not null|(?:=|bang) null)\b",
            }
            ambiguous |= bool(re.search(mentions[expected.kind], clause) or
                              re.search(r"\b(nhan dinh (?:nay|do)|phat bieu (?:nay|do)|that (?:claim|statement))\b.*"
                                        r"\b(sai|khong dung|wrong|false)\b", clause))
    if not judgments:
        if covered and abstentions and not ambiguous:
            return FactCheck("missing", .99, "Các mệnh đề đã được đối chiếu; ý này vắng và người trả lời nói chưa nhớ.",
                             abstentions[0], verification_rule=VERSION + ":closed_absence")
        return FactCheck("unknown", 0)
    if ambiguous or len({correct for correct, _ in judgments}) > 1:
        return FactCheck("conflicted", 0, "Phát biểu cùng chủ thể còn mâu thuẫn hoặc chưa rõ phạm vi.",
                         judgments[0][1], verification_rule=VERSION + ":" + expected.kind)
    correct, quote = judgments[0]
    return FactCheck("supported" if correct else "contradicted", .99,
                     "Đối chiếu chủ thể, quan hệ và giá trị với chính mệnh đề rubric.", quote,
                     verification_rule=VERSION + ":" + expected.kind)
