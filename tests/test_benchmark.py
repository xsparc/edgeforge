from types import SimpleNamespace

import numpy as np
import pytest

from edgeforge.benchmark import benchmark, preprocess
from edgeforge.bundle import pack, unpack
from edgeforge.contracts import BenchmarkOptions, ModelConfig
from edgeforge.errors import EdgeForgeError


class Double:
    runtime_version = "test"
    providers = ["test"]

    def run(self, inputs):
        return {"y": inputs["x"] * 2}


def test_metrics_and_warmup(config, vectors, monkeypatch):
    calls = []
    runner = Double()
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter",
        lambda *a: SimpleNamespace(
            runtime_version="test",
            providers=["test"],
            run=lambda inputs: (calls.append(1), runner.run(inputs))[1],
        ),
    )
    report = benchmark(
        unpack(pack(b"fake", vectors, config)), BenchmarkOptions(iterations=3, warmup=2)
    )
    assert len(calls) == 2 * (3 + 2)
    assert report.agreement["passed"] is True
    assert report.agreement["elements_compared"] == 12
    assert report.latency_ms["p95"] >= report.latency_ms["min"] >= 0
    assert report.storage["model_bytes"] == 4
    assert "hostname" not in report.device


@pytest.mark.parametrize("kind", ["wrong", "nan", "shape", "dtype"])
def test_output_failures_are_explicit(config, vectors, monkeypatch, kind):
    values = {
        "wrong": np.zeros(2, dtype="float32"),
        "nan": np.array([float("nan"), 0], dtype="float32"),
        "shape": np.ones(3, dtype="float32"),
        "dtype": np.ones(2, dtype="int32"),
    }
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter",
        lambda *a: SimpleNamespace(
            runtime_version="test", providers=["test"], run=lambda _: {"y": values[kind]}
        ),
    )
    bundle = unpack(pack(b"fake", vectors, config))
    if kind in {"shape", "dtype"}:
        with pytest.raises(EdgeForgeError):
            benchmark(bundle, BenchmarkOptions(iterations=1))
    else:
        report = benchmark(bundle, BenchmarkOptions(iterations=1))
        assert report.agreement["passed"] is False
        assert report.agreement["finite"] is (kind != "nan")
        report.model_dump_json()


def test_affine_preprocessing(config):
    modified = ModelConfig.model_validate(
        config.model_dump() | {"preprocessing": {"x": {"scale": 2.0, "offset": -1.0}}}
    )
    source = np.array([1, 2], dtype="float32")
    actual = preprocess({"x": source}, modified)
    np.testing.assert_array_equal(actual["x"], [1, 3])
    np.testing.assert_array_equal(source, [1, 2])


def test_invocation_budget(config, vectors):
    with pytest.raises(EdgeForgeError):
        # Expand fixture cases within the archive-size budget.
        import io

        buffer = io.BytesIO()
        np.savez(
            buffer,
            input__x=np.zeros((100, 2), dtype="float32"),
            output__y=np.zeros((100, 2), dtype="float32"),
        )
        benchmark(
            unpack(pack(b"fake", buffer.getvalue(), config)), BenchmarkOptions(iterations=10000)
        )


def test_int64_comparison_does_not_lose_precision(config, monkeypatch):
    import io

    config.outputs[0].dtype = "int64"
    expected = np.array([[2**60, 2**60]], dtype="int64")
    buffer = io.BytesIO()
    np.savez(buffer, input__x=np.zeros((1, 2), dtype="float32"), output__y=expected)
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter",
        lambda *a: SimpleNamespace(
            runtime_version="test", providers=["test"], run=lambda _: {"y": expected[0] + 1}
        ),
    )
    report = benchmark(
        unpack(pack(b"fake", buffer.getvalue(), config)), BenchmarkOptions(iterations=1, warmup=0)
    )
    assert report.agreement["passed"] is False
    assert report.agreement["max_abs_error"] == 1
