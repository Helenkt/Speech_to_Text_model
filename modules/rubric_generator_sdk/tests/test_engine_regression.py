import copy,json,tempfile,threading,time,unittest

from pathlib import Path

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from rubric_generator_sdk._engine import generator as g

ROOT=Path(__file__).parent

SPEC = g.InputSpec.model_validate_json((ROOT/'sample_input.json').read_text(encoding='utf-8'))

PLAN = dict(tasks=[
    dict(quote='Định nghĩa Stack', labels=['DEFINITION'], weight=4),
    dict(quote='so sánh Stack với Queue về nguyên tắc lấy phần tử và vị trí thêm, lấy phần tử.', labels=['COMPARISON'], weight=6)
], issues=[])

ANCHORED_PLAN = dict(choices={f'T{i}':dict(labels=row['labels'],weight=row['weight']) for i,row in enumerate(PLAN['tasks'],1)},issues=[])

DEFINITION = dict(criteria=[
    dict(kind='DEFINITION', source_ids=['R1'], weight=1),
    dict(kind='DEFINITION', source_ids=['R2'], weight=1)
], issues=[])

COMPARISON = dict(criteria=[
    dict(kind='COMPARISON', aspect='nguyên tắc lấy phần tử', sides=[dict(subject='Stack', value='LIFO', negated=False), dict(subject='Queue', value='FIFO', negated=False)], conditions=[], source_ids=['R2','R4'], weight=1, partial=None),
    dict(kind='COMPARISON', aspect='vị trí thêm, lấy phần tử', sides=[dict(subject='Stack', value='thêm và lấy tại đỉnh', negated=False), dict(subject='Queue', value='thêm cuối, lấy đầu', negated=False)], conditions=[], source_ids=['R3','R5'], weight=1, partial=None)
], issues=[])

CONFIG = dict(model=g.DEFAULT_MODEL, base_url='http://127.0.0.1:11434', timeout=420, num_ctx=4096)

BINDING = dict(test_fixture=True, config=CONFIG, input_sha256=g.sha(SPEC.model_dump(mode='json')))

def plan(data=PLAN, spec=SPEC):
    return g.validate_plan_choice(spec, g.PlanChoice.model_validate_json(json.dumps(data,ensure_ascii=False)))

def materialize(task, data, spec=SPEC):
    sources=g.references(spec)
    if task['labels']==['PROCEDURE'] and data['criteria'] and 'action' in data['criteria'][0]:
        # Final graph compiler is shared by the two-stage production path.
        return g.materialize_data(task,data,sources)
    value=g.task_contract(task,sources).model_validate_json(json.dumps(data,ensure_ascii=False))
    return g.materialize_task(task,value,sources)

def fixture_caller(fail=None):
    def call(base_url,payload,record,save,timeout,progress):
        record.update(request=payload,request_sha256=g.sha(payload))
        name=record['stage']
        if name==fail:
            record.update(status='ERROR',response_text='{"criteria":',error='simulated timeout')
            save();raise TimeoutError('simulated timeout')
        value={'B1_B2':ANCHORED_PLAN,'B3_T1':DEFINITION,'B3_T2':COMPARISON}[name]
        record.update(response_text=json.dumps(value,ensure_ascii=False),status='RECEIVED')
        save();return copy.deepcopy(value)
    return call

