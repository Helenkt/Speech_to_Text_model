import argparse
import http.client
import json
import sys
from .api import RubricGenerator,doctor
from ._engine.generator import DEFAULT_MODEL,no_duplicates,read_json

EXIT_CODES={'DRAFT_READY':0,'INVALID_INPUT':2,'NEEDS_REVIEW':3,'ERROR':4,'BUSY':5,'INTERRUPTED':130}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Local V15 rubric draft generator')
    commands=parser.add_subparsers(dest='command',required=True)
    check=commands.add_parser('doctor')
    check.add_argument('--offline',action='store_true')
    generate=commands.add_parser('generate')
    generate.add_argument('--input',required=True,help='UTF-8 JSON path or - for stdin')
    generate.add_argument('--work-dir',required=True)
    generate.add_argument('--timeout',type=int,default=420)
    generate.add_argument('--num-ctx',type=int,default=4096)
    generate.add_argument('--retry-failed',action='store_true')
    generate.add_argument('--expected-model-digest')
    for p in (check,generate):
        p.add_argument('--model',default=DEFAULT_MODEL)
        p.add_argument('--base-url',default='http://127.0.0.1:11434')
    args=parser.parse_args(argv)
    try:
        if args.command=='doctor':
            result=doctor(offline=args.offline,model=args.model,base_url=args.base_url)
            print(json.dumps(result,ensure_ascii=True));return 0
        engine=RubricGenerator(args.work_dir,model=args.model,base_url=args.base_url,timeout=args.timeout,
                               num_ctx=args.num_ctx,expected_model_digest=args.expected_model_digest)
        try:
            if args.input=='-':
                raw=sys.stdin.buffer.read(200001)
                if len(raw)>200000:raise ValueError('Input JSON exceeds 200000 bytes')
                data=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=no_duplicates)
            else:data=read_json(args.input)
        except (OSError,UnicodeError,ValueError) as error:
            result=engine._response('INVALID_INPUT',error=dict(code='INPUT_JSON',message=str(error)))
        else:
            result=engine.generate_input(data,retry_failed=args.retry_failed,
                progress=lambda s:print(s,file=sys.stderr,flush=True))
        # One JSON object on stdout. Progress is exclusively on stderr.
        print(json.dumps(result,ensure_ascii=True),flush=True)
        return EXIT_CODES[result['status']]
    except (OSError,ValueError,RuntimeError,http.client.HTTPException) as error:
        print(json.dumps(dict(status='ERROR',error=dict(code='SETUP_OR_DOCTOR',message=str(error))),ensure_ascii=True))
        return 4


if __name__=='__main__':raise SystemExit(main())
