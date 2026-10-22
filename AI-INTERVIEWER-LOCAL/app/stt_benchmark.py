from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.services.speech_to_text import transcribe_bytes
from app.services.stt_benchmark import build_benchmark_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Đánh giá STT local bằng WER/CER")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/stt_benchmark_report.json"))
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = payload.get("samples") or []
    settings = Settings.from_env()
    evaluated = []
    for sample in samples:
        item = dict(sample)
        if not item.get("hypothesis"):
            audio_path = (manifest_path.parent / str(item["audio"])).resolve()
            result = transcribe_bytes(
                settings,
                audio_path.read_bytes(),
                filename=audio_path.name,
                language=item.get("language"),
                hotwords=item.get("critical_terms") or [],
                ambient_noise_dbfs=item.get("ambient_noise_dbfs"),
            )
            item["hypothesis"] = result["text"]
            item["stt"] = {
                "model": result.get("model"),
                "runtime": result.get("runtime"),
                "metrics": result.get("metrics"),
            }
        evaluated.append(item)

    report = build_benchmark_report(evaluated)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"passed": report["passed"], **report["conditions"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
