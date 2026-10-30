"""Evidence selection and explicit dependency contracts for D/E/P/application."""
from typing import Annotated, Literal
import re
from pydantic import Field, create_model
from .._core.core import StrictModel

WEIGHT=Annotated[int,Field(ge=1,le=10)]
SHORT=Annotated[str,Field(min_length=1,max_length=400)]
ISSUES=Annotated[list[SHORT],Field(max_length=3)]

APPLICATION_PROMPT='''B3 APPLICATION: chọn câu nguồn chứa KẾT QUẢ cần đạt của tình huống.
Mỗi criteria có kind=APPLICATION, source_ids chứa đúng MỘT mã R, weight 1..10.
Code lấy nguyên văn câu đó làm tiêu chí và mức đạt tối đa, giữ kết quả, đơn vị,
điều kiện. Không thay kết quả bằng chỉ dẫn chung 'áp dụng đúng công thức'.
Nếu đề hỏi tính tiền thì chọn câu có số tiền cuối cùng; nếu hỏi xử lý tình huống
thì chọn câu có quyết định/hành động cụ thể. Chọn đủ kết quả độc lập được hỏi,
không chọn lại cùng mã. Không yêu cầu trình bày cách tính nếu đề chỉ hỏi kết quả.
Nếu đáp án chỉ nêu phương pháp nhưng thiếu kết quả, hoặc kết quả sai/mâu thuẫn,
ghi issues để rà soát. Không tự sửa đáp án hay bịa kết quả. issues=[] nếu đủ.'''

DEFINITION_PROMPT='''B3 DEFINITION: chọn các câu nguồn định nghĩa đúng khái niệm trong selected_task.quote.
Mỗi criteria chỉ có kind, source_ids chứa đúng MỘT mã R, và weight 1..10.
Code dùng nguyên văn câu nguồn làm kiến thức cần chấm; không trả claim hoặc chỉ dẫn
"nêu rõ/giải thích đầy đủ". Chọn đủ ý trong phạm vi task, không chọn câu chỉ nói
đối tượng khác. Một câu nguồn không được chọn hai lần. Một câu có nhiều mệnh đề
vẫn là một tiêu chí đầy đủ, không tự chia điểm một phần khi chưa có ranh giới.
issues=[] nếu đủ thông tin, ghi lỗi cụ thể nếu đáp án thiếu/mâu thuẫn.'''

EXPLANATION_PROMPT='''B3 EXPLANATION: trích từng quan hệ nguyên nhân -> kết quả từ đáp án.
Mỗi criteria có cause và effect; mỗi trường là {source_id, quote}.
quote phải là đoạn NGUYÊN VĂN liên tiếp trong đúng source_id, có đủ chủ thể và giữ
phủ định/điều kiện. Không diễn đạt lại. conditions là các đoạn trích điều kiện nếu cần.
Code tự lấy hợp các nguồn của nguyên nhân, kết quả và điều kiện; không trả source_ids.
Mỗi tiêu chí là một mối nối rõ, không gộp cả chuỗi A -> B -> C rồi chấm lại A -> B.
Có thể tách A -> B và B -> C; không lặp hai tiêu chí với cùng cặp đoạn nguyên nhân,
kết quả. Không chọn cùng đoạn làm cả nguyên nhân và kết quả. Không suy ra quan hệ
chỉ vì hai ý cùng xuất hiện; cần đáp án hỗ trợ quan hệ đó. weight 1..10.
issues=[] nếu đủ thông tin, nếu không hãy nêu lỗi cụ thể.'''

PROCEDURE_PROMPT='''B3 PROCEDURE phần 1: chọn các câu nguồn mô tả các bước cần thực hiện.
Mỗi criteria chỉ có kind=PROCEDURE, source_ids chứa đúng MỘT mã R và weight 1..10.
Chọn các bước liên quan đến selected_task, tối đa 8, không lặp mã R. Giữ thứ tự
trình bày của đáp án. Code lấy nguyên văn câu nguồn làm action, giữ cả điều kiện
"chỉ khi/chỉ sau". Chưa trả quan hệ trước/sau; phần tiếp theo sẽ xử lý riêng.
Nếu một câu nguồn gộp nhiều bước không thể chấm rõ thì ghi issues, không tự bịa bước.
issues=[] nếu không có vấn đề.'''

DEPENDENCY_PROMPT='''B3 PROCEDURE phần 2: xác định quan hệ phụ thuộc bắt buộc giữa các bước.
steps chứa ID S1, S2... và action nguyên văn đáp án. after là object có đúng các ID đó.
after[S2]=[S1] nghĩa bước S2 CHỈ được thực hiện sau bước S1, KHÔNG phải số thứ tự S2.
Bước không có tiền đề trong steps dùng []. Không bước nào phụ thuộc vào chính nó.
Chỉ nối phụ thuộc được đáp án hỗ trợ; không ép các bước độc lập thành chuỗi.
Không tạo vòng lặp. Điều kiện nằm trong action vẫn phải giữ khi chấm.
issues=[] nếu đủ thông tin, nêu vấn đề cụ thể nếu không xác định được.'''


