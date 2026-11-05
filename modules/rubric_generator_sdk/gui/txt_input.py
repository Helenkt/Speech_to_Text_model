import unicodedata
from pathlib import Path

def load_txt(path):
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    fields = {}
    key = None
    for line in lines:
        head, sep, body = line.partition(":")
        label = unicodedata.normalize("NFC", head.strip()).casefold()
        if sep and label in ("câu hỏi", "câu trả lời"):
            if label in fields or (key is None and label != "câu hỏi"):
                raise ValueError("Mỗi tệp cần đúng một câu hỏi, sau đó là một câu trả lời.")
            key = label
            fields[key] = [body.lstrip()]
        elif key is not None:
            fields[key].append(line)
        elif line.strip():
            raise ValueError("Dòng đầu tiên phải bắt đầu bằng 'câu hỏi:'.")
    vals = ["\n".join(fields.get(k, [])).strip() for k in ("câu hỏi", "câu trả lời")]
    if not all(vals):
        raise ValueError("Cần nhập đủ nội dung sau 'câu hỏi:' và 'câu trả lời:'.")
    return dict(question=vals[0], reference_answer=vals[1], total_units=1000, units_per_point=100)
