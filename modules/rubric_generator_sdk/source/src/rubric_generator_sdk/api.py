from __future__ import annotations
import http.client
import json
from pathlib import Path
import re
from importlib.metadata import version
from ._core.core import InputSpec, Rubric, digest, validate_rubric
from ._engine import generator as g
from ._version import __version__
from .contracts import GenerationResponse
from .integrity import verify_runtime
from .locking import WorkerLock, BusyError

OWNER={'owner':'rubric-generator-sdk','storage_schema':1}


def validate_rubric_dict(value:dict)->dict:
    """Structural validation only, never human approval or semantic certification."""
    rubric=Rubric.model_validate_json(json.dumps(value,ensure_ascii=False))
    validate_rubric(rubric)
    return dict(structurally_valid=True,rubric_sha256=digest(rubric),human_approved=False)


def _checkpoint(path,binding):
    state=g.read_json(path)
    if state.get('integrity')!=g.sha({k:v for k,v in state.items() if k!='integrity'}):
        raise ValueError('Checkpoint integrity mismatch; preserve it and use a new work_dir')
    if state.get('binding')!=binding:
        raise ValueError('Checkpoint binding mismatch')
    return state


class RubricGenerator:
    """Blocking SDK. Call from a background worker with one shared local work_dir."""
    def __init__(self,work_dir,*,model=g.DEFAULT_MODEL,base_url='http://127.0.0.1:11434',
                 timeout=420,num_ctx=4096,expected_model_digest=None):
        if type(timeout) is not int or not 30<=timeout<=1200:
            raise ValueError('timeout must be an integer from 30 to 1200')
        if type(num_ctx) is not int or not 2048<=num_ctx<=16384:
            raise ValueError('num_ctx must be an integer from 2048 to 16384')
        if not isinstance(model,str) or not model.strip():raise ValueError('model must be nonempty')
        if not isinstance(base_url,str):raise ValueError('base_url must be a string')
        conn,_=g.connection(base_url,timeout);conn.close()
        if expected_model_digest is not None and not re.fullmatch('[a-f0-9]{64}',expected_model_digest):
            raise ValueError('expected_model_digest must be a lowercase SHA-256 digest')
        self.work_dir=Path(work_dir).expanduser().resolve()
        if self.work_dir.is_relative_to(Path(__file__).resolve().parent):
            raise ValueError('work_dir must be outside the installed package')
        self.config=dict(model=model,base_url=base_url.rstrip('/'),timeout=timeout,num_ctx=num_ctx)
        self.expected_model_digest=expected_model_digest

    def _response(self,status,**fields):
        return GenerationResponse(status=status,model_tag=self.config['model'],**fields).model_dump(mode='json')

    def generate(self,question:str,reference_answer:str,*,question_id=None,total_units=1000,
                 task_budgets_units=None,retry_failed=False,progress=None)->dict:
        data=dict(question=question,reference_answer=reference_answer,total_units=total_units,
                  units_per_point=100,task_budgets_units=task_budgets_units)
        if question_id is not None:data['question_id']=question_id
        return self.generate_input(data,retry_failed=retry_failed,progress=progress)

    def generate_input(self,data:dict,*,retry_failed=False,progress=None)->dict:
        if type(retry_failed) is not bool:raise ValueError('retry_failed must be a bool')
        if progress is not None and not callable(progress):raise ValueError('progress must be callable')
        try:
            if not isinstance(data,dict):raise ValueError('Input must be a JSON object')
            request=dict(data)
            automatic_id='question_id' not in request
            if automatic_id:request['question_id']='Q_AUTO'
            spec=InputSpec.model_validate_json(json.dumps(request,ensure_ascii=False))
            if automatic_id:
                spec=spec.model_copy(update={'question_id':'Q_'+g.sha(spec.model_dump(mode='json',exclude={'question_id'}))[:24]})
        except (TypeError,ValueError) as error:
            return self._response('INVALID_INPUT',error=dict(code='INPUT_VALIDATION',message=str(error)))
        def report(text):
            if progress is not None:
                # A display callback must never change the model result.
                try:progress(text)
                except Exception:pass
        fields=dict(question_id=spec.question_id)
        stage='PACKAGE_CHECK';folder=None
        try:
            runtime_sha=verify_runtime()
            root=self.work_dir
            marker=root/'storage.json'
            if root.exists() and not marker.exists() and any(p.name!='.worker.lock' for p in root.iterdir()):
                raise ValueError('work_dir is not empty and does not belong to this SDK; choose a new directory')
            root.mkdir(parents=True,exist_ok=True)
            stage='WORKER_LOCK'
            with WorkerLock(root/'.worker.lock'):
                if marker.exists():
                    if g.read_json(marker)!=OWNER:raise ValueError('Unknown work_dir owner')
                else:
                    if any(p.name!='.worker.lock' for p in root.iterdir()):
                        raise ValueError('work_dir contains unrelated files')
                    g.write_json(marker,OWNER)
                stage='MODEL_CHECK'
                model_sha=g.model_digest(self.config['base_url'],self.config['model'])
                fields['model_digest']=model_sha
                if self.expected_model_digest and model_sha!=self.expected_model_digest:
                    raise ValueError('Installed Ollama model digest differs from expected_model_digest')
                binding=dict(sdk_version=__version__,engine_version=g.VERSION,runtime_sha256=runtime_sha,
                             pydantic_version=version('pydantic'),input_sha256=g.sha(spec.model_dump(mode='json')),
                             config=self.config,model_digest=model_sha)
                job_id=g.sha(binding)
                fields['job_id']=job_id
                folder=root/'jobs'/job_id
                path=folder/'generation_result.json'
                stage='CHECKPOINT_CHECK'
                prior=_checkpoint(path,binding) if path.exists() else None
                initial_calls=len(prior['calls']) if prior else 0
                lock=folder/'run.lock'
                if lock.exists():
                    if not retry_failed or prior is None:
                        raise ValueError('Interrupted job lock found; inspect checkpoint then use retry_failed=True')
                    # The OS worker lock is held and this private job's binding was verified.
                    lock.unlink()
                stage='GENERATION'
                state=g.run(spec,self.config,folder,binding,retry_failed=retry_failed,progress=report)
                result_fields=dict(fields,metrics=dict(model_calls_total=len(state['calls']),new_model_calls=len(state['calls'])-initial_calls),
                    artifacts=dict(checkpoint=str(path),result=str(folder/'sdk_result.json')))
                if state['status']=='DRAFT_READY':
                    checked=validate_rubric_dict(state['rubric'])
                    if checked['rubric_sha256']!=state['rubric_sha256']:raise ValueError('Generated rubric hash mismatch')
                    result_fields.update(rubric=state['rubric'],rubric_sha256=state['rubric_sha256'],
                        quality_report=state['quality_report'],review_status='PENDING')
                    result_fields['artifacts'].update(rubric_json=str(folder/'rubric_draft.json'),rubric_markdown=str(folder/'rubric_draft.md'))
                else:
                    codes={'NEEDS_REVIEW':'SEMANTIC_OR_CONTRACT_REVIEW','ERROR':'OLLAMA_OR_IO_ERROR','INTERRUPTED':'INTERRUPTED'}
                    result_fields['error']=dict(code=codes.get(state['status'],'ENGINE_STATE'),message=state.get('error','Generation did not complete'))
                result=self._response(state['status'],**result_fields)
                stage='RESULT_WRITE'
                g.write_json(folder/'sdk_result.json',result)
                return result
        except BusyError as error:
            return self._response('BUSY',**fields,error=dict(code='WORKER_BUSY',message=str(error)))
        except KeyboardInterrupt:
            return self._response('INTERRUPTED',**fields,error=dict(code='INTERRUPTED',message='Interrupted by caller'))
        except (OSError,ValueError,RuntimeError,http.client.HTTPException) as error:
            code={'PACKAGE_CHECK':'PACKAGE_OR_STORAGE_ERROR','WORKER_LOCK':'STORAGE_ERROR',
                  'MODEL_CHECK':'MODEL_UNAVAILABLE_OR_MISMATCH','CHECKPOINT_CHECK':'CHECKPOINT_REJECTED',
                  'GENERATION':'GENERATION_ERROR','RESULT_WRITE':'RESULT_WRITE_ERROR'}[stage]
            if folder is not None:fields['artifacts']=dict(checkpoint=str(folder/'generation_result.json'))
            return self._response('ERROR',**fields,error=dict(code=code,message=str(error)))


def doctor(*,offline=False,model=g.DEFAULT_MODEL,base_url='http://127.0.0.1:11434')->dict:
    runtime_sha=verify_runtime()
    spec=InputSpec(question='Định nghĩa mã phiên.',reference_answer='Mã phiên là mã định danh một phiên.')
    task=dict(id='T1',quote=spec.question,labels=['DEFINITION'],weight=1)
    sources=g.references(spec)
    raw=dict(criteria=[dict(kind='DEFINITION',source_ids=[next(iter(sources))],weight=1)],issues=[])
    value=g.task_contract(task,sources).model_validate_json(json.dumps(raw,ensure_ascii=False))
    draft=g.materialize_task(task,value,sources)
    rubric=g.compile_output(spec,[task],[draft]);validate_rubric(rubric)
    result=dict(status='OK',package_version=__version__,engine_version=g.VERSION,pydantic_version=version('pydantic'),
                runtime_sha256=runtime_sha,offline=offline,model_calls=0,model_tag=model,production_ready=False)
    if not offline:result['model_digest']=g.model_digest(base_url,model)
    return result
