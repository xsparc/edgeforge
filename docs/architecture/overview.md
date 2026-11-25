# Architecture

EdgeForge turns a trusted local ONNX model or exported ExecuTorch program and
numeric test vectors into a portable bundle. It measures that bundle where it
runs. It does not implement an inference engine or claim that a host benchmark
predicts another device's performance.

## Boundaries

`contracts` defines versioned JSON models. `bundle` validates and hashes assets
without extracting archives. Runtime adapters load model bytes and expose one
synchronous inference interface. The benchmark layer owns warmup, measurement,
output comparison, and capability reporting. CLI and optional HTTP transports
call the same SDK functions.

```mermaid
flowchart LR
    Model[Model + NPZ vectors + JSON configuration] --> Bundle[Validated bundle]
    Bundle --> Worker[Benchmark worker]
    Worker --> ORT[ONNX Runtime]
    Worker --> ET[ExecuTorch]
    Worker --> Report[Versioned JSON report]
    CLI[CLI / Python SDK] --> Worker
    API[Optional HTTP API] --> Worker
```

## Portability and repeatability

An `.efb` file contains exactly `manifest.json`, `model.bin`, and `vectors.npz`.
ZIP entries use fixed metadata and no compression. The manifest records asset
sizes and SHA-256 digests, input/output order, dtypes, shapes, preprocessing,
thread settings, runtime selection, and quantization provenance. Identical
inputs produce identical bundle bytes within the supported format version.
Benchmark timing is inherently variable and is never part of the bundle hash.
Runtime and dependency versions belong in reports and environment lock files.

Each NPZ array has a case axis, then the exact tensor shape. Names are
`input__<name>` or `output__<name>`. Pickled arrays, nonfinite values, unknown
entries, inconsistent cases, and excess resource sizes are rejected.
Preprocessing is `(input * scale) + offset`, in the declared floating dtype.
Golden outputs represent the post-preprocessing model result.

## SaaS interoperability and scaling

The Python SDK and JSON Schema are the stable integration boundary. Artifact
digests provide cache and object-store keys; reports reference the exact bundle.
The optional API accepts registered bundle IDs, never arbitrary filesystem paths,
URLs, Python modules, or model uploads. It is a bounded single-worker service
for trusted integration, with a documented path to queued isolated workers.
Independent worker processes scale across devices; benchmark concurrency on
one device would invalidate timing and is intentionally restricted.

Storage, identity, billing, distributed scheduling, tenant isolation, cloud
deployment, and model registries stay outside the MVP. An eventual control plane
can pass immutable bundles through object storage and retain reports by digest.

## Performance and security

Load once, warm up separately, measure inference only, and report the scope of
every metric. RSS includes the whole process; it is not accelerator memory.
Provider availability does not prove that every node executes on that provider.
Native runtime parsing is not a security sandbox. Use trusted models and isolate
workers before processing third-party models. See [security](../security.md).
