"""Small CLI; JSON on stdout and stable error categories on stderr."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .bundle import MAX_BUNDLE_BYTES, MAX_MODEL_BYTES, MAX_VECTOR_BYTES, pack, read_bounded, unpack
from .contracts import Manifest, ModelConfig
from .errors import EdgeForgeError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="edgeforge", description="Portable edge AI bundles")
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("pack", help="Build a reproducible deployment bundle")
    build.add_argument("--model", type=Path, required=True)
    build.add_argument("--vectors", type=Path, required=True)
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    inspect = commands.add_parser("inspect", help="Verify and inspect a bundle")
    inspect.add_argument("bundle", type=Path)
    commands.add_parser("schema", help="Print the manifest JSON Schema")
    return root


def run(args: argparse.Namespace) -> dict:
    if args.command == "schema":
        return Manifest.model_json_schema()
    if args.command == "pack":
        config = ModelConfig.model_validate_json(read_bounded(args.config, 65536))
        data = pack(
            read_bounded(args.model, MAX_MODEL_BYTES),
            read_bounded(args.vectors, MAX_VECTOR_BYTES),
            config,
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
        print(json.dumps(run(args), indent=2, allow_nan=False))
        return 0
    except (EdgeForgeError, ValidationError, OSError) as exc:
        code = "io_error" if isinstance(exc, OSError) else "invalid_input"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