class PlanTests(unittest.TestCase):
    def test_two_fields_input_defaults_to_ten_points(self):
        self.assertEqual(SPEC.total_units,1000)
        self.assertEqual(len(plan()),2)
    def test_observed_full_question_scope_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][0]['quote']=SPEC.question
        with self.assertRaisesRegex(ValueError,'OVERLAPPING_TASKS'):plan(bad)
    def test_unrequested_secondary_explanation_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][1]['labels'].append('EXPLANATION')
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_SECONDARY'):plan(bad)
    def test_plan_issues_stop_even_if_they_are_work_instructions(self):
        bad=copy.deepcopy(PLAN);bad['issues']=['Lập danh sách task']
        with self.assertRaisesRegex(ValueError,'Plan issues'):plan(bad)
    def test_omitted_requested_aspect_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][1]['quote']='so sánh Stack với Queue về nguyên tắc lấy phần tử'
        with self.assertRaisesRegex(ValueError,'UNCOVERED'):plan(bad)
    def test_normalization_uses_original_question_text(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][0]['quote']='định   nghĩa Stack'
        self.assertEqual(plan(bad)[0]['quote'],'Định nghĩa Stack')
    def test_invented_question_quote_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][0]['quote']='Định nghĩa Queue'
        with self.assertRaisesRegex(ValueError,'exact question span'):plan(bad)
    def test_same_label_independent_requests(self):
        spec=g.InputSpec(question='Định nghĩa A và định nghĩa B.',reference_answer='A là X. B là Y.')
        data=dict(tasks=[dict(quote='Định nghĩa A',labels=['DEFINITION'],weight=1),dict(quote='định nghĩa B.',labels=['DEFINITION'],weight=1)],issues=[])
        self.assertEqual(len(plan(data,spec)),2)
    def test_multiple_labels_do_not_force_split(self):
        spec=g.InputSpec(question='Phân tích cơ chế A dẫn đến B.',reference_answer='A khiến B vì C.')
        data=dict(tasks=[dict(quote=spec.question,labels=['ANALYSIS','EXPLANATION'],weight=1)],issues=[])
        self.assertEqual(len(plan(data,spec)),1)

