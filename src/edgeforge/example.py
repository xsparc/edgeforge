"""Small generated fixture; no downloaded model or dataset is needed."""

import io
from pathlib import Path

import numpy as np

from .bundle import canonical_json, deterministic_zip, pack
from .contracts import ModelConfig
from .errors import EdgeForgeError


def example_assets() -> tuple[bytes, bytes, ModelConfig]:
    try:
        from onnx import TensorProto, helper, numpy_helper
    except ImportError as exc:
        raise EdgeForgeError("install the onnx extra to generate the example") from exc
    weights = numpy_helper.from_array(np.eye(2, dtype="float32") * 2, name="weights")
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["x", "weights"], ["y"])],
        "double",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [2])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [2])],
        [weights],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=9)
    files = {}
    for name, values in {"input__x": [[1, 2], [3, 4]], "output__y": [[2, 4], [6, 8]]}.items():
        buffer = io.BytesIO()
        np.save(buffer, np.array(values, dtype="float32"), allow_pickle=False)
        files[f"{name}.npy"] = buffer.getvalue()
    config = ModelConfig(
        runtime="onnx",
        inputs=[{"name": "x", "dtype": "float32", "shape": [2]}],
        outputs=[{"name": "y", "dtype": "float32", "shape": [2]}],
    )
    return model.SerializeToString(), deterministic_zip(files), config


def write_example(directory: Path) -> dict:
    model, vectors, config = example_assets()
    bundle = pack(model, vectors, config)
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in {
        "model.onnx": model,
        "vectors.npz": vectors,
        "config.json": canonical_json(config.model_dump()),
        "example.efb": bundle,
    }.items():
        (directory / name).write_bytes(data)
    return {"created": ["config.json", "example.efb", "model.onnx", "vectors.npz"]}
