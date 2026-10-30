"""Run with a Python environment where rubric-generator-sdk is installed."""
import argparse
import json
from pathlib import Path
from rubric_generator_sdk import RubricGenerator

parser=argparse.ArgumentParser()
parser.add_argument('--work-dir',required=True)
args=parser.parse_args()
engine=RubricGenerator(work_dir=Path(args.work_dir))
result=engine.generate(
    question_id='INTERVIEW_SESSION_CODE_001',
    question='Định nghĩa mã phiên đăng nhập.',
    reference_answer='Mã phiên đăng nhập là mã định danh tạm thời đại diện cho một phiên đăng nhập.',
)
print(json.dumps(result,ensure_ascii=True,indent=2))
# If DRAFT_READY, save as a draft with reviewer approval still pending.
# Keep the envelope and rubric_sha256, not just result['rubric'].