class RubricTests(unittest.TestCase):
    def test_composite_sources_totals_and_levels(self):
        tasks=plan();rubric=g.compile_output(SPEC,tasks,[materialize(tasks[0],DEFINITION),materialize(tasks[1],COMPARISON)])
        self.assertTrue(rubric.is_composite)
        self.assertEqual([t.max_points_units for t in rubric.tasks],[400,600])
        self.assertEqual(sum(c.max_points_units for c in rubric.criteria),1000)
        self.assertTrue(all(s.quote in SPEC.reference_answer for c in rubric.criteria for s in c.sources))
        g.validate_rubric(rubric)
    def test_unknown_source_is_rejected(self):
        bad=copy.deepcopy(DEFINITION);bad['criteria'][0]['source_ids']=['R999']
        with self.assertRaises(ValueError):materialize(plan()[0],bad)
    def test_task_issues_block_rubric(self):
        bad=copy.deepcopy(DEFINITION);bad['issues']=['Đáp án thiếu ý.']
        with self.assertRaisesRegex(ValueError,'Task issues'):materialize(plan()[0],bad)
    def test_whitespace_claim_is_rejected(self):
        bad=copy.deepcopy(COMPARISON);bad['criteria'][0]['aspect']='  '
        with self.assertRaises(ValueError):materialize(plan()[1],bad)
    def test_duplicate_claim_is_rejected(self):
        bad=copy.deepcopy(DEFINITION);bad['criteria'].append(bad['criteria'][0])
        tasks=plan()
        with self.assertRaisesRegex(ValueError,'Repeated selected reference'):
            g.compile_output(SPEC,tasks,[materialize(tasks[0],bad),materialize(tasks[1],COMPARISON)])
    def test_one_definition_sentence_cannot_be_selected_twice(self):
        bad=copy.deepcopy(DEFINITION);bad['criteria'][1]['source_ids']=['R1']
        with self.assertRaisesRegex(ValueError,'Repeated selected reference'):materialize(plan()[0],bad)
    def test_atomic_fact_has_no_invented_partial_score(self):
        draft=materialize(plan()[0],DEFINITION)
        self.assertEqual([x.percent for x in draft.criteria[0].levels],[0,100])
    def test_declared_partial_boundary_is_preserved(self):
        bad=copy.deepcopy(COMPARISON)
        bad['criteria'][0]['partial']=dict(percent=50,descriptor='Nêu đúng một phía, thiếu phía còn lại.')
        draft=materialize(plan()[1],bad)
        self.assertEqual([x.percent for x in draft.criteria[0].levels],[0,50,100])
    def test_negation_in_relations_is_preserved(self):
        bad=copy.deepcopy(COMPARISON);bad['criteria'][0]['sides'][1]['negated']=True
        draft=materialize(plan()[1],bad)
        self.assertTrue(draft.criteria[0].verification.relations[1].negated)
    def test_all_seven_types_compile_with_distinct_verification_methods(self):
        rows={
            'DEFINITION':dict(),
            'COMPARISON':dict(aspect='quyền sửa',sides=[dict(subject='A',value='được sửa',negated=False),dict(subject='B',value='được sửa',negated=True)],conditions=[],partial=None),
            'EXPLANATION':dict(cause=dict(source_id='R1',quote='A'),effect=dict(source_id='R1',quote='B'),conditions=[dict(source_id='R1',quote='C')]),
            'PROCEDURE':dict(action='A',after=[],conditions=['B'],partial=None),
            'ENUMERATION':dict(item='A'),
            'APPLICATION':dict(),
            'ANALYSIS':dict(claim='Chọn A',basis='A có B',link='B đáp ứng điều kiện đề.',partial=None)
        }
        methods=set()
        for kind,fields in rows.items():
            with self.subTest(kind=kind):
                spec=g.InputSpec(question='Yêu cầu mẫu.',reference_answer='Đáp án mẫu có A, B và C; 8000 đồng.')
                task=dict(id='T1',quote=spec.question,labels=[kind],weight=1)
                entry=dict(kind=kind,weight=1,**fields)
                if kind!='EXPLANATION':entry['source_ids']=['R1']
                data=dict(criteria=[entry],issues=[])
                draft=materialize(task,data,spec);rubric=g.compile_output(spec,[task],[draft])
                methods.add(rubric.criteria[0].verification.method)
                self.assertEqual(rubric.total_units,1000)
        self.assertEqual(len(methods),7)
    def test_cycle_across_procedure_criteria_is_rejected(self):
        spec=g.InputSpec(question='Trình bày quy trình.',reference_answer='A rồi B.')
        task=dict(id='T1',quote=spec.question,labels=['PROCEDURE'],weight=1)
        data=dict(criteria=[dict(kind='PROCEDURE',source_ids=['R0'],weight=1,action=action,after=after,conditions=[],partial=None)
            for action,after in [('A',[2]),('B',[1])]],issues=[])
        with self.assertRaisesRegex(ValueError,'Cyclic'):materialize(task,data,spec)
    def test_unknown_dependency_is_rejected(self):
        spec=g.InputSpec(question='Trình bày quy trình.',reference_answer='A rồi B.')
        task=dict(id='T1',quote=spec.question,labels=['PROCEDURE'],weight=1)
        data=dict(criteria=[dict(kind='PROCEDURE',source_ids=['R0'],weight=1,action='A',after=[7],conditions=[],partial=None)],issues=[])
        with self.assertRaisesRegex(ValueError,'dependency'):materialize(task,data,spec)

