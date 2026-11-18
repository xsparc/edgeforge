import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("onnxruntime")

from fastapi.testclient import TestClient

from edgeforge.bundle import pack
from edgeforge.errors import EdgeForgeError
from edgeforge.example import example_assets
from edgeforge.service import create_app

TOKEN = "test-only-token-" + "x" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def service(tmp_path):
    model, vectors, config = example_assets()
    path = tmp_path / "example.efb"
    path.write_bytes(pack(model, vectors, config))
    with TestClient(create_app({"example": path}, TOKEN)) as client:
        yield client, path


def test_authentication_health_and_openapi(service):
    client, _ = service
    assert client.get("/healthz").json()["status"] == "ok"
    for path in ("/v1/bundles", "/v1/capabilities", "/v1/openapi.json"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=AUTH).status_code == 200
    schema = client.get("/v1/openapi.json", headers=AUTH).json()
    assert schema["paths"]["/v1/benchmarks"]["post"]["security"] == [{"BearerAuth": []}]


def test_native_benchmark_and_registry_are_path_free(service):
    client, path = service
    listing = client.get("/v1/bundles", headers=AUTH)
    assert str(path) not in listing.text
    result = client.post(
        "/v1/benchmarks",
        headers=AUTH,
        json={"bundle_id": "example", "options": {"iterations": 2, "warmup": 0}},
    )
    assert result.status_code == 200
    assert result.json()["agreement"]["passed"] is True
    assert result.json()["bundle_sha256"] == listing.json()["bundles"][0]["sha256"]


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"bundle_id": "missing"}, 404),
        ({"bundle_id": "../private"}, 422),
        ({"bundle_id": "example", "url": "https://invalid.example"}, 422),
        ({"bundle_id": "example", "options": {"iterations": 1001}}, 422),
        ({"bundle_id": "example", "options": {"atol": -1.0}}, 422),
    ],
)
def test_rejects_invalid_requests(service, payload, code):
    client, _ = service
    result = client.post("/v1/benchmarks", headers=AUTH, json=payload)
    assert result.status_code == code
    assert "private" not in result.text


def test_rejects_changed_registration(service):
    client, path = service
    model, vectors, config = example_assets()
    config.threads = 2
    path.write_bytes(pack(model, vectors, config))
    result = client.post("/v1/benchmarks", headers=AUTH, json={"bundle_id": "example"})
    assert result.status_code == 409


def test_bounds_streaming_body(service):
    client, _ = service
    result = client.post("/v1/benchmarks", headers=AUTH, content=iter([b"x" * 5000, b"x" * 5000]))
    assert result.status_code == 413


def test_native_failure_is_sanitized_and_releases_worker(service, monkeypatch):
    client, _ = service

    def fail(*args):
        raise RuntimeError("sensitive-host-path")

    monkeypatch.setattr("edgeforge.service.benchmark", fail)
    for _ in range(2):
        result = client.post("/v1/benchmarks", headers=AUTH, json={"bundle_id": "example"})
        assert result.status_code == 422
        assert result.json() == {"error": "benchmark_failed"}


def test_concurrent_benchmarks_have_backpressure(service, monkeypatch):
    client, _ = service
    entered, release = threading.Event(), threading.Event()

    def block(*args):
        entered.set()
        assert release.wait(5)
        raise RuntimeError("test completion")

    monkeypatch.setattr("edgeforge.service.benchmark", block)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            client.post, "/v1/benchmarks", headers=AUTH, json={"bundle_id": "example"}
        )
        try:
            assert entered.wait(5)
            second = client.post("/v1/benchmarks", headers=AUTH, json={"bundle_id": "example"})
            assert second.status_code == 503
            assert second.headers["Retry-After"] == "1"
        finally:
            release.set()
        assert first.result().status_code == 422


def test_requires_nontrivial_token():
    with pytest.raises(EdgeForgeError):
        create_app({}, "short")
