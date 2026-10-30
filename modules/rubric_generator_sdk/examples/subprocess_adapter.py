"""Standard-library-only adapter for a backend using a different Python environment.

Call this from the backend's background job worker, not its HTTP request handler.
The python_executable and work_dir values are server configuration, not user input.
"""
import json
import subprocess


def generate_rubric(python_executable,work_dir,question,reference_answer,*,question_id=None,timeout_seconds=None):
    request=dict(question=question,reference_answer=reference_answer)
    if question_id is not None:request['question_id']=question_id
    completed=subprocess.run(
        [str(python_executable),'-m','rubric_generator_sdk','generate',
         '--input','-','--work-dir',str(work_dir)],
        input=json.dumps(request,ensure_ascii=False).encode('utf-8'),
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout_seconds,check=False,
    )
    try:result=json.loads(completed.stdout.decode('utf-8'))
    except (UnicodeError,ValueError) as error:
        raise RuntimeError('SDK process did not return a JSON response; inspect worker stderr') from error
    expected={'DRAFT_READY':0,'INVALID_INPUT':2,'NEEDS_REVIEW':3,'ERROR':4,'BUSY':5,'INTERRUPTED':130}
    if result.get('status') not in expected or completed.returncode!=expected[result['status']]:
        raise RuntimeError('Unexpected SDK process exit/status; inspect worker logs')
    return result
