# ADR 0001: Portable artifacts over existing inference runtimes

Status: accepted

Use a Python library with thin CLI and optional HTTP transports. Define a bounded,
versioned bundle and report contract. Use ONNX Runtime sessions and ExecuTorch
program methods behind adapters. Default to explicit CPU execution with one
thread; compiled ExecuTorch delegates remain a property of the exported program.

This follows the initial product scope. Current primary documentation confirms
the [ONNX provider interface](https://onnxruntime.ai/docs/execution-providers/)
and [ExecuTorch program API](https://docs.pytorch.org/executorch/stable/runtime-python-api-reference.html).
The research brief is advisory; no additional product authority is derived from it.

A new inference engine would duplicate kernels, device integration, and runtime
maintenance. A hosted monolith would couple deployment policy to the portable
toolkit. The chosen boundary leaves those responsibilities separate while
providing executable integration contracts now.

Tradeoffs: Python adds host overhead, optional runtime wheels have different
platform coverage, and native target benchmarks still require physical devices.
Dynamic shapes, external weight files, custom operators, and arbitrary model
importers are deferred until explicit compatibility and resource tests exist.
