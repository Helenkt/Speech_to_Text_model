from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from stt_local import LocalWhisperEngine, recommend_runtime


PROJECT_ROOT = Path(__file__).parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the local STT model")
    parser.add_argument("--model", default="small")
    args = parser.parse_args()

    model_dir = PROJECT_ROOT / "models" / args.model
    required_files = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
    missing = [name for name in required_files if not (model_dir / name).is_file()]
    if missing:
        raise SystemExit(f"Model is incomplete. Missing: {', '.join(missing)}")

    profile = recommend_runtime()
    engine = LocalWhisperEngine(model_dir, device="auto")
    report = {
        "status": "ready",
        "model": args.model,
        "model_size_mb": round((model_dir / "model.bin").stat().st_size / 1024**2, 1),
        "model_sha256": sha256(model_dir / "model.bin"),
        "device": engine.device,
        "compute_type": engine.compute_type,
        "cpu_threads": profile.cpu_threads,
        "cuda_ready": profile.cuda_ready,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

