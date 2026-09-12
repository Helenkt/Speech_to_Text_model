from __future__ import annotations

import argparse
from pathlib import Path

from stt_local import recommend_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a Faster Whisper model for fully local inference."
    )
    parser.add_argument(
        "--model",
        default="auto",
        help="auto, tiny, base, small, medium, or a Hugging Face ID",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "models",
        help="Directory that stores the downloaded model",
    )
    return parser.parse_args()


def main() -> int:
    from faster_whisper.utils import download_model

    args = parse_args()
    model = recommend_runtime().model if args.model == "auto" else args.model
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(__file__).parent / ".cache" / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = download_model(
        model,
        output_dir=str(args.output_dir / model),
        cache_dir=str(cache_dir),
    )
    print(f"Model ready: {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
