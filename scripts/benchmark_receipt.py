"""Create or verify an offline receipt for two retained report files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

REPORT_MAX_BYTES = 256 * 1024
RECEIPT_MAX_BYTES = 1024


def read_bounded(path: Path, limit: int) -> bytes:
    """Read only one bounded, explicitly named regular file."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    # Check the open handle as well as the path: don't read a special file.
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("not a regular file")
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("unsupported file")
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        if (
            not 0 < len(data) <= limit
            or len(data) != before.st_size
            or (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            != (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        ):
            raise ValueError("empty, oversized or changed file")
    return data


def report_fingerprint(path: Path) -> dict[str, str | int]:
    data = read_bounded(path, REPORT_MAX_BYTES)
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def encode_receipt(before: Path, after: Path) -> str:
    receipt = {
        "schema_version": 1,
        "before": report_fingerprint(before),
        "after": report_fingerprint(after),
    }
    return json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="first retained report")
    parser.add_argument("--after", type=Path, required=True, help="second retained report")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--verify", type=Path, metavar="RECEIPT", help="compare a saved receipt")
    actions.add_argument("--output", type=Path, metavar="RECEIPT", help="write a new receipt")
    args = parser.parse_args(argv)
    try:
        expected = encode_receipt(args.before, args.after)
        if args.verify is not None:
            # This format is canonical ASCII JSON. Exact bytes reject unknown
            # fields, alternate encodings and oversized input without parsing.
            received = read_bounded(args.verify, RECEIPT_MAX_BYTES)
    except (OSError, ValueError):
        print("receipt: input unavailable, unsupported, or outside size limits", file=sys.stderr)
        return 2
    if args.verify is not None:
        # Text-mode redirection on Windows may translate LF to CRLF.
        normalized = received[:-2] + b"\n" if received.endswith(b"\r\n") else received
        if normalized != expected.encode("ascii"):
            print("receipt: reports do not match the canonical receipt", file=sys.stderr)
            return 1
        print("receipt: report bytes match")
    elif args.output is not None:
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(args.output, flags, 0o600), "wb") as handle:
                handle.write(expected.encode("ascii"))
        except OSError:
            print("receipt: could not write a new receipt file", file=sys.stderr)
            return 2
    else:
        print(expected, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
