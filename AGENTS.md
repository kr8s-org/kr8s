# AGENTS.md

Guidance for AI agents (and humans) working in the `kr8s` repository.

`kr8s` is a simple, extensible Python client library for Kubernetes that feels
familiar to people who already know `kubectl`. It ships a synchronous API by
default and an async API (`asyncio`/`trio`) under `kr8s.asyncio`.

## Repository layout

- `kr8s/` — the library source.
  - `_objects.py` — the heart of the project. Defines `APIObject` (async) and
    every Kubernetes resource class (`Pod`, `Deployment`, `Service`, …). All
    real logic lives here as async methods named with an `async_` prefix
    (e.g. `async_get`, `async_create`, `async_delete`).
  - `_api.py` — the async `Api` client (auth, request dispatch, caching).
  - `_auth.py`, `_config.py` — kubeconfig loading, auth, and cluster config.
  - `_async_utils.py` — the machinery that lets the sync API wrap async code by
    running a background thread with its own event loop (`Portal`,
    `as_sync_func`, `as_sync_generator`). Rarely needs changing.
  - `objects.py`, `_api.py`-derived sync surfaces — the **sync** public API.
    `APIObjectSyncMixin` (in `_objects.py`) and `kr8s/objects.py` wrap the
    `async_*` methods with `as_sync_func` / `as_sync_generator`.
  - `asyncio/` — the **async** public API. Thin re-exports of the underlying
    async classes/functions from `kr8s._*` modules.
  - `_exec.py`, `_portforward.py`, `_data_utils.py`, `_exceptions.py` — helpers.
  - `_vendored/` — third-party code (e.g. `asyncache`). **Do not lint, format,
    or edit** — it is excluded from all tooling.
  - `tests/` — pytest suite (`test_*.py`), plus `resources/` and `scripts/`.
  - `conftest.py` (both root and `kr8s/`) — shared fixtures.
- `docs/` — Sphinx documentation (MyST markdown). `contributing.md` and
  `releasing.md` are the canonical process docs.
- `examples/kubectl-ng/` — a separate `kubectl-ng` package (a `kubectl` clone
  built on kr8s) with its **own** `pyproject.toml` and test suite.
- `ci/` — automation scripts (e.g. `update-kubernetes.py`).
- `.github/workflows/` — CI (`test-kr8s.yaml`, `test-kubectl-ng.yaml`, release).

## The sync/async architecture (read this before editing resource code)

kr8s is built async-first. **All real implementation is async and lives once.**

1. Write logic as an `async def async_<name>(...)` method on the async class in
   `kr8s/_objects.py` (or `_api.py`).
2. Expose it on the async API via `kr8s/asyncio/` re-exports (no wrapping — the
   async method is the public async method minus the `async_` prefix where the
   public name is defined, or exposed directly).
3. Expose it on the sync API by adding a wrapper in the `*SyncMixin` /
   `kr8s/objects.py` that calls `as_sync_func(self.async_<name>)(...)` (or
   `as_sync_generator` for generators).

When you add or change a method, update **both** the async source and its sync
wrapper, and keep signatures in sync. Sync wrappers carry
`# type: ignore[override]` because they intentionally override async signatures
with sync ones — this is expected. Docstrings live on the async version; sync
wrappers inherit them (`kr8s/objects.py` sets `# ruff: noqa: D102`).

## Development environment