class RegressionV11Tests(unittest.TestCase):
    def test_observed_collapsed_plan_is_rejected_before_criteria(self):
        data=g.read_json(ROOT/'observed_v1_excerpt.json')
        spec=SPEC.model_copy(update={'question':data['classification']['tasks'][0]['quote']})
        with self.assertRaisesRegex(ValueError,'UNSPLIT_INDEPENDENT'):
            plan(data['classification'],spec)
    def test_observed_definition_only_criteria_cannot_enter_comparison_schema(self):
        data=g.read_json(ROOT/'observed_v1_excerpt.json')
        with self.assertRaises(ValueError):materialize(plan()[1],data['generated_criteria'])
    def test_anchored_contract_cannot_omit_second_request(self):
        contract=g.anchored_contract(g.explicit_requests(SPEC.question))
        bad=copy.deepcopy(ANCHORED_PLAN);bad['choices'].pop('T2')
        with self.assertRaises(ValueError):contract.model_validate_json(json.dumps(bad))
    def test_task_kind_is_not_a_union_in_model_schema(self):
        for task in plan():
            schema=g.task_contract(task,g.references(SPEC)).model_json_schema()
            item=schema['properties']['criteria']['items']
            self.assertNotIn('anyOf',item)
            definition=schema['$defs'][item['$ref'].split('/')[-1]]
            self.assertEqual(definition['properties']['kind']['const'],task['labels'][0])
    def test_same_action_is_split_and_different_entities_are_not_special_cased(self):
        for question in ['Định nghĩa Heap và định nghĩa Tree.',
                         'Giải thích X và so sánh X với Y.',
                         'Liệt kê A; đánh giá B.',
                         'Định nghĩa A rồi so sánh A với B.']:
            with self.subTest(question=question):self.assertEqual(len(g.explicit_requests(question)),2)
    def test_object_coordination_and_comparison_axes_are_not_split(self):
        for question in ['So sánh Heap và Tree.',
                         'So sánh A và B về tốc độ và bộ nhớ.',
                         'Định nghĩa A và B.',
                         'Phân tích cơ chế A dẫn đến B.']:
            with self.subTest(question=question):self.assertEqual(g.explicit_requests(question),[])
    def test_quoted_parenthesized_and_nominal_actions_are_not_split(self):
        for question in ['Định nghĩa "đọc và so sánh dữ liệu".',
                         'Giải thích thuật ngữ (định nghĩa A và so sánh B).',
                         'So sánh hai phương pháp định nghĩa và phân tích dữ liệu.',
                         'Giải thích mối liên hệ giữa định nghĩa và so sánh.',
                         'Nếu A đúng thì định nghĩa A và so sánh A với B.']:
            with self.subTest(question=question):self.assertEqual(g.explicit_requests(question),[])
    def test_obvious_primary_kind_conflict_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][1]['labels']=['DEFINITION']
        with self.assertRaisesRegex(ValueError,'PRIMARY_KIND_CONFLICT'):plan(bad)
    def test_unrequested_secondary_comparison_is_rejected(self):
        bad=copy.deepcopy(PLAN);bad['tasks'][0]['labels'].append('COMPARISON')
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_SECONDARY_COMPARISON'):plan(bad)
    def test_omitted_single_letter_entity_is_not_treated_as_filler(self):
        spec=g.InputSpec(question='Định nghĩa A và B.',reference_answer='A là X. B là Y.')
        bad=dict(tasks=[dict(quote='Định nghĩa A',labels=['DEFINITION'],weight=1)],issues=[])
        with self.assertRaisesRegex(ValueError,'UNCOVERED'):plan(bad,spec)
    def test_integration_plan_is_one_task_but_calls_have_fixed_kinds(self):
        spec=g.InputSpec(question='Phân tích cơ chế A dẫn đến B.',reference_answer='A gây B. B đáp ứng điều kiện C.')
        values={
            'B1_B2':dict(choices=dict(T1=dict(labels=['ANALYSIS','EXPLANATION'],weight=1)),issues=[]),
            'B3_T1_ANALYSIS':dict(criteria=[dict(kind='ANALYSIS',claim='A đáp ứng C',basis='B đáp ứng C',link='A tạo B nên đáp ứng C',source_ids=['R1','R2'],weight=1,partial=None)],issues=[]),
            'B3_T1_EXPLANATION':dict(criteria=[dict(kind='EXPLANATION',cause=dict(source_id='R1',quote='A'),effect=dict(source_id='R1',quote='B'),conditions=[],weight=1)],issues=[])
        }
        captured=[]
        def caller(url,payload,record,save,timeout,progress):
            captured.append(payload)
            value=values[record['stage']]
            record.update(request=payload,response_text=json.dumps(value),status='RECEIVED');save()
            return value
        with tempfile.TemporaryDirectory() as d:
            state=g.run(spec,CONFIG,d,dict(test='multilabel'),caller=caller,progress=lambda x:None)
            self.assertEqual(state['status'],'DRAFT_READY')
            self.assertEqual(len(state['rubric']['tasks']),1)
            self.assertFalse(state['rubric']['is_composite'])
            self.assertEqual(len(state['rubric']['question_types']),2)
            self.assertEqual([c['id'] for c in state['rubric']['criteria']],['T1_C1','T1_C2'])
            self.assertEqual(len(captured),3)
            self.assertNotIn('anyOf',captured[-1]['format']['properties']['criteria']['items'])
    def test_failed_second_kind_resumes_only_that_kind(self):
        spec=g.InputSpec(question='Phân tích cơ chế A dẫn đến B.',reference_answer='A gây B. B đáp ứng C.')
        mixed=dict(choices=dict(T1=dict(labels=['ANALYSIS','EXPLANATION'],weight=1)),issues=[])
        analysis=dict(criteria=[dict(kind='ANALYSIS',claim='A phù hợp C',basis='B đáp ứng C',link='A tạo B',source_ids=['R1','R2'],weight=1,partial=None)],issues=[])
        explanation=dict(criteria=[dict(kind='EXPLANATION',cause=dict(source_id='R1',quote='A'),effect=dict(source_id='R1',quote='B'),conditions=[],weight=1)],issues=[])
        def caller(url,payload,record,save,timeout,progress):
            if record['stage']=='B3_T1_EXPLANATION':raise TimeoutError('fixture timeout')
            return mixed if record['stage']=='B1_B2' else analysis
        with tempfile.TemporaryDirectory() as d:
            state=g.run(spec,CONFIG,d,dict(test='multilabel_resume'),caller=caller,progress=lambda x:None)
            self.assertEqual(state['status'],'ERROR')
            retried=[]
            def retry(url,payload,record,save,timeout,progress):
                retried.append(record['stage']);return explanation
            state=g.run(spec,CONFIG,d,dict(test='multilabel_resume'),caller=retry,retry_failed=True,progress=lambda x:None)
            self.assertEqual(state['status'],'DRAFT_READY')
            self.assertEqual(retried,['B3_T1_EXPLANATION'])
    def test_observed_transcript_is_not_sent_to_model(self):
        with tempfile.TemporaryDirectory() as d:
            state=g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller(),progress=lambda x:None)
            requests=json.dumps([x['request'] for x in state['calls']],ensure_ascii=False)
            self.assertNotIn('USER_PASTED_EXCERPT',requests)
            self.assertNotIn('expected_score',requests)
            self.assertNotIn('80.985',requests)
    def test_observed_plan_shape_stops_pipeline_after_first_call(self):
        observed=g.read_json(ROOT/'observed_v1_excerpt.json')['classification']
        calls=[]
        def caller(url,payload,record,save,timeout,progress):
            calls.append(record['stage'])
            record.update(response_text=json.dumps(observed),status='RECEIVED');save()
            return observed
        with tempfile.TemporaryDirectory() as d:
            state=g.run(SPEC,CONFIG,d,BINDING,caller=caller,progress=lambda x:None)
            self.assertEqual(state['status'],'NEEDS_REVIEW')
            self.assertEqual(calls,['B1_B2'])
            self.assertIsNone(state['rubric'])
            self.assertEqual(state['steps'],{})
    def test_definition_only_response_in_comparison_is_saved_and_rejected(self):
        good=fixture_caller()
        def caller(url,payload,record,save,timeout,progress):
            if record['stage']=='B3_T2':
                record.update(response_text=json.dumps(DEFINITION),status='RECEIVED');save()
                return DEFINITION
            return good(url,payload,record,save,timeout,progress)
        with tempfile.TemporaryDirectory() as d:
            state=g.run(SPEC,CONFIG,d,BINDING,caller=caller,progress=lambda x:None)
            self.assertEqual(state['status'],'NEEDS_REVIEW')
            self.assertEqual(set(state['steps']),{'B1_B2','B3_T1'})
            self.assertEqual(state['calls'][-1]['status'],'REJECTED')
            self.assertEqual(json.loads(state['calls'][-1]['response_text']),DEFINITION)
            self.assertIsNone(state['rubric'])

