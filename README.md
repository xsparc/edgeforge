# EdgeForge

Portable edge AI deployment bundles and reproducible benchmarks for ONNX Runtime
and ExecuTorch. EdgeForge packages models, test vectors, preprocessing, and runtime
settings with integrity checks, then measures inference on the target device.

## Quick start

Python 3.11 or newer. Until the MVP PRs are merged, the complete implementation is
on `feat/service-interoperability`:

```sh
git clone --branch feat/service-interoperability https://github.com/xsparc/edgeforge.git
cd edgeforge
python -m venv .venv
# Activate the environment using your shell's activation command.
python -m pip install -e '.[onnx,api]'
edgeforge example demo
edgeforge benchmark demo/example.efb --output report.json
```

The example generates its model and test vectors locally. The JSON report includes
latency percentiles, sampled process RSS, storage size, numerical agreement, and
runtime/device capabilities. `edgeforge --help` lists all commands.

## MVP capabilities

- Deterministic bundles with versioned contracts, bounded assets, and SHA-256 checks.
- ONNX Runtime CPU inference, explicit execution providers, affine preprocessing,
  and dynamic INT8 quantization for supported constant-weight matrix operations.
- ExecuTorch adapter for pre-exported PTE programs, with a PyTorch export example.
- CLI, Python SDK, JSON Schemas, and an optional authenticated HTTP service.
- Tests, platform CI, architecture decisions, roadmap, and verification evidence.

The bundle is portable; a compiled model still needs a compatible runtime and
target. Output agreement is not task-level accuracy. RSS is not accelerator memory.
Accelerator and mobile validation remain future work. The service is for trusted
registered models; it is not a multi-tenant sandbox or managed SaaS product.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Benchmarking](docs/benchmarking.md) | Commands, metrics, quantization, runtime limits |
| [HTTP service](docs/service.md) | Authentication, OpenAPI, request limits, scaling boundary |
| [Architecture](docs/architecture/overview.md) | Contracts, runtime adapters, portability |
| [Python SDK example](examples/sdk.py) | Embed measurement in a worker |
| [ExecuTorch export](examples/export_executorch.py) | Export a local PyTorch model |
| [Schemas](schemas/) | Manifest, report, and OpenAPI contracts |
| [Roadmap](docs/roadmap/implementation-roadmap.md) | Three MVP slices and next decisions |
| [Validation](docs/governance/validation.md) | Executed checks and known gaps |
| [Security](docs/security.md) | Trust and resource boundaries |

## Development

```sh
python -m pip install -e '.[dev,onnx,api]'
python -m pytest -q
ruff check .
ruff format --check .
python scripts/check_governance.py --strict
python -m build
```

Native ExecuTorch validation uses a separate compatible PyTorch/ExecuTorch
environment; see the workflow and benchmarking guide. Keep exported schemas in
sync with `python scripts/export_schemas.py`. OpenSteward stewardship follows the
project instructions and evidence registry; merges and releases require review.

MIT licensed. Model and runtime licenses remain separate.
