import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch

from rubric_generator_sdk import RubricGenerator,doctor,validate_rubric_dict
from rubric_generator_sdk._engine import generator as g
from rubric_generator_sdk.locking import WorkerLock,BusyError
from rubric_generator_sdk.contracts import GenerationResponse
from test_engine_regression import ANCHORED_PLAN,DEFINITION,COMPARISON,SPEC

SIMPLE=dict(question='Định nghĩa mã phiên.',reference_answer='Mã phiên là mã định danh một phiên đăng nhập.')


class Server:
    def __init__(self):
        self.calls=[];self.mode='normal';outer=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def reply(self,value):
                body=(json.dumps(value,ensure_ascii=False)+'\n').encode('utf-8')
                self.send_response(200);self.send_header('Content-Length',str(len(body)))
                self.send_header('Content-Type','application/x-ndjson');self.end_headers();self.wfile.write(body)
            def do_GET(self):
                self.reply(dict(models=[dict(name=g.DEFAULT_MODEL,model=g.DEFAULT_MODEL,digest='a'*64)]))
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.calls.append(payload)
                if outer.mode=='http_error':
                    self.send_response(503);self.end_headers();self.wfile.write(b'Fixture unavailable');return
                text=payload['messages'][1]['content']
                data=json.loads(text.split('\nDATA\n',1)[1])
                if text.startswith('B1/B2'):
                    if 'Stack' in data['question']:value=ANCHORED_PLAN
                    else:value=dict(choices=dict(T1=dict(labels=['DEFINITION'],weight=1)),issues=[])
                    if outer.mode=='review':value=dict(value,issues=['Reference needs manual review'])
                elif 'Stack' in data['question']:
                    value=DEFINITION if data['selected_kind']=='DEFINITION' else COMPARISON
                else:
                    value=dict(criteria=[dict(kind='DEFINITION',source_ids=['R0'],weight=1)],issues=[])
                content='not json' if outer.mode=='bad_json' else json.dumps(value,ensure_ascii=False)
                self.reply(dict(model=g.DEFAULT_MODEL,message=dict(content=content),done=True,done_reason='stop',prompt_eval_count=300,eval_count=100))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)


class SDKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.server=Server()
    @classmethod
    def tearDownClass(cls):cls.server.close()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'data'
        self.server.calls.clear();self.server.mode='normal'
        self.sdk=RubricGenerator(self.root,base_url=self.server.url)
    def tearDown(self):self.tmp.cleanup()

    def test_generation_and_json_contract(self):
        result=self.sdk.generate_input(SIMPLE)
        self.assertEqual(result['status'],'DRAFT_READY')
        self.assertEqual(result['metrics']['new_model_calls'],2)
        self.assertEqual(result['rubric']['total_units'],1000)
        self.assertEqual(result['review_status'],'PENDING')
        self.assertFalse(result['human_approved']);self.assertFalse(result['production_ready'])
        self.assertEqual(validate_rubric_dict(result['rubric'])['rubric_sha256'],result['rubric_sha256'])
        GenerationResponse.model_validate_json(json.dumps(result))
        self.assertTrue(Path(result['artifacts']['result']).exists())
    def test_composite_and_teacher_budgets(self):
        result=self.sdk.generate_input(dict(SPEC.model_dump(mode='json'),task_budgets_units={'T1':400,'T2':600}))
        self.assertEqual(result['status'],'DRAFT_READY',result)
        self.assertEqual([t['max_points_units'] for t in result['rubric']['tasks']],[400,600])
        self.assertEqual(result['metrics']['new_model_calls'],3)
    def test_function_and_json_same_normalized_identity(self):
        a=self.sdk.generate(**SIMPLE)
        b=self.sdk.generate_input(SIMPLE)
        self.assertEqual(a['job_id'],b['job_id']);self.assertEqual(a['question_id'],b['question_id'])
        self.assertEqual(b['metrics']['new_model_calls'],0);self.assertEqual(len(self.server.calls),2)
    def test_invalid_input_has_no_network_calls(self):
        with patch.object(g,'model_digest',side_effect=AssertionError('No network')):
            for data in [dict(question='',reference_answer='x'),dict(question='x'),dict(SIMPLE,total_units=True),dict(SIMPLE,question_id='../escape'),dict(SIMPLE,extra='bad'),None]:
                with self.subTest(data=data):self.assertEqual(self.sdk.generate_input(data)['status'],'INVALID_INPUT')
    def test_review_is_not_a_rubric(self):
        self.server.mode='review';r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'NEEDS_REVIEW');self.assertIsNone(r['rubric'])
        self.assertEqual(r['metrics']['model_calls_total'],1)
        self.sdk.generate_input(SIMPLE);self.assertEqual(len(self.server.calls),1)
    def test_invalid_model_json_requests_review(self):
        self.server.mode='bad_json';r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'NEEDS_REVIEW');self.assertIsNone(r['rubric'])
    def test_transport_error_and_explicit_retry(self):
        self.server.mode='http_error';r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(r['metrics']['model_calls_total'],1)
        self.server.mode='normal';r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(r['metrics']['new_model_calls'],0)
        r=self.sdk.generate_input(SIMPLE,retry_failed=True)
        self.assertEqual(r['status'],'DRAFT_READY');self.assertEqual(r['metrics']['model_calls_total'],3)
    def test_model_digest_pin(self):
        pinned=RubricGenerator(self.root,base_url=self.server.url,expected_model_digest='b'*64)
        result=pinned.generate_input(SIMPLE)
        self.assertEqual(result['status'],'ERROR');self.assertEqual(result['error']['code'],'MODEL_UNAVAILABLE_OR_MISMATCH')
        self.assertEqual(len(self.server.calls),0)
    def test_offline_doctor_never_calls_ollama(self):
        with patch.object(g,'model_digest',side_effect=AssertionError('No network')):
            self.assertEqual(doctor(offline=True)['status'],'OK')
    def test_storage_preserves_unrelated_files(self):
        self.root.mkdir();p=self.root/'README.md';p.write_text('existing')
        r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(p.read_text(),'existing')
        self.assertEqual(len(self.server.calls),0)
    def test_busy_does_not_start_model(self):
        self.root.mkdir()
        with WorkerLock(self.root/'.worker.lock'):
            result=self.sdk.generate_input(SIMPLE)
        self.assertEqual(result['status'],'BUSY');self.assertEqual(len(self.server.calls),0)
        self.assertEqual(self.sdk.generate_input(SIMPLE)['status'],'DRAFT_READY')
    def test_lock_released_when_other_process_exits(self):
        self.root.mkdir()
        code='from pathlib import Path; from rubric_generator_sdk.locking import WorkerLock; import sys,time\nwith WorkerLock(Path(sys.argv[1])):\n print("LOCKED",flush=True)\n time.sleep(15)'
        child=subprocess.Popen([sys.executable,'-c',code,str(self.root/'.worker.lock')],stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'LOCKED')
            self.assertEqual(self.sdk.generate_input(SIMPLE)['status'],'BUSY')
        finally:
            child.kill();child.wait(timeout=5);child.stdout.close()
        with WorkerLock(self.root/'.worker.lock'):pass
    def test_tampered_checkpoint_blocked_before_new_generation(self):
        r=self.sdk.generate_input(SIMPLE);p=Path(r['artifacts']['checkpoint'])
        data=json.loads(p.read_text());data['status']='ERROR';p.write_text(json.dumps(data))
        r=self.sdk.generate_input(SIMPLE,retry_failed=True)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(r['error']['code'],'CHECKPOINT_REJECTED')
        self.assertEqual(len(self.server.calls),2)
    def test_stale_job_lock_requires_explicit_retry(self):
        self.server.mode='http_error';r=self.sdk.generate_input(SIMPLE)
        lock=Path(r['artifacts']['checkpoint']).parent/'run.lock';lock.write_text('old process')
        self.server.mode='normal';r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'ERROR');self.assertTrue(lock.exists())
        r=self.sdk.generate_input(SIMPLE,retry_failed=True)
        self.assertEqual(r['status'],'DRAFT_READY');self.assertFalse(lock.exists())
    def test_changed_input_separate_job(self):
        first=self.sdk.generate_input(dict(SIMPLE,question_id='MY_Q'))
        second=self.sdk.generate_input(dict(SIMPLE,question_id='MY_Q',total_units=2000))
        self.assertNotEqual(first['job_id'],second['job_id'])
        self.assertEqual(second['rubric']['total_units'],2000)
        self.assertTrue(Path(first['artifacts']['checkpoint']).exists())
    def test_progress_callback_cannot_break_generation(self):
        def bad(_):raise ValueError('Display failure')
        self.assertEqual(self.sdk.generate_input(SIMPLE,progress=bad)['status'],'DRAFT_READY')
    def test_cli_one_json_stdout_and_cache(self):
        cmd=[sys.executable,'-m','rubric_generator_sdk','generate','--input','-','--work-dir',str(self.root),'--base-url',self.server.url]
        env=dict(os.environ,PYTHONIOENCODING='cp1258')
        run=subprocess.run(cmd,input=json.dumps(SIMPLE,ensure_ascii=False).encode('utf-8'),capture_output=True,env=env,timeout=10)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        self.assertEqual(len(run.stdout.splitlines()),1)
        result=json.loads(run.stdout);self.assertEqual(result['status'],'DRAFT_READY')
        self.assertIn(b'generating',run.stderr)
        run=subprocess.run(cmd,input=json.dumps(SIMPLE).encode(),capture_output=True,env=env,timeout=10)
        self.assertEqual(json.loads(run.stdout)['metrics']['new_model_calls'],0)
    def test_cli_duplicate_json_keys_rejected(self):
        cmd=[sys.executable,'-m','rubric_generator_sdk','generate','--input','-','--work-dir',str(self.root)]
        run=subprocess.run(cmd,input=b'{"question":"A","question":"B","reference_answer":"X"}',capture_output=True,timeout=10)
        self.assertEqual(run.returncode,2);self.assertEqual(json.loads(run.stdout)['status'],'INVALID_INPUT')
    def test_runtime_integrity_failure_stops_generation(self):
        with patch('rubric_generator_sdk.api.verify_runtime',side_effect=ValueError('Changed SDK file')):
            r=self.sdk.generate_input(SIMPLE)
        self.assertEqual(r['status'],'ERROR');self.assertEqual(len(self.server.calls),0)
    def test_namespace_does_not_replace_project_modules(self):
        code='import sys,types\na=types.ModuleType("generator");b=types.ModuleType("rubric_builder");sys.modules["generator"]=a;sys.modules["rubric_builder"]=b\nimport rubric_generator_sdk\nassert sys.modules["generator"] is a and sys.modules["rubric_builder"] is b\nprint("OK")'
        r=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)


if __name__=='__main__':unittest.main()
