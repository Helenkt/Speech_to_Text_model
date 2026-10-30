"""Conservative request-axis constraints and one-owner definition source routing.

These are structural constraints. They do not certify semantic source relevance.
"""
import re
from typing import Annotated, Literal
from pydantic import Field, create_model
from .._core.core import StrictModel

DEFINITION_ALLOCATION_PROMPT='''B2 nguồn định nghĩa: phân mỗi câu nguồn cho đúng MỘT yêu cầu định nghĩa.
definition_tasks liệt kê các vế độc lập. owners có đúng một khóa cho mỗi source ID.
Giá trị là ID task nhận kiến thức của câu đó, hoặc UNUSED nếu không phải kiến thức
định nghĩa cần chấm ở các task này. Chọn theo đối tượng mà câu đang định nghĩa,
không chỉ vì câu chứa từ thuộc đối tượng khác. Không phân toàn bộ đáp án cho mọi task.
Mỗi task phải có nguồn đủ để trả lời. Nếu câu gộp kiến thức không thể tách cho hai
task, hoặc không đủ nguồn cho task nào, ghi issues để chuyển rà soát.
Một câu có thể chứa nhiều thuộc tính của cùng một đối tượng. Các task khác loại
có thể dùng lại nguồn làm bối cảnh; owners chỉ phân điểm giữa các task định nghĩa.
Chỉ trả owners và issues, không viết giải thích dài.'''

SCOPED_COMPARISON_PROMPT='''B3 COMPARISON: chỉ đối chiếu đúng requested_aspects.
Mỗi phương diện đúng một criterion, aspect phải dùng đúng tên trong requested_aspects.
Không thêm phương diện khác dù đáp án có nói tới. Nội dung từng side.value chỉ trả
lời phương diện đó; không dùng một ý ngoài phạm vi rồi gắn nhãn aspect hợp lệ.
Chọn source_ids hỗ trợ đủ các phía, giữ điều kiện/phủ định. Không chấm lại định nghĩa
đã thuộc task khác. Nếu phương diện gồm nhiều ý, sides phải phủ đủ các ý trong đó.
Mỗi criterion có kind=COMPARISON, source_ids, weight 1..10, aspect, sides gồm subject,
value, negated; conditions; partial=null nếu chưa có ranh giới điểm thành phần rõ.
negated=true chỉ khi phủ định chính value; không đảo nghĩa một value đã chứa 'không'.
issues=[] khi đủ dữ liệu; nếu thiếu nội dung cần so sánh thì nêu vấn đề cụ thể.'''


def comparison_axes(task):
    """Only explicit trailing 'về/theo' lists, never inferred from answer content."""
    if 'COMPARISON' not in task['labels']:
        return []
    from .generator import protected_positions
    quote=task['quote'];protected=protected_positions(quote)
    matches=[m for m in re.finditer(r'\b(?:về|theo)\s+',quote,re.I)
             if not any(protected[m.start():m.end()])]
    if not matches:return []
    text=quote[matches[0].end():].strip().rstrip('.?!;').strip()
    if not text:raise ValueError('EMPTY_COMPARISON_SCOPE')
    protected=protected_positions(text);parts=[];start=0
    for m in re.finditer(r'\s+và\s+|\s*;\s*',text,re.I):
        if any(protected[m.start():m.end()]):continue
        parts.append(text[start:m.start()].strip());start=m.end()
    parts.append(text[start:].strip())
    if any(not p for p in parts) or len(parts)>8 or len({p.casefold() for p in parts})!=len(parts):
        raise ValueError('AMBIGUOUS_COMPARISON_SCOPE: inspect the explicit aspect list')
    return parts


def validate_comparison_axes(task,data):
    axes=comparison_axes(task)
    if axes:
        actual=[x['aspect'] for x in data['criteria']]
        if len(actual)!=len(axes) or set(actual)!=set(axes):
            raise ValueError('COMPARISON_SCOPE_MISMATCH: exactly one criterion per requested aspect')


def definition_tasks(tasks):
    return [t for t in tasks if 'DEFINITION' in t['labels']]


def allocation_contract(tasks,sources):
    ids=[t['id'] for t in definition_tasks(tasks)]
    if len(ids)<2:raise ValueError('Source allocation needs multiple definition tasks')
    Owner=Literal[tuple(ids+['UNUSED'])]
    Owners=create_model('DefinitionSourceOwners',__base__=StrictModel,
                        **{sid:(Owner,...) for sid in sources})
    return create_model('DefinitionAllocation',__base__=StrictModel,owners=(Owners,...),
        issues=(Annotated[list[Annotated[str,Field(min_length=1,max_length=400)]],Field(max_length=3)],...))


def allocated_sources(choice,tasks,sources):
    data=choice.model_dump(mode='json')
    if data['issues']:raise ValueError('Definition source issues: '+'; '.join(data['issues']))
    if set(data['owners'])!=set(sources):raise ValueError('Incomplete definition source allocation')
    result={t['id']:{} for t in definition_tasks(tasks)}
    for sid,owner in data['owners'].items():
        if owner=='UNUSED':continue
        if owner not in result:raise ValueError('Unknown definition owner')
        # Reject an obvious swap only when a direct 'X là ...' head matches
        # exactly one requested target/suffix. Unresolved aliases need review.
        head=re.match(r'\s*(.{1,160}?)\s+là\s+',sources[sid],re.I)
        if head:
            def words(text):return ' '.join(re.findall(r'\w+',text.casefold()))
            subject=words(head.group(1));matches=[]
            for task in definition_tasks(tasks):
                command=re.match(r'\s*(?:(?:hãy|vui lòng|bạn hãy|anh/chị hãy)\s+)?định nghĩa\s+(.+)',task['quote'],re.I)
                if command:
                    target=words(command.group(1))
                    if target==subject or target.endswith(' '+subject):matches.append(task['id'])
            if len(matches)==1 and owner!=matches[0]:
                raise ValueError('DEFINITION_SUBJECT_OWNER_MISMATCH: '+sid+' names the target of '+matches[0])
        result[owner][sid]=sources[sid]
    if any(not refs for refs in result.values()):
        raise ValueError('Definition task has no assigned source; review reference coverage')
    return result
