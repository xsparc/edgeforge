# EdgeForge

This directory is an independent Git repository. Preserve sibling projects.

Use OpenSteward research, delivery, and evidence skills for stewardship. Deliver
bounded, tested changes. The initial MVP is authorized as three stacked pull
requests; merging, deployment, releases, paid services, and contacting people
require separate permission.

Read sources in this order: `docs/architecture/overview.md`,
`docs/roadmap/implementation-roadmap.md`, accepted decisions under
`docs/architecture/decisions/`, code and tests, then supporting documentation.
The governance registry is a derived index, not authority.

Keep public files free of local paths, machine identifiers, credentials, and
private operator configuration. Never load pickle models or arbitrary Python
from a request. Runtime inputs are trusted local artifacts, not a sandbox.

Use Python 3.11 or newer. Run `python -m pytest`, `ruff check .`, and
`python scripts/check_governance.py --as-of YYYY-MM-DD --strict` before closeout.
Record real runtime checks separately from mocked adapter contracts. Keep
benchmark scope and platform limitations explicit.
