"""Minimal capability report without machine or network identifiers."""

import importlib.metadata
import os
import platform

import psutil


def capabilities() -> dict:
    packages = {}
    for name in ("numpy", "onnxruntime", "onnx", "executorch", "torch", "psutil"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    providers = []
    if packages["onnxruntime"]:
        try:
            import onnxruntime

            providers = onnxruntime.get_available_providers()
        except (ImportError, OSError):
            pass
    return {
        "schema_version": 1,
        "os": platform.system(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "logical_cpus": os.cpu_count(),
        "system_ram_bytes": psutil.virtual_memory().total,
        "packages": packages,
        "onnx_registered_providers": providers,
        "accelerator_verification": "not-probed",
    }