class RequestLabelSchemaV12Tests(unittest.TestCase):
    def test_both_stack_requests_have_only_the_requested_label_in_schema(self):
        requests=g.planning_requests(SPEC.question)
        contract=g.anchored_contract(requests)
        schema=contract.model_json_schema()
        for request,expected in zip(requests,['DEFINITION','COMPARISON']):
            policy=g.request_label_policy(request['quote'])
            self.assertEqual(policy['allowed_labels'],[expected])
            fields=schema['$defs']['Labels_'+request['id']]['properties']['labels']
            self.assertEqual(fields['items']['const'],expected)
            self.assertEqual(fields['minItems'],1);self.assertEqual(fields['maxItems'],1)
    def test_extra_explanation_cannot_validate_for_either_request(self):
        # Synthetic variants of the logged V11 error; its raw response was not supplied.
        contract=g.anchored_contract(g.planning_requests(SPEC.question))
        for task_id in ['T1','T2']:
            with self.subTest(task_id=task_id):
                bad=copy.deepcopy(ANCHORED_PLAN)
                bad['choices'][task_id]['labels'].append('EXPLANATION')
                with self.assertRaises(ValueError):contract.model_validate_json(json.dumps(bad))
    def test_replacing_primary_with_explanation_is_rejected_by_schema(self):
        bad=copy.deepcopy(ANCHORED_PLAN);bad['choices']['T1']['labels']=['EXPLANATION']
        with self.assertRaises(ValueError):
            g.anchored_contract(g.planning_requests(SPEC.question)).model_validate_json(json.dumps(bad))
    def test_standalone_requests_use_the_same_label_constraints(self):
        cases={'Định nghĩa Heap.':'DEFINITION','So sánh A và B.':'COMPARISON',
            'Giải thích vì sao X gây Y.':'EXPLANATION','Trình bày các bước gửi phiếu.':'PROCEDURE',
            'Liệt kê ba trường dữ liệu.':'ENUMERATION','Áp dụng đơn giá để tính phí.':'APPLICATION',
            'Đánh giá độ phù hợp của A.':'ANALYSIS'}
        for question,kind in cases.items():
            with self.subTest(kind=kind):
                requests=g.planning_requests(question)
                self.assertEqual(len(requests),1)
                self.assertEqual(g.request_label_policy(question)['allowed_labels'],[kind])
                value=g.anchored_contract(requests).model_validate_json(json.dumps(
                    dict(choices=dict(T1=dict(labels=[kind],weight=1)),issues=[])))
                spec=g.InputSpec(question=question,reference_answer='Đáp án mẫu.')
                self.assertEqual(len(g.validate_plan_choice(spec,g.materialize_anchored_plan(value,requests))),1)
    def test_integrated_causal_analysis_still_allows_two_labels(self):
        question='Phân tích cơ chế A dẫn đến B.'
        requests=g.planning_requests(question)
        self.assertEqual(g.request_label_policy(question)['allowed_labels'],['ANALYSIS','EXPLANATION'])
        value=g.anchored_contract(requests).model_validate_json(json.dumps(
            dict(choices=dict(T1=dict(labels=['ANALYSIS','EXPLANATION'],weight=1)),issues=[])))
        self.assertEqual(len(g.materialize_anchored_plan(value,requests).tasks),1)
    def test_mechanism_as_an_object_does_not_add_explanation(self):
        for question,kind in [('Định nghĩa cơ chế X.','DEFINITION'),('So sánh cơ chế X với Y.','COMPARISON')]:
            self.assertEqual(g.request_label_policy(question)['allowed_labels'],[kind])
    def test_quoted_terms_do_not_inject_secondary_labels(self):
        self.assertEqual(g.request_label_policy('Định nghĩa "giải thích và so sánh".')['allowed_labels'],['DEFINITION'])
    def test_explicit_no_explanation_is_respected_by_label_policy(self):
        for question in ['Định nghĩa A, không cần giải thích.','Phân tích cơ chế A, không cần giải thích.']:
            self.assertNotIn('EXPLANATION',g.request_label_policy(question)['allowed_labels'])
    def test_ambiguous_noun_or_conditional_request_uses_model_planner(self):
        for question in ['So sánh phương pháp định nghĩa và phân tích dữ liệu.',
                         'Nếu A đúng thì định nghĩa A và so sánh A với B.',
                         'Hệ thống cần phản ứng thế nào khi mất kết nối?']:
            self.assertEqual(g.planning_requests(question),[])
    def test_no_topic_or_case_id_is_used_to_choose_labels(self):
        for a,b in [('Heap','Tree'),('bản nháp','bản đã gửi'),('Foo','Bar')]:
            requests=g.planning_requests(f'Định nghĩa {a} và so sánh {a} với {b}.')
            self.assertEqual([g.request_label_policy(r['quote'])['allowed_labels'] for r in requests],
                [['DEFINITION'],['COMPARISON']])
    def test_completed_run_records_label_policies_and_passes_schema_to_ollama(self):
        with tempfile.TemporaryDirectory() as d:
            state=g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller(),progress=lambda x:None)
            self.assertEqual(state['status'],'DRAFT_READY')
            self.assertEqual(state['decomposition']['request_label_policies']['T1']['allowed_labels'],['DEFINITION'])
            request=state['calls'][0]['request']
            self.assertEqual(request['format']['$defs']['Labels_T2']['properties']['labels']['items']['const'],'COMPARISON')
            self.assertTrue(request['stream'])

