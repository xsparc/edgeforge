"""Scoped, serial inference measurements and golden-output agreement."""

import time
from datetime import UTC, datetime

import numpy as np
import psutil

from . import __version__
from .adapters import create_adapter
from .bundle import Bundle, load_vectors
from .capabilities import capabilities
from .contracts import BenchmarkOptions, Contract, ModelConfig
from .errors import EdgeForgeError


class BenchmarkReport(Contract):
    schema_version: int = 1
    edgeforge_version: str
    bundle_sha256: str
    measured_at: str
    runtime: str
    runtime_version: str
    requested_provider: str
    active_providers: list[str]
    threads: int | None
    options: BenchmarkOptions
    cases: int
    latency_ms: dict[str, float]
    memory: dict[str, int | str]
    storage: dict[str, int]
    agreement: dict[str, bool | int | float | str]
    device: dict
    measurement_scope: str


def preprocess(inputs: dict[str, np.ndarray], config: ModelConfig) -> dict[str, np.ndarray]:
    result = {}
    for spec in config.inputs:
        array = inputs[spec.name].copy()
        if spec.name in config.preprocessing:
            transform = config.preprocessing[spec.name]
            with np.errstate(over="ignore", invalid="ignore"):
                array = (array * transform.scale + transform.offset).astype(spec.dtype)
        if not np.isfinite(array).all():
            raise EdgeForgeError("preprocessing produced nonfinite values")
        result[spec.name] = np.ascontiguousarray(array)
    return result


def benchmark(bundle: Bundle, options: BenchmarkOptions | None = None) -> BenchmarkReport:
    options = options or BenchmarkOptions()
    config = bundle.manifest.config
    vectors = load_vectors(bundle.vectors, config)
    cases = len(vectors[f"input__{config.inputs[0].name}"])
    if cases * (options.warmup + options.iterations) > 100_000:
        raise EdgeForgeError("benchmark exceeds invocation budget")
    process = psutil.Process()
    baseline = process.memory_info().rss
    runtime = create_adapter(bundle.model, config)
    peak = max(baseline, process.memory_info().rss)
    samples = []
    compared = 0
    matched = 0
    max_abs_error = 0.0
    finite = True
    for case in range(cases):
        inputs = preprocess(
            {s.name: vectors[f"input__{s.name}"][case] for s in config.inputs}, config
        )
        for _ in range(options.warmup):
            runtime.run(inputs)
        for _ in range(options.iterations):
            start = time.perf_counter_ns()
            outputs = runtime.run(inputs)
            samples.append((time.perf_counter_ns() - start) / 1_000_000)
            peak = max(peak, process.memory_info().rss)
            if set(outputs) != {s.name for s in config.outputs}:
                raise EdgeForgeError("runtime returned unexpected outputs")
            for spec in config.outputs:
                actual = np.asarray(outputs[spec.name])
                expected = vectors[f"output__{spec.name}"][case]
                if actual.shape != expected.shape or actual.dtype != expected.dtype:
                    raise EdgeForgeError("runtime output dtype or shape differs from contract")
                values_finite = bool(np.isfinite(actual).all())
                finite = finite and values_finite
                compared += actual.size
                if values_finite:
                    if actual.dtype.kind in "biu":
                        matches = actual == expected
                        # Python integers preserve differences above float64's exact range.
                        error = max(
                            (
                                abs(int(a) - int(b))
                                for a, b in zip(actual.flat, expected.flat, strict=True)
                            ),
                            default=0,
                        )
                    else:
                        matches = np.isclose(actual, expected, atol=options.atol, rtol=options.rtol)
                        error = float(np.max(np.abs(actual.astype("float64") - expected)))
                    matched += int(np.count_nonzero(matches))
                    max_abs_error = max(max_abs_error, error)
    return BenchmarkReport(
        edgeforge_version=__version__,
        bundle_sha256=bundle.sha256,
        measured_at=datetime.now(UTC).isoformat(),
        runtime=config.runtime,
        runtime_version=runtime.runtime_version,
        requested_provider=config.provider,
        active_providers=runtime.providers,
        threads=config.threads if config.runtime == "onnx" else None,
        options=options,
        cases=cases,
        latency_ms={
            "min": min(samples),
            "mean": float(np.mean(samples)),
            "p50": float(np.percentile(samples, 50)),
            "p95": float(np.percentile(samples, 95)),
            "max": max(samples),
        },
        memory={
            "rss_before_load_bytes": baseline,
            "rss_sampled_peak_bytes": peak,
            "rss_sampled_increase_bytes": peak - baseline,
            "scope": "whole-process RSS sampled after load and inference; not device VRAM",
        },
        storage={"model_bytes": len(bundle.model), "bundle_bytes": bundle.size_bytes},
        agreement={
            "passed": finite and matched == compared,
            "finite": finite,
            "elements_compared": compared,
            "elements_matching": matched,
            "fraction_matching": matched / compared,
            "max_abs_error": max_abs_error,
            "scope": "golden-output numerical agreement; not task-level accuracy",
        },
        device=capabilities(),
        measurement_scope=(
            "serial adapter call including tensor conversion and materialization; "
            "excludes model load, preprocessing, RSS sampling and comparison"
        ),
    )
