# Benchmarking

Install an ONNX environment with `python -m pip install -e '.[onnx]'`, then:

```sh
edgeforge example demo
edgeforge inspect demo/example.efb
edgeforge benchmark demo/example.efb --warmup 5 --iterations 50 --output report.json
edgeforge doctor
```

The fixture is generated locally with two cases and a small constant-weight
matrix multiplication. No pretrained weights or dataset downloads are needed.
Example directories and output files must not already exist.

To quantize a supported ONNX model:

```sh
edgeforge pack --model demo/model.onnx --vectors demo/vectors.npz --config demo/config.json --quantize dynamic-int8 --output demo/int8.efb
edgeforge benchmark demo/int8.efb --atol 0.05 --rtol 0.02
```

The MVP quantizes constant-weight MatMul/Gemm operations using ONNX Runtime's
dynamic INT8 path. Unsupported or unchanged models fail. Quantization preserves
the original model digest. Golden vectors remain the reference, and tolerances
are explicit in the report. A smaller model is not necessarily a faster model.

## Metrics

Each case is preprocessed once, warmed up, and measured for the requested number
of iterations. Latency samples cover the synchronous adapter call, including
input conversion and output materialization. Model loading, preprocessing,
memory sampling, and correctness comparisons are outside the timed interval.
Percentiles pool all measured calls across cases; they are not confidence intervals.

RSS is sampled before loading, after loading, and after each inference. This is
whole-process resident memory, including Python and runtime libraries. Short-lived
allocation peaks can be missed. It is not GPU memory, model-only RAM, or an OS
high-water mark. Storage is the exact model and bundle byte count.

Floating outputs use `abs(actual - expected) <= atol + rtol * abs(expected)`.
Integer and boolean outputs use exact comparison. Every timed result is checked;
nonfinite results fail agreement. Shape or dtype mismatches are errors. Agreement
is a regression metric, not classification accuracy. CLI exit codes: 0 success,
2 invalid input/I/O/runtime error, 3 completed benchmark with failed agreement.

## Runtime support

ONNX accepts self-contained models with static numeric tensor I/O. External data
and shape mismatches are rejected before execution. The default provider is CPU;
explicit unavailable providers fail. CPU fallback is disabled for non-CPU requests.
Registered providers describe the runtime build, not physical hardware validation.

ExecuTorch accepts a pre-exported self-contained `.pte` program with a `forward`
method. Input and output specification order is positional. Set `runtime` to
`executorch` and `provider` to `portable`. Export/delegate selection and quantization
belong to the PyTorch/ExecuTorch export workflow. Arbitrary checkpoint loading is
not part of the CLI. `threads` must stay at 1; the report uses null because the
compiled runtime's threading cannot be controlled by this adapter. Delegates are
reported as `compiled-program`, without claiming which device executed nodes.

Use one benchmark process per device, record power/thermal settings externally,
and compare matching runtime versions and workloads. The MVP does not attest
thermal state, power use, accelerator placement, or cross-device equivalence.
