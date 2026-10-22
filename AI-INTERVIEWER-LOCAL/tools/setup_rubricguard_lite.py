from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


REVISION = "0a71e92a985b6e1ad1828cf67ce9c459639c1dca"
REPOSITORY = "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli"
FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "model.onnx",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("models/rubricguard-lite"))
    parser.add_argument("--keep-fp32", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = f"https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/onnx"
    int8 = args.output_dir / "model.int8.onnx"
    for name in FILES:
        target = args.output_dir / name
        if name == "model.onnx" and int8.exists():
            continue
        if not target.exists():
            print(f"Downloading {name}...", flush=True)
            urllib.request.urlretrieve(f"{base}/{name}", target)

    from onnxruntime.quantization import QuantType, quantize_dynamic

    fp32 = args.output_dir / "model.onnx"
    if not int8.exists():
        print("Quantizing model to INT8...", flush=True)
        quantize_dynamic(fp32, int8, weight_type=QuantType.QInt8)
    if not args.keep_fp32 and fp32.exists():
        fp32.unlink()
    summary = args.output_dir / "training_summary.json"
    if not summary.exists():
        summary.write_text(
            json.dumps(
                {
                    "model_stage": "pretrained_baseline",
                    "production_ready": False,
                    "note": (
                        "Pretrained model; no project-specific validation has been run. "
                        "Fine-tune and evaluate the exported INT8 model before enabling automatic scoring."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print(f"RubricGuard Lite ready: {int8} ({int8.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
