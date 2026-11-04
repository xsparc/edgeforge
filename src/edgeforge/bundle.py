"""Deterministic ZIP transport. Bundles are verified without filesystem extraction."""

import hashlib
import io
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from .contracts import Asset, Manifest, ModelConfig
from .errors import EdgeForgeError

MAX_MODEL_BYTES = 512 * 1024 * 1024
MAX_VECTOR_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = MAX_MODEL_BYTES + MAX_VECTOR_BYTES + 65536


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if not data or len(data) > limit:
        raise EdgeForgeError("asset is empty or exceeds its size limit")
    return data


def load_vectors(data: bytes, config: ModelConfig) -> dict[str, np.ndarray]:
    """Each array has a leading case axis followed by the declared tensor shape."""
    expected = {
        f"{side}__{s.name}": s
        for side, specs in (("input", config.inputs), ("output", config.outputs))
        for s in specs
    }
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if (
                len(entries) != len(expected)
                or {i.filename for i in entries} != {f"{k}.npy" for k in expected}
                or sum(i.file_size for i in entries) > MAX_VECTOR_BYTES
                or any(i.flag_bits & 1 for i in entries)
            ):
                raise EdgeForgeError("invalid or oversized vector archive")
            # Validate headers before NumPy can allocate using an attacker-controlled shape.
            for name, spec in expected.items():
                with archive.open(f"{name}.npy") as stream:
                    version = np.lib.format.read_magic(stream)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                    else:
                        raise EdgeForgeError("unsupported vector encoding")
                    if (
                        len(shape) != len(spec.shape) + 1
                        or shape[1:] != tuple(spec.shape)
                        or not 1 <= shape[0] <= 1024
                        or dtype != np.dtype(spec.dtype)
                        or dtype.hasobject
                        or math.prod(shape) * dtype.itemsize > MAX_VECTOR_BYTES
                        or stream.tell() + math.prod(shape) * dtype.itemsize
                        != archive.getinfo(f"{name}.npy").file_size
                    ):
                        raise EdgeForgeError("invalid vector header")
        with np.load(io.BytesIO(data), allow_pickle=False) as arrays:
            vectors = {name: arrays[name] for name in expected}
        cases = set()
        for name, spec in expected.items():
            array = vectors[name]
            if (
                array.dtype != np.dtype(spec.dtype)
                or array.shape[1:] != tuple(spec.shape)
                or array.ndim != len(spec.shape) + 1
                or not np.isfinite(array).all()
            ):
                raise EdgeForgeError("vector tensor does not match its declared dtype or shape")
            cases.add(array.shape[0])
        if len(cases) != 1 or not 1 <= next(iter(cases)) <= 1024:
            raise EdgeForgeError("vectors require 1 to 1024 matching cases")
        return vectors
    except (
        ValueError,
        KeyError,
        OSError,
        zipfile.BadZipFile,
        EOFError,
        RuntimeError,
        NotImplementedError,
        OverflowError,
    ) as exc:
        raise EdgeForgeError("invalid test vectors; expected finite numeric NPZ arrays") from exc


def deterministic_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return buffer.getvalue()


def pack(
    model: bytes,
    vectors: bytes,
    config: ModelConfig,
    *,
    quantization: str = "none",
    source_digest: str | None = None,
) -> bytes:
    if not 0 < len(model) <= MAX_MODEL_BYTES or not 0 < len(vectors) <= MAX_VECTOR_BYTES:
        raise EdgeForgeError("asset is empty or exceeds its size limit")
    load_vectors(vectors, config)
    manifest = Manifest(
        config=config,
        model=Asset(sha256=digest(model), size_bytes=len(model)),
        vectors=Asset(sha256=digest(vectors), size_bytes=len(vectors)),
        quantization=quantization,
        source_model_sha256=source_digest or digest(model),
    )
    return deterministic_zip(
        {
            "manifest.json": canonical_json(manifest.model_dump()),
            "model.bin": model,
            "vectors.npz": vectors,
        }
    )


@dataclass(frozen=True)
class Bundle:
    sha256: str
    size_bytes: int
    manifest: Manifest
    model: bytes
    vectors: bytes


def unpack(data: bytes) -> Bundle:
    if not 0 < len(data) <= MAX_BUNDLE_BYTES:
        raise EdgeForgeError("bundle exceeds size limit")
    limits = {"manifest.json": 65536, "model.bin": MAX_MODEL_BYTES, "vectors.npz": MAX_VECTOR_BYTES}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) != 3 or {i.filename for i in entries} != set(limits):
                raise EdgeForgeError("bundle must contain exactly its three declared files")
            for entry in entries:
                if (
                    entry.file_size > limits[entry.filename]
                    or entry.flag_bits & 1
                    or (entry.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise EdgeForgeError("unsupported bundle entry")
            files = {name: archive.read(name) for name in limits}
        manifest = Manifest.model_validate_json(files["manifest.json"])
        for name, asset in (("model.bin", manifest.model), ("vectors.npz", manifest.vectors)):
            if len(files[name]) != asset.size_bytes or digest(files[name]) != asset.sha256:
                raise EdgeForgeError("bundle integrity check failed")
        load_vectors(files["vectors.npz"], manifest.config)
        return Bundle(digest(data), len(data), manifest, files["model.bin"], files["vectors.npz"])
    except (
        ValidationError,
        ValueError,
        KeyError,
        OSError,
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        OverflowError,
    ) as exc:
        raise EdgeForgeError("invalid bundle or failed integrity check") from exc