class CheckpointTests(unittest.TestCase):
    def test_complete_run_has_three_calls_and_resumes_with_zero_calls(self):
        with tempfile.TemporaryDirectory() as d:
            first=g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller(),progress=lambda x:None)
            self.assertEqual(first['status'],'DRAFT_READY');self.assertEqual(len(first['calls']),3)
            second=g.run(SPEC,CONFIG,d,BINDING,caller=lambda *a: self.fail('No new calls'),progress=lambda x:None)
            self.assertEqual(len(second['calls']),3)
            self.assertFalse(second['production_ready'])
            self.assertEqual(second['semantic_quality'],'UNCONFIRMED')
            self.assertTrue((Path(d)/'rubric_draft.md').exists())
    def test_timeout_keeps_completed_plan_and_requires_explicit_retry(self):
        with tempfile.TemporaryDirectory() as d:
            first=g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller('B3_T1'),progress=lambda x:None)
            self.assertEqual(first['status'],'ERROR');self.assertEqual(set(first['steps']),{'B1_B2'})
            second=g.run(SPEC,CONFIG,d,BINDING,caller=lambda *a:self.fail('No blind retry'),progress=lambda x:None)
            self.assertEqual(len(second['calls']),2)
            third=g.run(SPEC,CONFIG,d,BINDING,retry_failed=True,caller=fixture_caller(),progress=lambda x:None)
            self.assertEqual(third['status'],'DRAFT_READY');self.assertEqual(len(third['calls']),4)
            self.assertEqual(third['calls'][2]['stage'],'B3_T1')
            self.assertEqual(third['calls'][1]['response_text'],'{"criteria":')
    def test_changed_binding_stops_before_model_call(self):
        with tempfile.TemporaryDirectory() as d:
            g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller(),progress=lambda x:None)
            with self.assertRaisesRegex(ValueError,'different input'):
                g.run(SPEC,CONFIG,d,dict(BINDING,version='different'),caller=lambda *a:self.fail())
    def test_modified_checkpoint_stops_before_model_call(self):
        with tempfile.TemporaryDirectory() as d:
            g.run(SPEC,CONFIG,d,BINDING,caller=fixture_caller(),progress=lambda x:None)
            p=Path(d)/'generation_result.json';data=g.read_json(p);data['steps']['B1_B2']['value']['choices']['T1']['weight']=8;g.write_json(p,data)
            with self.assertRaisesRegex(ValueError,'edited'):g.run(SPEC,CONFIG,d,BINDING,caller=lambda *a:self.fail())
    def test_run_lock_prevents_second_writer(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'run.lock').write_text('another process')
            with self.assertRaises(FileExistsError):g.run(SPEC,CONFIG,d,BINDING,caller=lambda *a:self.fail())
    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate JSON key'):
            json.loads('{"claim":"A","claim":"B"}',object_pairs_hook=g.no_duplicates)

