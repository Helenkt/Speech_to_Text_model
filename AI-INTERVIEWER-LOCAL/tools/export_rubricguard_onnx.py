from __future__ import annotations

import argparse
import json
from pathlib import Path


def quantize_weights_only(source: Path, destination: Path) -> None:
    import numpy as np
    import onnx
    from onnx import helper, numpy_helper
    from onnxruntime.quantization import QuantType, quantize_dynamic

    embedding_only = destination.with_name("model.embedding-int8.onnx")
    quantize_dynamic(source, embedding_only, weight_type=QuantType.QInt8,
                     op_types_to_quantize=["Gather"])
    model = onnx.load(embedding_only)
    matmul_weights = {node.input[1] for node in model.graph.node if node.op_type == "MatMul"}
    initializers, dequantize = [], []
    for tensor in model.graph.initializer:
        if tensor.name not in matmul_weights or tensor.data_type != onnx.TensorProto.FLOAT:
            initializers.append(tensor)
            continue
        values = numpy_helper.to_array(tensor)
        if values.ndim != 2:
            initializers.append(tensor)
            continue
        scales = np.maximum(np.abs(values).max(axis=0) / 127, 1e-12).astype(np.float32)
        quantized = np.clip(np.rint(values / scales), -127, 127).astype(np.int8)
        names = [tensor.name + suffix for suffix in (".int8", ".scale", ".zero")]
        initializers.extend([numpy_helper.from_array(quantized, names[0]),
            numpy_helper.from_array(scales, names[1]),
            numpy_helper.from_array(np.zeros(scales.shape, dtype=np.int8), names[2])])
        dequantize.append(helper.make_node("DequantizeLinear", names, [tensor.name],
                                         axis=1, name=tensor.name + ".dequantize"))
    del model.graph.initializer[:]
    model.graph.initializer.extend(initializers)
    nodes = list(model.graph.node)
    del model.graph.node[:]
    model.graph.node.extend(dequantize + nodes)
    onnx.checker.check_model(model)
    onnx.save(model, destination)
    embedding_only.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(
        args.checkpoint, local_files_only=True, fix_mistral_regex=False
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.checkpoint, local_files_only=True, attn_implementation="eager"
    ).eval()
    encoded = tokenizer(
        "Câu trả lời mẫu.",
        "Tiêu chí mẫu.",
        return_tensors="pt",
    )

    class LogitsOnly(torch.nn.Module):
        def __init__(self, wrapped: torch.nn.Module):
            super().__init__()
            self.wrapped = wrapped

        def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
            return self.wrapped(input_ids=input_ids, attention_mask=attention_mask).logits

    fp32_path = args.output_dir / "model.onnx"
    torch.onnx.export(
        LogitsOnly(model),
        (encoded["input_ids"], encoded["attention_mask"]),
        fp32_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        opset_version=17,
        dynamo=False,
    )
    quantize_weights_only(fp32_path, args.output_dir / "model.int8.onnx")
    tokenizer.save_pretrained(args.output_dir)
    model.config.save_pretrained(args.output_dir)
    summary_path = args.checkpoint / "training_summary.json"
    if summary_path.exists():
        (args.output_dir / "training_summary.json").write_text(
            summary_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (args.output_dir / "runtime_manifest.json").write_text(
        json.dumps(
            {
                "format": "ONNX INT8 weights, FP32 activations",
                "quantization": "embedding INT8 + per-channel MatMul weight-only INT8",
                "input": getattr(model.config, "rubric_input_format", "student_answer + rubric_claim"),
                "labels": ["entailment", "neutral", "contradiction"],
                "fp32_mb": round(fp32_path.stat().st_size / (1024 * 1024), 1),
                "int8_mb": round(
                    (args.output_dir / "model.int8.onnx").stat().st_size / (1024 * 1024), 1
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
