import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from edgeforge.adapters import ExecuTorchAdapter
from edgeforge.benchmark import benchmark
from edgeforge.bundle import pack, unpack
from edgeforge.contracts import BenchmarkOptions, ModelConfig


def et_config(config):
    return ModelConfig.model_validate(
        config.model_dump() | {"runtime": "executorch", "provider": "portable"}
    )


def test_executorch_api_contract(config, monkeypatch):
    calls = []

    class Tensor:
        def __init__(self, array):
            self.array = array

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.array

    runtime_module = ModuleType("executorch.runtime")
    method = SimpleNamespace(execute=lambda tensors: [Tensor(tensors[0].array * 2)])
    program = SimpleNamespace(load_method=lambda name: (calls.append(name), method)[1])
    runtime_module.Runtime = SimpleNamespace(
        get=lambda: SimpleNamespace(load_program=lambda data: (calls.append(data), program)[1])
    )
    monkeypatch.setitem(sys.modules, "executorch.runtime", runtime_module)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(from_numpy=Tensor))
    monkeypatch.setattr("edgeforge.adapters.version", lambda _: "contract-test")
    adapter = ExecuTorchAdapter(b"program", et_config(config))
    np.testing.assert_array_equal(adapter.run({"x": np.array([1, 2])})["y"], [2, 4])
    assert calls == [b"program", "forward"]


def test_real_executorch_export_and_execution(config, vectors):
    torch = pytest.importorskip("torch")
    pytest.importorskip("executorch.runtime")
    from executorch.exir import to_edge_transform_and_lower

    class Double(torch.nn.Module):
        def forward(self, x):
            return x + x

    exported = torch.export.export(Double().eval(), (torch.ones(2),))
    program = to_edge_transform_and_lower(exported, partitioner=[]).to_executorch()
    bundle = unpack(pack(program.buffer, vectors, et_config(config)))
    report = benchmark(bundle, BenchmarkOptions(iterations=2, warmup=1))
    assert report.agreement["passed"] is True
