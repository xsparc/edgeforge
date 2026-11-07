import pytest

pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")

from edgeforge.adapters import OnnxAdapter, validate_onnx
from edgeforge.benchmark import benchmark
from edgeforge.bundle import digest, pack, unpack
from edgeforge.contracts import BenchmarkOptions, ModelConfig
from edgeforge.errors import EdgeForgeError
from edgeforge.example import example_assets
from edgeforge.quantize import dynamic_int8


def test_real_cpu_inference_and_deterministic_example():
    model, vectors, config = example_assets()
    assert example_assets() == (model, vectors, config)
    result = benchmark(unpack(pack(model, vectors, config)), BenchmarkOptions(iterations=3))
    assert result.agreement["passed"] is True
    assert result.active_providers == ["CPUExecutionProvider"]


def test_real_dynamic_quantization(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    model, vectors, config = example_assets()
    quantized = dynamic_int8(model)
    assert quantized != model
    bundle = unpack(
        pack(quantized, vectors, config, quantization="dynamic-int8", source_digest=digest(model))
    )
    report = benchmark(bundle, BenchmarkOptions(iterations=3, atol=0.05, rtol=0.02))
    assert report.agreement["passed"] is True
    assert bundle.manifest.source_model_sha256 == digest(model)


def test_missing_provider_never_silently_falls_back():
    model, _, config = example_assets()
    config = ModelConfig.model_validate(config.model_dump() | {"provider": "MissingProvider"})
    with pytest.raises(EdgeForgeError, match="unavailable"):
        OnnxAdapter(model, config)


def test_wrong_static_contract_fails():
    model, _, config = example_assets()
    config.inputs[0].shape = [3]
    with pytest.raises(EdgeForgeError):
        OnnxAdapter(model, config)


def test_external_tensor_data_rejected():
    import onnx

    model, _, _ = example_assets()
    graph = onnx.load_model_from_string(model)
    tensor = graph.graph.initializer[0]
    tensor.ClearField("raw_data")
    tensor.data_location = onnx.TensorProto.EXTERNAL
    entry = tensor.external_data.add()
    entry.key, entry.value = "location", "private-weights.bin"
    with pytest.raises(EdgeForgeError):
        validate_onnx(graph.SerializeToString())


def test_scalar_tensor_and_cli_accuracy_exit(tmp_path, monkeypatch, capsys):
    import io

    import numpy as np
    from onnx import TensorProto, helper

    from edgeforge.cli import main

    graph = helper.make_graph(
        [helper.make_node("Add", ["x", "x"], ["y"])],
        "scalar",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=9)
    config = ModelConfig(
        runtime="onnx",
        inputs=[{"name": "x", "dtype": "float32", "shape": []}],
        outputs=[{"name": "y", "dtype": "float32", "shape": []}],
    )
    vectors = io.BytesIO()
    np.savez(
        vectors,
        input__x=np.array([1, 2], dtype="float32"),
        output__y=np.array([2, 4], dtype="float32"),
    )
    bundle = unpack(pack(model.SerializeToString(), vectors.getvalue(), config))
    assert benchmark(bundle, BenchmarkOptions(iterations=1)).agreement["passed"] is True
    wrong = io.BytesIO()
    np.savez(
        wrong,
        input__x=np.array([1, 2], dtype="float32"),
        output__y=np.array([0, 0], dtype="float32"),
    )
    path = tmp_path / "wrong.efb"
    path.write_bytes(pack(model.SerializeToString(), wrong.getvalue(), config))
    monkeypatch.setattr("sys.argv", ["edgeforge", "benchmark", str(path), "--iterations", "1"])
    assert main() == 3
    assert '"passed": false' in capsys.readouterr().out
