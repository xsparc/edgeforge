"""Native runtime adapters. Imports are lazy so bundle tooling stays lightweight."""

from importlib.metadata import version
from typing import Protocol

import numpy as np

from .contracts import ModelConfig
from .errors import EdgeForgeError


class Adapter(Protocol):
    runtime_version: str
    providers: list[str]

    def run(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]: ...


def validate_onnx(model: bytes):
    try:
        import onnx
        from google.protobuf.message import Message
    except ImportError as exc:
        raise EdgeForgeError("install the onnx extra to use this runtime") from exc
    try:
        graph = onnx.load_model_from_string(model)

        def visit(message):
            if isinstance(message, onnx.TensorProto) and (
                message.external_data or message.data_location == onnx.TensorProto.EXTERNAL
            ):
                raise EdgeForgeError("external ONNX data is unsupported")
            for _, value in message.ListFields():
                if isinstance(value, Message):
                    visit(value)
                elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    for child in value:
                        if isinstance(child, Message):
                            visit(child)

        visit(graph)
        onnx.checker.check_model(graph)
        return graph
    except Exception as exc:
        raise EdgeForgeError("invalid or unsupported self-contained ONNX model") from exc


class OnnxAdapter:
    def __init__(self, model: bytes, config: ModelConfig):
        validate_onnx(model)
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise EdgeForgeError("install the onnx extra to use this runtime") from exc
        if config.provider not in ort.get_available_providers():
            raise EdgeForgeError("requested ONNX execution provider is unavailable")
        options = ort.SessionOptions()
        options.intra_op_num_threads = config.threads
        options.inter_op_num_threads = 1
        options.log_severity_level = 4
        if config.provider != "CPUExecutionProvider":
            options.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
        try:
            self.session = ort.InferenceSession(model, options, providers=[config.provider])
            self.session.disable_fallback()
            self.providers = self.session.get_providers()
            if config.provider not in self.providers:
                raise EdgeForgeError("provider initialization fell back unexpectedly")
            types = {
                "float32": "tensor(float)",
                "float64": "tensor(double)",
                "int32": "tensor(int32)",
                "int64": "tensor(int64)",
                "uint8": "tensor(uint8)",
                "bool": "tensor(bool)",
            }
            for metadata, specs in (
                (self.session.get_inputs(), config.inputs),
                (self.session.get_outputs(), config.outputs),
            ):
                by_name = {node.name: node for node in metadata}
                if set(by_name) != {spec.name for spec in specs}:
                    raise EdgeForgeError("model tensor names differ from configuration")
                for spec in specs:
                    node = by_name[spec.name]
                    if node.type != types[spec.dtype] or node.shape != spec.shape:
                        raise EdgeForgeError("model tensor dtype or static shape differs")
            self.outputs = [spec.name for spec in config.outputs]
            self.runtime_version = ort.__version__
        except Exception as exc:
            raise EdgeForgeError("ONNX session initialization failed") from exc

    def run(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        try:
            return dict(zip(self.outputs, self.session.run(self.outputs, inputs), strict=True))
        except Exception as exc:
            raise EdgeForgeError("ONNX inference failed") from exc


class ExecuTorchAdapter:
    def __init__(self, model: bytes, config: ModelConfig):
        try:
            import torch
            from executorch.runtime import Runtime
        except ImportError as exc:
            raise EdgeForgeError(
                "install a supported ExecuTorch build to use this runtime"
            ) from exc
        if config.threads != 1:
            raise EdgeForgeError("ExecuTorch thread overrides are unsupported")
        try:
            self.torch = torch
            self.program = Runtime.get().load_program(model)
            self.method = self.program.load_method("forward")
            self.inputs = [s.name for s in config.inputs]
            self.outputs = [s.name for s in config.outputs]
            self.providers = ["compiled-program"]
            self.runtime_version = version("executorch")
        except Exception as exc:
            raise EdgeForgeError("ExecuTorch program initialization failed") from exc

    def run(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        try:
            tensors = [
                self.torch.from_numpy(np.ascontiguousarray(inputs[n]).copy()) for n in self.inputs
            ]
            outputs = self.method.execute(tensors)
            return {
                name: tensor.detach().cpu().numpy().copy()
                for name, tensor in zip(self.outputs, outputs, strict=True)
            }
        except Exception as exc:
            raise EdgeForgeError("ExecuTorch inference failed") from exc


def create_adapter(model: bytes, config: ModelConfig) -> Adapter:
    return (
        OnnxAdapter(model, config) if config.runtime == "onnx" else ExecuTorchAdapter(model, config)
    )