def contract_for(kind,sources):
    SourceID=Literal[tuple(sources)]
    fields=dict(kind=(Literal[kind],...),weight=(WEIGHT,...))
    if kind in {'DEFINITION','PROCEDURE','APPLICATION'}:
        fields['source_ids']=(Annotated[list[SourceID],Field(min_length=1,max_length=1)],...)
    elif kind=='EXPLANATION':
        Span=create_model('EvidenceSpan',__base__=StrictModel,source_id=(SourceID,...),quote=(SHORT,...))
        fields.update(cause=(Span,...),effect=(Span,...),conditions=(Annotated[list[Span],Field(max_length=3)],...))
    else:raise ValueError('Unsupported grounded contract')
    Item=create_model(kind.title()+'GroundedCriterion',__base__=StrictModel,**fields)
    return create_model('GroundedTaskCriteria',__base__=StrictModel,
        criteria=(Annotated[list[Item],Field(min_length=1,max_length=8)],...),issues=(ISSUES,...))


def selected_rows(choice,sources):
    data=choice.model_dump(mode='json')
    if data['issues']:raise ValueError('Task issues: '+'; '.join(data['issues']))
    rows=data['criteria']
    if not rows:raise ValueError('Empty criteria')
    ids=[x['source_ids'][0] for x in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Repeated selected reference sentence')
    if any(x not in sources for x in ids):raise ValueError('Unknown reference source')
    return rows


def resolve_span(span,sources):
    sid=span['source_id']
    if sid not in sources:raise ValueError('Unknown reference source')
    words=span['quote'].split()
    if not words:raise ValueError('Blank evidence quote')
    matches=list(re.finditer(r'\s+'.join(re.escape(w) for w in words),sources[sid],re.IGNORECASE))
    matches=[m for m in matches if
        (m.start()==0 or not(sources[sid][m.start()-1].isalnum() and sources[sid][m.start()].isalnum())) and
        (m.end()==len(sources[sid]) or not(sources[sid][m.end()-1].isalnum() and sources[sid][m.end()].isalnum()))]
    if len(matches)!=1:raise ValueError('Evidence quote must identify one exact span in '+sid)
    m=matches[0]
    return dict(source_id=sid,quote=sources[sid][m.start():m.end()],start=m.start(),end=m.end())


def overlap(a,b):
    return a['source_id']==b['source_id'] and max(a['start'],b['start'])<min(a['end'],b['end'])


def grounded_data(kind,choice,sources):
    data=choice.model_dump(mode='json')
    if data['issues']:raise ValueError('Task issues: '+'; '.join(data['issues']))
    if kind in {'DEFINITION','APPLICATION'}:
        rows=selected_rows(choice,sources)
        criteria=[dict(x,claim=sources[x['source_ids'][0]]) for x in rows]
        if kind=='APPLICATION':
            for item in criteria:
                item.update(rule='Đối chiếu kết quả, đơn vị và điều kiện với đáp án: '+item['claim']+
                    ' Chấp nhận kết quả tương đương; không bắt buộc cách trình bày nếu đề không yêu cầu.',partial=None)
        return dict(criteria=criteria,issues=[])
    if kind!='EXPLANATION':raise ValueError('Procedure requires its dependency stage')
    rows=[];edges=[]
    for item in data['criteria']:
        cause=resolve_span(item['cause'],sources);effect=resolve_span(item['effect'],sources)
        conditions=[resolve_span(x,sources) for x in item['conditions']]
        if overlap(cause,effect):raise ValueError('CAUSE_EFFECT_SPAN_OVERLAP: select distinct causal endpoints')
        if any(overlap(cause,c) and overlap(effect,e) for c,e in edges):
            raise ValueError('OVERLAPPING_CAUSAL_CREDIT: two criteria reuse the same endpoint spans')
        edges.append((cause,effect))
        rows.append(dict(kind=kind,weight=item['weight'],cause=cause['quote'],effect=effect['quote'],
            conditions=[x['quote'] for x in conditions],
            source_ids=list(dict.fromkeys(x['source_id'] for x in [cause,effect]+conditions))))
    return dict(criteria=rows,issues=[])


def procedure_steps(selection,sources):
    return [dict(id=f'S{i}',action=sources[row['source_ids'][0]],source_ids=row['source_ids'],weight=row['weight'])
            for i,row in enumerate(selected_rows(selection,sources),1)]


def dependency_contract(steps):
    fields={}
    for step in steps:
        other=[s['id'] for s in steps if s['id']!=step['id']]
        Type=Annotated[list[Literal[tuple(other)]],Field(max_length=len(other))] if other else Annotated[list[str],Field(max_length=0)]
        fields[step['id']]=(Type,...)
    Links=create_model('StepDependencies',__base__=StrictModel,**fields)
    return create_model('ProcedureDependencies',__base__=StrictModel,after=(Links,...),issues=(ISSUES,...))


def materialize_procedure(task,steps,dependencies,sources):
    from .generator import materialize_data
    dep=dependencies.model_dump(mode='json')
    if dep['issues']:raise ValueError('Dependency issues: '+'; '.join(dep['issues']))
    ids={s['id']:i for i,s in enumerate(steps,1)}
    if set(dep['after'])!=set(ids):raise ValueError('Dependency steps do not match selection')
    rows=[]
    for s in steps:
        parents=dep['after'][s['id']]
        if len(set(parents))!=len(parents) or s['id'] in parents or any(x not in ids for x in parents):
            raise ValueError('Invalid dependency endpoint')
        rows.append(dict(kind='PROCEDURE',action=s['action'],source_ids=s['source_ids'],weight=s['weight'],
                         after=[ids[x] for x in parents],conditions=[],partial=None))
    return materialize_data(task,dict(criteria=rows,issues=[]),sources)
