"""Explicit ONNX dynamic INT8 transformation with source provenance."""

import tempfile
from pathlib import Path

from .adapters import validate_onnx
from .bundle import MAX_MODEL_BYTES, read_bounded
from .errors import EdgeForgeError


def dynamic_int8(model: bytes) -> bytes:
    graph = validate_onnx(model)
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise EdgeForgeError("install the onnx extra to quantize models") from exc
    try:
        with tempfile.TemporaryDirectory(prefix="edgeforge-") as directory:
            output = Path(directory) / "model.onnx"
            quantize_dynamic(
                graph,
                str(output),
                weight_type=QuantType.QInt8,
                op_types_to_quantize=["MatMul", "Gemm"],
                per_channel=False,
            )
            result = read_bounded(output, MAX_MODEL_BYTES)
            transformed = validate_onnx(result)
            if not any(
                n.op_type in {"MatMulInteger", "QLinearMatMul"} for n in transformed.graph.node
            ):
                raise EdgeForgeError(
                    "model has no supported quantizable constant-weight operations"
                )
            return result
    except Exception as exc:
        raise EdgeForgeError(
            "dynamic INT8 quantization failed or changed no supported operations"
        ) from exc
