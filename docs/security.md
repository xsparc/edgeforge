# Trust and resource boundaries

Models and test vectors must come from a trusted source. Hashes detect changed
bytes; they do not authenticate publishers or make native model parsers safe.
EdgeForge never loads pickle checkpoints, executes user-supplied Python, installs
custom operators, downloads models, or extracts bundle entries to disk.

The format bounds models to 512 MiB, vectors to 64 MiB, 32 inputs and outputs,
1024 cases, and 16 million elements per tensor. These are input admission limits,
not native execution memory or time isolation. A native model can still exhaust
resources or crash its process. Production multi-tenant deployments require
separate sandboxed worker processes, memory/CPU limits, timeouts, authenticated
artifact storage, and an external identity gateway.

The optional HTTP service is intended for trusted operators. Bind to loopback
by default. It accepts opaque IDs from a startup registry, and a bearer token is
mandatory. Put TLS and an identity gateway in front before remote exposure.
Do not send untrusted models to this service. No tenant isolation is claimed.

Reports omit hostnames, usernames, local paths, environment dumps, and device
serial numbers. Device capabilities describe the runtime environment, not a
hardware attestation. Runtime errors use fixed categories at public boundaries.

For vulnerabilities, use GitHub private vulnerability reporting if available;
avoid posting credentials, private models, or sensitive traces in public issues.
