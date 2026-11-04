"""Authenticated, bounded HTTP transport for trusted registered bundles."""

import hmac
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import Field

from .benchmark import BenchmarkReport, benchmark
from .bundle import MAX_BUNDLE_BYTES, read_bounded, unpack
from .capabilities import capabilities
from .contracts import BenchmarkOptions, Contract, Name
from .errors import EdgeForgeError


class BenchmarkRequest(Contract):
    bundle_id: Name
    options: BenchmarkOptions = Field(default_factory=BenchmarkOptions)


class RequestBoundary:
    """Authenticate and cap even chunked bodies before JSON parsing."""

    def __init__(self, app, token: str):
        self.app = app
        self.authorization = f"Bearer {token}".encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if scope["path"] != "/healthz" and not hmac.compare_digest(
            headers.get(b"authorization", b""), self.authorization
        ):
            response = JSONResponse(
                {"error": "unauthorized"}, 401, headers={"WWW-Authenticate": "Bearer"}
            )
            return await response(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > 8192:
                return await JSONResponse({"error": "request_too_large"}, 413)(scope, receive, send)
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


@dataclass(frozen=True)
class RegisteredBundle:
    path: Path
    sha256: str


def create_app(registry: dict[str, Path], token: str) -> FastAPI:
    """Construct a single-worker service; registration is an operator action."""
    if not token.isascii() or len(token) < 32 or len(registry) > 64:
        raise EdgeForgeError(
            "use an ASCII bearer token of at least 32 characters and at most 64 bundles"
        )
    registered = {}
    for name, path in registry.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name):
            raise EdgeForgeError("invalid registered bundle ID")
        bundle = unpack(read_bounded(Path(path), MAX_BUNDLE_BYTES))
        registered[name] = RegisteredBundle(Path(path).resolve(), bundle.sha256)
    gate = threading.Lock()
    app = FastAPI(
        title="EdgeForge",
        version="1",
        docs_url=None,
        redoc_url=None,
        openapi_url="/v1/openapi.json",
    )
    app.add_middleware(RequestBoundary, token=token)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"error": "invalid_request"}, 422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": exc.detail}, exc.status_code, headers=exc.headers)

    @app.get("/healthz")
    def health():
        return {"status": "ok", "schema_version": 1}

    @app.get("/v1/capabilities")
    def device():
        return capabilities()

    @app.get("/v1/bundles")
    def bundles():
        return {
            "schema_version": 1,
            "bundles": [
                {"id": name, "sha256": item.sha256} for name, item in sorted(registered.items())
            ],
        }

    @app.post("/v1/benchmarks", response_model=BenchmarkReport)
    def measure(request: BenchmarkRequest):
        if request.options.iterations > 1000 or request.options.warmup > 20:
            raise HTTPException(422, "service_budget_exceeded")
        item = registered.get(request.bundle_id)
        if item is None:
            raise HTTPException(404, "bundle_not_found")
        if not gate.acquire(blocking=False):
            raise HTTPException(503, "device_busy", headers={"Retry-After": "1"})
        try:
            bundle = unpack(read_bounded(item.path, MAX_BUNDLE_BYTES))
            if bundle.sha256 != item.sha256:
                raise HTTPException(409, "registered_bundle_changed")
            return benchmark(bundle, request.options)
        except HTTPException:
            raise
        except Exception:
            # Runtime exception chains may include model paths or native library details.
            raise HTTPException(422, "benchmark_failed") from None
        finally:
            gate.release()

    def openapi():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            schema.setdefault("components", {})["securitySchemes"] = {
                "BearerAuth": {"type": "http", "scheme": "bearer"}
            }
            for path, operations in schema["paths"].items():
                if path != "/healthz":
                    for operation in operations.values():
                        operation["security"] = [{"BearerAuth": []}]
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi
    return app
