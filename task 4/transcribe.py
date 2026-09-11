from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from stt_local import LocalWhisperEngine, recommend_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast local speech-to-text")
    parser.add_argument("audio", type=Path, help="Input audio or video file")
    parser.add_argument(
        "--model",
        default="auto",
        help="auto, tiny, base, small, medium, or a local model path",
    )
    parser.add_argument("--language", default="vi", help="vi, en, or auto")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--compute-type", default="auto")
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--hotwords", help="Preferred terms separated by spaces or commas")
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def resolve_model(model: str) -> str:
    if model == "auto":
        model = recommend_runtime().model
    local_path = Path(__file__).parent / "models" / model
    return str(local_path) if local_path.is_dir() else model


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    profile = recommend_runtime()
    selected_model = resolve_model(args.model)
    print(
        f"Auto profile: model={Path(selected_model).name}, "
        f"device={profile.device}, threads={profile.cpu_threads}, "
        f"RAM={profile.memory_gb:.1f}GB"
    )
    engine = LocalWhisperEngine(
        selected_model,
        device=args.device,
        compute_type=args.compute_type,
        download_root=Path(__file__).parent / "models",
    )
    result = engine.transcribe(
        args.audio,
        language=None if args.language == "auto" else args.language,
        beam_size=args.beam_size,
        vad_filter=not args.no_vad,
        hotwords=args.hotwords,
    )

    rendered = (
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        if args.as_json
        else result.text
    )
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Saved: {args.output}")
    else:
        print(rendered)

    print(
        f"Runtime: {result.device}/{result.compute_type} | "
        f"processing={result.processing_seconds:.3f}s | RTF={result.real_time_factor:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
