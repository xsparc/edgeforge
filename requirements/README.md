# Reproducible ONNX and service environment

`onnx-api.txt` pins transitive runtime and development dependencies with hashes
and platform/Python markers. CI installs it with pip's `--require-hashes` mode,
then installs the local project without re-resolving dependencies. It covers the
core, ONNX, API, and development extras; ExecuTorch uses a separate compatible
PyTorch environment as documented in the CI workflow.

To reproduce:

```sh
python -m pip install --require-hashes -r requirements/onnx-api.txt
python -m pip install --no-deps -e .
```

To refresh intentionally, run `uv pip compile pyproject.toml --extra onnx --extra api --extra dev --universal --generate-hashes --no-header --no-annotate --output-file requirements/onnx-api.txt`, then run the platform CI matrix and review dependency changes.

The lock pins package artifacts, not operating-system images, hardware, native
drivers, or thermal conditions. Build isolation resolves the declared build
backend independently. Record runtime versions with every benchmark.
