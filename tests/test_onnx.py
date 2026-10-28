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
