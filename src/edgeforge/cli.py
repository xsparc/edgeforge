"""Small CLI; JSON on stdout and stable error categories on stderr."""

import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from .bundle import MAX_BUNDLE_BYTES, MAX_MODEL_BYTES, MAX_VECTOR_BYTES, pack, read_bounded, unpack
from .contracts import BenchmarkOptions, Manifest, ModelConfig
from .errors import EdgeForgeError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="edgeforge", description="Portable edge AI bundles")
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("pack", help="Build a reproducible deployment bundle")
    build.add_argument("--model", type=Path, required=True)
    build.add_argument("--vectors", type=Path, required=True)
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--quantize", choices=["none", "dynamic-int8"], default="none")
    inspect = commands.add_parser("inspect", help="Verify and inspect a bundle")
    inspect.add_argument("bundle", type=Path)
    commands.add_parser("schema", help="Print the manifest JSON Schema")
    commands.add_parser("doctor", help="Report runtime versions and registered providers")
    demo = commands.add_parser("example", help="Generate a small runnable ONNX example")
    demo.add_argument("directory", type=Path)
    bench = commands.add_parser("benchmark", help="Measure a bundle on this device")
    bench.add_argument("bundle", type=Path)
    bench.add_argument("--warmup", type=int, default=5)
    bench.add_argument("--iterations", type=int, default=50)
    bench.add_argument("--atol", type=float, default=1e-5)
    bench.add_argument("--rtol", type=float, default=1e-4)
    bench.add_argument("--output", type=Path)
    serve = commands.add_parser("serve", help="Serve trusted registered bundles over HTTP")
    serve.add_argument("--registry", type=Path, required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8741)
    return root


def run(args: argparse.Namespace) -> dict:
    if args.command == "serve":
        try:
            import uvicorn

            from .service import create_app
        except ImportError as exc:
            raise EdgeForgeError("install the api extra to serve bundles") from exc
        try:
            registry = json.loads(read_bounded(args.registry, 65536))
        except (ValueError, UnicodeError) as exc:
            raise EdgeForgeError("invalid registry JSON") from exc
        if not isinstance(registry, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in registry.items()
        ):
            raise EdgeForgeError("registry must map bundle IDs to file paths")
        paths = {name: args.registry.resolve().parent / path for name, path in registry.items()}
        app = create_app(paths, os.environ.get("EDGEFORGE_API_TOKEN", ""))
        if not 1 <= args.port <= 65535:
            raise EdgeForgeError("invalid service port")
        uvicorn.run(app, host=args.host, port=args.port, workers=1, access_log=False)
        return {"status": "stopped"}
    if args.command == "doctor":
        from .capabilities import capabilities

        return capabilities()
    if args.command == "example":
        from .example import write_example

        return write_example(args.directory)
    if args.command == "benchmark":
        from .benchmark import benchmark

        bundle = unpack(read_bounded(args.bundle, MAX_BUNDLE_BYTES))
        options = BenchmarkOptions(
            warmup=args.warmup, iterations=args.iterations, atol=args.atol, rtol=args.rtol
        )
        report = benchmark(bundle, options).model_dump()
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
        return report
    if args.command == "schema":
        return Manifest.model_json_schema()
    if args.command == "pack":
        config = ModelConfig.model_validate_json(read_bounded(args.config, 65536))
        from .bundle import digest

        model = read_bounded(args.model, MAX_MODEL_BYTES)
        source_digest = digest(model)
        if args.quantize != "none":
            if config.runtime != "onnx":
                raise EdgeForgeError("dynamic INT8 requires an ONNX model")
            from .quantize import dynamic_int8

            model = dynamic_int8(model)
        data = pack(
            model,
            read_bounded(args.vectors, MAX_VECTOR_BYTES),
            config,
            quantization=args.quantize,
            source_digest=source_digest,
        )
        # Exclusive creation prevents accidental replacement of a model or previous result.
        with args.output.open("xb") as stream:
            stream.write(data)
        bundle = unpack(data)
    else:
        bundle = unpack(read_bounded(args.bundle, MAX_BUNDLE_BYTES))
    return {
        "bundle_sha256": bundle.sha256,
        "size_bytes": bundle.size_bytes,
        "manifest": bundle.manifest.model_dump(),
    }


def main() -> int:
    args = parser().parse_args()
    try:
        result = run(args)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 3 if result.get("agreement", {}).get("passed") is False else 0
    except (EdgeForgeError, ValidationError, OSError) as exc:
        code = "io_error" if isinstance(exc, OSError) else "invalid_input"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