class StreamTests(unittest.TestCase):
    def server(self, chunks, *, delay=0, code=200):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(code);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
                try:
                    for chunk in chunks:
                        if delay:time.sleep(delay)
                        self.wfile.write((json.dumps(chunk,ensure_ascii=False)+'\n').encode('utf-8'));self.wfile.flush()
                except (BrokenPipeError,ConnectionResetError):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}'
    def chunks(self, *, done=True, reason='stop', model=g.DEFAULT_MODEL):
        text=json.dumps(PLAN,ensure_ascii=False)
        chunks=[dict(model=model,message=dict(content=text[i:i+23]),done=False) for i in range(0,len(text),23)]
        if done:chunks.append(dict(model=model,message=dict(content=''),done=True,done_reason=reason,prompt_eval_count=400,eval_count=100))
        return chunks
    def invoke(self,url,timeout=2):
        payload=g.make_payload(CONFIG,g.PLAN_PROMPT,dict(question=SPEC.question),g.PlanChoice,512)
        record=dict(stage='test');self.record=record
        return g.stream_call(url,payload,record,lambda:None,timeout,progress=lambda x:None)
    def test_streamed_utf8_json_is_reconstructed(self):
        self.assertEqual(self.invoke(self.server(self.chunks())),PLAN)
        self.assertGreater(self.record['chunks'],1)
    def test_truncated_generation_preserves_text_and_stops(self):
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            self.invoke(self.server(self.chunks(reason='length')))
        self.assertTrue(self.record['response_text'])
    def test_missing_terminal_stops(self):
        with self.assertRaisesRegex(RuntimeError,'without done'):
            self.invoke(self.server(self.chunks(done=False)))
    def test_timeout_preserves_partial_and_finishes(self):
        start=time.monotonic()
        with self.assertRaises((TimeoutError,OSError)):
            self.invoke(self.server(self.chunks(),delay=0.02),timeout=0.09)
        self.assertLess(time.monotonic()-start,1)
        self.assertTrue(self.record['response_text'])
        self.assertEqual(self.record['status'],'ERROR')
    def test_wrong_model_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'model differs'):
            self.invoke(self.server(self.chunks(model='wrong:model')))
    def test_context_limit_is_rejected(self):
        chunks=self.chunks();chunks[-1]['prompt_eval_count']=4090
        with self.assertRaisesRegex(RuntimeError,'context limit'):self.invoke(self.server(chunks))
    def test_thinking_output_is_rejected(self):
        chunks=self.chunks();chunks[0]['message']['thinking']='reasoning'
        with self.assertRaisesRegex(RuntimeError,'thinking'):self.invoke(self.server(chunks))
