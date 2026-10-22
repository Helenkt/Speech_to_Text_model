from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.services.speech_to_text import transcribe_bytes
from app.services.stt_benchmark import build_benchmark_report


def check_audio(settings: Settings, manifest: Path, required_languages: list[str]) -> dict:
    base = manifest.resolve().parent
    supplied = json.loads(manifest.read_text(encoding="utf-8-sig"))
    samples = supplied["samples"] if isinstance(supplied, dict) else supplied
    results = []
    for sample in samples:
        path = (base / sample["audio"]).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError("Audio must exist inside the manifest directory")
        started = perf_counter()
        transcription = transcribe_bytes(settings, path.read_bytes(), filename=path.name,
            language=sample["language"], ambient_noise_dbfs=sample.get("ambient_noise_dbfs"))
        results.append({**sample, "hypothesis": transcription["text"],
                        "seconds": round(perf_counter() - started, 3),
                        "model": transcription["model"], "runtime": transcription["runtime"],
                        "needs_retry": transcription.get("needs_retry"),
                        "decode_strategy": transcription.get("decode_strategy"),
                        "decode_passes": transcription.get("decode_passes"),
                        "retry_windows": transcription.get("retry_windows", []),
                        "quality_warnings": transcription.get("quality_warnings", []),
                        "quality_reasons": transcription.get("quality_reasons", []),
                        "metrics": transcription.get("metrics", {})})
        print(f"{sample.get('id', path.name)}: decoded in {results[-1]['seconds']}s", flush=True)
    return {**build_benchmark_report(results, required_languages=required_languages),
            "production_certified": False, "llm_correction_used": False,
            "writes_student_data": False,
            "coverage_notice": "Saved audio regressions only; not a representative student benchmark or a microphone test."}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only STT checks against existing audio and reference transcripts")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--required-languages", nargs="+", default=["vi", "en"])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path to retain previous checks")
    report = check_audio(Settings.from_env(), args.manifest, args.required_languages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"passed": report["passed"], "production_certified": False,
                      "samples": [{"id": s.get("id"), "wer": s["wer"], "critical_errors": s["critical_errors"],
                                   "needs_retry": s["needs_retry"], "seconds": s["seconds"]}
                                  for s in report["samples"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
