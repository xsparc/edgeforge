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
    commands.add_parser("report-schema", help="Print the strict retained-report JSON Schema")
    commands.add_parser("comparison-schema", help="Print the descriptive comparison JSON Schema")
    retained = commands.add_parser(
        "comparison-check", help="Check a retained comparison without execution"
    )
    retained.add_argument("comparison", type=Path)

    identity = commands.add_parser(
        "comparison-identity", help="Print a canonical comparison digest"
    )
    identity.add_argument("comparison", type=Path)
    canonical = commands.add_parser(
        "comparison-canonical", help="Export canonical retained comparison bytes"
    )
    canonical.add_argument("comparison", type=Path)
    canonical.add_argument("--output", required=True, type=Path)

    verify = commands.add_parser(
        "comparison-verify", help="Verify a comparison against two reports"
    )
    verify.add_argument("before", type=Path)
    verify.add_argument("after", type=Path)
    verify.add_argument("comparison", type=Path)
    verify.add_argument("--format", choices=["json", "csv"], default="json")
    render = commands.add_parser("comparison-html", help="Render a checked retained comparison")
    render.add_argument("comparison", type=Path)
    render.add_argument("--output", required=True, type=Path)
    for command in (retained, canonical, render):
        expected = command.add_mutually_exclusive_group()
        expected.add_argument("--expected-sha256")
        expected.add_argument("--identity", type=Path)
    commands.add_parser("comparison-identity-schema", help="Print the retained identity schema")
    verify_identity = commands.add_parser(
        "comparison-verify-identity", help="Verify a comparison against an identity file"
    )
    verify_identity.add_argument("comparison", type=Path)
    verify_identity.add_argument("identity", type=Path)
    review = commands.add_parser(
        "comparison-review", help="Render a comparison checked against explicit reports"
    )
    review.add_argument("comparison", type=Path)
    review.add_argument("before", type=Path)
    review.add_argument("after", type=Path)
    review.add_argument("--identity", type=Path)
    review.add_argument("--output", required=True, type=Path)
    review.add_argument("--format", choices=["html", "csv"], default="html")
    compare = commands.add_parser(
        "report-compare", help="Compare two retained reports without execution"
    )
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--format", choices=["json", "csv"], default="json")
    compare.add_argument("--output", type=Path)
    check = commands.add_parser("report-check", help="Validate a saved report without execution")
    check.add_argument("report", type=Path)
    check.add_argument("--bundle", type=Path, help="Also check source identity and declared counts")
    export = commands.add_parser("report-csv", help="Export a validated report as UTF-8 CSV")
    export.add_argument("report", type=Path)
    export.add_argument("--output", type=Path)
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
    if args.command == "comparison-identity-schema":
        from .comparison_identity import ComparisonIdentity

        return ComparisonIdentity.model_json_schema()
    if args.command == "comparison-schema":
        from .comparison import ReportComparison

        return ReportComparison.model_json_schema()
    if args.command in {"report-schema", "report-check"}:
        from .reports import MAX_REPORT_BYTES, ReportEvidence, validate_report, verify_report_bundle

        if args.command == "report-schema":
            return ReportEvidence.model_json_schema()
        report = validate_report(read_bounded(args.report, MAX_REPORT_BYTES))
        if args.bundle:
            verify_report_bundle(report, unpack(read_bounded(args.bundle, MAX_BUNDLE_BYTES)))
        return {
            "schema_version": 1,
            "valid": True,
            "bundle_checked": args.bundle is not None,
            "interpretation": "local_consistency_not_measurement_attestation",
        }
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
        if args.command in {
            "comparison-check",
            "comparison-verify",
            "comparison-html",
            "comparison-identity",
            "comparison-canonical",
            "comparison-verify-identity",
            "comparison-review",
        }:
            from .comparison import MAX_COMPARISON_BYTES, render_comparison_csv
            from .comparison_review import (
                read_comparison,
                read_source,
                render_comparison_html,
                verify_comparison,
            )
            from .reports import MAX_REPORT_BYTES

            raw = read_bounded(args.comparison, MAX_COMPARISON_BYTES)
            if args.command == "comparison-verify":
                verify_comparison(
                    read_source(read_bounded(args.before, MAX_REPORT_BYTES)),
                    read_source(read_bounded(args.after, MAX_REPORT_BYTES)),
                    raw,
                    format=args.format,
                )
                print(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "verified": True,
                            "interpretation": "local_source_consistency_only",
                        }
                    )
                )
            else:
                comparison = read_comparison(raw)
                if args.command == "comparison-review":
                    verify_comparison(
                        read_source(read_bounded(args.before, MAX_REPORT_BYTES)),
                        read_source(read_bounded(args.after, MAX_REPORT_BYTES)),
                        raw,
                    )
                from .comparison_identity import (
                    MAX_IDENTITY_BYTES,
                    canonical_comparison,
                    comparison_identity,
                    read_identity,
                    verify_expected_identity,
                    verify_identity_record,
                )

                if getattr(args, "identity", None) is not None:
                    verify_identity_record(
                        comparison, read_identity(read_bounded(args.identity, MAX_IDENTITY_BYTES))
                    )
                if getattr(args, "expected_sha256", None) is not None:
                    verify_expected_identity(comparison, args.expected_sha256)
                if args.command in {"comparison-identity", "comparison-canonical"}:
                    identity = comparison_identity(comparison)
                    if args.command == "comparison-canonical":
                        output = canonical_comparison(comparison)
                        with args.output.open("xb") as stream:
                            stream.write(output)
                    print(json.dumps(identity))
                elif args.command in {"comparison-html", "comparison-review"}:
                    output = (
                        render_comparison_csv(comparison)
                        if args.command == "comparison-review" and args.format == "csv"
                        else render_comparison_html(comparison)
                    ).encode("utf-8")
                    if len(output) > MAX_COMPARISON_BYTES:
                        raise EdgeForgeError("review exceeds byte limit")
                    with args.output.open("xb") as stream:
                        stream.write(output)
                else:
                    print(
                        json.dumps(
                            {
                                "schema_version": 1,
                                "valid": True,
                                "interpretation": "local_consistency_only",
                            }
                        )
                    )
            return 0
        if args.command == "report-compare":
            from .comparison import MAX_COMPARISON_BYTES, compare_reports, render_comparison_csv
            from .reports import MAX_REPORT_BYTES, validate_report

            comparison = compare_reports(
                validate_report(read_bounded(args.before, MAX_REPORT_BYTES)),
                validate_report(read_bounded(args.after, MAX_REPORT_BYTES)),
            )
            output = (
                render_comparison_csv(comparison)
                if args.format == "csv"
                else comparison.model_dump_json(indent=2) + "\n"
            ).encode("utf-8")
            if len(output) > MAX_COMPARISON_BYTES:
                raise EdgeForgeError("comparison exceeds byte limit")
            if args.output:
                with args.output.open("xb") as stream:
                    stream.write(output)
            elif hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(output)
            else:
                print(output.decode("utf-8"), end="")
            return 0
        if args.command == "report-csv":
            from .reports import MAX_REPORT_BYTES, render_report_csv, validate_report

            output = render_report_csv(validate_report(read_bounded(args.report, MAX_REPORT_BYTES)))
            if args.output:
                with args.output.open("xb") as stream:
                    stream.write(output.encode("utf-8"))
            elif hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(output.encode("utf-8"))
            else:
                print(output, end="")
            return 0
        result = run(args)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 3 if result.get("agreement", {}).get("passed") is False else 0
    except (EdgeForgeError, ValidationError, OSError) as exc:
        code = "io_error" if isinstance(exc, OSError) else "invalid_input"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