Use [`uv`](https://github.com/astral-sh/uv) (the project's chosen tool) but
anything that installs the package in editable mode works.

```bash
pip install uv
uv sync --dev
```

Common tasks are defined via [`taskipy`](https://github.com/taskipy/taskipy) in
`pyproject.toml`:

- `uv run task test` — run the test suite.
- `uv run task test-ci` — tests with retries (what CI runs).
- `uv run task docs` — build docs once.
- `uv run task docs-serve` — live-reloading docs server.

## Testing

Tests run with `pytest` and use [`kind`](https://kind.sigs.k8s.io/) via
[`pytest-kind`](https://pypi.org/project/pytest-kind/) to spin up a real
Kubernetes cluster in Docker. **Docker must be available.** Cluster lifecycle is
handled by fixtures, so no manual cluster setup is needed.

```bash
uv run task test
# or a single file / test
uv run pytest kr8s/tests/test_objects.py
uv run pytest kr8s/tests/test_objects.py::test_pod_create
```

Key testing facts:

- Tests are **integration-heavy** and hit a live kind cluster; they are slower
  than pure unit tests. A per-test timeout of 300s is configured.
- `pytest-asyncio` runs in `asyncio_mode = "auto"`, so `async def test_*`
  functions work without decorators.
- Each test gets a fresh namespace via the autouse `ns` fixture
  (`kr8s/conftest.py`); use it to avoid cross-test collisions.
- Useful fixtures: `example_pod_spec`, `example_deployment_spec`,
  `example_service_spec`, `example_crd_spec`, `serviceaccount`, `k8s_cluster`.
- Set `KUBERNETES_VERSION` to test against a specific k8s version. CI runs a
  matrix of Python 3.9–3.14 and multiple Kubernetes versions.
- Test/`conftest.py`/`examples`/`docs`/`ci` code is exempt from docstring (`D`),
  naming (`N`), and bugbear (`B`) lint rules.

## Linting, formatting, and types

Managed by [`pre-commit`](https://pre-commit.com/). Install and run it:

```bash
pip install pre-commit
pre-commit install            # run automatically on each commit
pre-commit run --all-files    # run manually against everything
```

The hooks (see `.pre-commit-config.yaml`) are:

- **black** — formatting.
- **ruff** — linting with autofix (`select = ["D","E","W","F","I","N","B"]`,
  Google docstring convention, line length 120). Public functions/classes need
  Google-style docstrings.
- **insert-license** — every `.py` file must carry the SPDX header from
  `LICENSE_HEADER` (auto-inserted). Keep it at the top of new files.
- **mypy** — type checking (excludes `examples`, `ci`, `docs`, `_vendored`).
  The library is typed and ships `py.typed`; keep annotations correct.
- **pyupgrade** — enforces modern syntax (`--py39-plus`); the project targets
  Python **3.9+**, so don't use syntax newer than 3.9 in library code.

`_vendored/` is excluded from every hook — never reformat it.

## Conventions

- **Python 3.9+ compatibility** in `kr8s/` library code. Use
  `from __future__ import annotations` for modern typing syntax.
- Keep code **human-readable** — a project goal is no swagger/generated code.
- Public API changes should be reflected in `docs/` (MyST markdown). Where docs
  show code, provide **both** sync and async examples using the `tab-set`
  directive (see `docs/asyncio.md`).
- New resource kinds go in `kr8s/_objects.py` and must be exported from both
  `kr8s/objects.py` (sync) and `kr8s/asyncio/objects.py` (async) `__all__`.

## Versioning & releasing

- Versioning follows [EffVer](https://jacobtomlinson.dev/effver); tags are
  prefixed `v` (e.g. `v0.20.15`). Version is derived from git tags via
  `hatch-vcs` — do not hand-edit `kr8s/_version.py`.
- Releasing (maintainers): create a `v0.0.0` tag and push it to the
  `kr8s-org/kr8s` upstream; the release GitHub Action builds and publishes to
  PyPI. See `docs/releasing.md`.

## Working with kubectl-ng

`examples/kubectl-ng/` is an independent package with its own `pyproject.toml`,
`uv.lock`, and tests, and it pins a specific released `kr8s` version. Develop it
from inside that directory (`uv sync --dev` there). It is covered by the
separate `test-kubectl-ng.yaml` workflow, not the main test workflow.

## Quick checklist before finishing a change

1. Implemented logic once as an `async_*` method (async-first).
2. Added/updated the matching **sync wrapper** with `as_sync_func` /
   `as_sync_generator`, and exported new kinds from both `objects.py` modules.
3. Added/updated tests in `kr8s/tests/` (they will spin up kind).
4. `uv run task test` (or the relevant subset) passes.
5. `pre-commit run --all-files` is clean (black, ruff, mypy, license header).
6. Updated `docs/` with sync + async examples where user-facing behavior changed.
