import io
import zipfile

import numpy as np
import pytest
from pydantic import ValidationError

from edgeforge.bundle import deterministic_zip, load_vectors, pack, unpack
from edgeforge.cli import main
from edgeforge.contracts import ModelConfig
from edgeforge.errors import EdgeForgeError


def test_reproducible_roundtrip(config, vectors):
    first = pack(b"model", vectors, config)
    assert first == pack(b"model", vectors, config)
    result = unpack(first)
    assert result.model == b"model"
    assert result.manifest.config == config


@pytest.mark.parametrize("change", ["model", "traversal", "duplicate", "manifest"])
def test_rejects_tampering(config, vectors, change):
    with zipfile.ZipFile(io.BytesIO(pack(b"model", vectors, config))) as archive:
        files = {n: archive.read(n) for n in archive.namelist()}
    if change == "model":
        files["model.bin"] = b"other"
    elif change == "traversal":
        files["../model.bin"] = files.pop("model.bin")
    elif change == "manifest":
        files["manifest.json"] = b"{}"
    data = deterministic_zip(files)
    if change == "duplicate":
        stream = io.BytesIO(data)
        with zipfile.ZipFile(stream, "a") as archive, pytest.warns(UserWarning):
            archive.writestr("model.bin", b"model")
        data = stream.getvalue()
    with pytest.raises(EdgeForgeError):
        unpack(data)


@pytest.mark.parametrize(
    "value",
    [
        np.array([[object(), object()]]),
        np.array([[float("nan"), 1]], dtype="float32"),
        np.ones((1, 3), dtype="float32"),
        np.ones((1, 2), dtype="int32"),
    ],
)
def test_rejects_unsafe_or_mismatched_vectors(config, value):
    buffer = io.BytesIO()
    np.savez(buffer, input__x=value, output__y=np.ones((1, 2), dtype="float32"))
    with pytest.raises(EdgeForgeError):
        load_vectors(buffer.getvalue(), config)


@pytest.mark.parametrize(
    "update",
    [
        {"unknown": True},
        {"threads": 0},
        {"schema_version": 2},
        {"preprocessing": {"missing": {"scale": 2.0}}},
    ],
)
def test_strict_contract(config, update):
    with pytest.raises(ValidationError):
        ModelConfig.model_validate(config.model_dump() | update)


def test_cli_errors_are_path_free(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["edgeforge", "inspect", str(tmp_path / "private.efb")])
    assert main() == 2
    assert capsys.readouterr().err.strip() == '{"error": "io_error"}'


def test_rejects_allocation_bomb_before_numpy_load(config, vectors, monkeypatch):
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        buffer, {"descr": "<f4", "fortran_order": False, "shape": (10**12, 2)}
    )
    with zipfile.ZipFile(io.BytesIO(vectors)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["input__x.npy"] = buffer.getvalue()
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("must reject before allocation"))
    with pytest.raises(EdgeForgeError):
        load_vectors(deterministic_zip(files), config)
