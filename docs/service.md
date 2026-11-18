# Service integration

Install `python -m pip install -e '.[onnx,api]'`. Generate the example and create
`registry.json` beside the example directory:

```json
{"example": "demo/example.efb"}
```

Provide a randomly generated ASCII token through `EDGEFORGE_API_TOKEN` (at least
32 characters). Keep it outside version control. For example, in a POSIX shell:

```sh
export EDGEFORGE_API_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
edgeforge serve --registry registry.json
```

In PowerShell:

```powershell
$env:EDGEFORGE_API_TOKEN = python -c 'import secrets; print(secrets.token_urlsafe(32))'
edgeforge serve --registry registry.json
```

The service defaults to loopback port 8741. It verifies registered bundles at
startup, records their hashes, and rejects changed bytes at execution. Registry
paths are relative to the registry file; they are privileged startup configuration
and never accepted from remote requests.

| Endpoint | Behavior |
| --- | --- |
| `GET /healthz` | Public liveness response without environment details |
| `GET /v1/bundles` | Authenticated ID and digest inventory |
| `GET /v1/capabilities` | Authenticated runtime and device-class report |
| `GET /v1/openapi.json` | Authenticated OpenAPI contract |
| `POST /v1/benchmarks` | Synchronous benchmark of a registered ID |

```sh
curl http://127.0.0.1:8741/v1/benchmarks \
  -H "Authorization: Bearer $EDGEFORGE_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"bundle_id":"example","options":{"warmup":5,"iterations":50}}'
```

Responses use the same report schema as the CLI. HTTP 200 means measurement
completed; inspect `agreement.passed` for numerical acceptance. Errors use
`{"error":"category"}` without raw native exceptions or filesystem paths:
401 unauthenticated, 404 unknown bundle, 409 changed registration, 413 oversized
body, 422 invalid input or failed execution, 503 device busy (`Retry-After: 1`).

Bodies are capped at 8 KiB before JSON parsing, including chunked transfers.
At most 64 bundles may be registered. HTTP requests permit up to 1000 iterations
and 20 warmups; the common benchmark layer caps total invocations at 100,000.
Only one request can benchmark at a time. Concurrent callers receive backpressure.

## Production integration boundary

This is a trusted single-worker transport, not a multi-tenant SaaS deployment.
Use exactly one service worker per device. Scaling to additional isolated devices
is external orchestration; do not increase HTTP worker count on a shared device.
The API does not upload models, fetch URLs, provide tenant storage, enqueue jobs,
or impose a hard timeout inside native inference. A disconnected client does not
terminate native work. Isolate untrusted model execution in supervised processes
with resource and execution limits before exposing it to third parties.

An application can put TLS, identity, rate limiting, and an asynchronous queue in
front of this contract. Use bundle SHA-256 as an immutable artifact key, persist
the full report and runtime versions, and use the upstream job ID for retries.
Repeated requests intentionally produce independent measurements; no idempotency
or completed-result caching is implied. CORS is disabled by default.

See [architecture](architecture/overview.md), [security](security.md), and the
checked-in [OpenAPI contract](../schemas/openapi.json).
