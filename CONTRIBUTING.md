# Contributing to Quantum Foundry

Thanks for your interest. Bug reports, new cited materials data, validation
benchmarks, new solver backends and documentation fixes are all welcome.

## Ground rules

- **Never present a number a solver didn't produce.** Stub output must stay
  labelled as stub output (`ProvenanceInfo.is_stub`), and every non-computed
  material property needs a `Citation` to a named paper or database. PRs that
  add uncited values or blur stub vs. real results won't be merged.
- **State assumptions and boundary conditions** for every physical model,
  in the module docstring.
- Be kind. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

1. Get a dev environment (see the README's Quickstart). A plain
   `pip install -e ".[dev]"` in a Python 3.11+ venv covers everything except
   the heavy real solvers.
2. Look at [`docs/ROADMAP.md`](docs/ROADMAP.md) and issues labelled
   `good first issue` for what's open.
3. Read `docs/ARCHITECTURE.md`'s "Data flow" and "The stub/real seam"
   sections before touching `orchestration/` or any solver stage.
4. Read `docs/DECISIONS.md` before changing module boundaries. Many apparent
   "obvious refactors" were tried and rejected for a documented reason (e.g.
   why Elmer runs via Docker, why gmsh only runs out-of-process).

For anything larger than a bug fix, open an issue first so the approach can
be agreed before you invest time in it.

## The stub/real backend pattern

Every solver stage (`dft/`, `transport/`, `thermal/`, `manufacturability/`)
is wired the same way. Using `transport/` as the concrete example:

- **`interfaces.py`** — a `typing.Protocol` (`@runtime_checkable`) defining
  the stage's contract: what a backend must expose (`name: str`,
  `is_stub: bool`, a `run(...)` method with a fixed signature) and what
  `Result` type it must return. This is the seam — anything satisfying the
  Protocol is interchangeable, whether it's 20 lines of arithmetic or a
  real NEGF solver.
- **`stub.py`** — a physically-grounded but cheap implementation (e.g.
  `transport/stub.py`'s long-channel MOSFET square-law model). Stubs use
  real `MaterialRecord` fields where they can, but never fabricate a
  number that should come from a real solver — see `dft/stub.py`'s
  `_ALWAYS_REQUIRED_FIELDS` gate for the pattern: raise, don't invent.
- **One or more real backends** — e.g. `transport/kwant_backend.py`
  (atomistic NEGF via Kwant), `transport/devsim_backend.py`
  (semiclassical drift-diffusion via DEVSIM). "Real" doesn't always mean
  "fully implemented" — read the module's own docstring for what's
  actually executed vs. still design-only.
- **`__init__.py`** — the registry. A `_BACKENDS: dict[str, type]` mapping
  and a `get_backend(name: str, **params) -> Backend` factory
  (`BackendNotFoundError` if the name isn't registered). `orchestration/
  pipeline.py` only ever calls `get_backend(name, **params)` — it never
  imports a concrete backend class directly, which is what makes swapping
  stub for real a one-line config change (`RunConfig`/`StageConfig`'s
  `backend` field), not a code change.

**To add a new backend for an existing stage**: implement the stage's
Protocol (matching `run()`'s exact signature and return type), set `name`
and `is_stub` on the class, add it to that stage's `__init__.py`
`_BACKENDS` dict and `__all__`, and register it with `scripts/preflight.sh`
if it has a real-world prerequisite (binary on PATH, importable module) that
should block a `--backend real` run when missing.

**Every `Result` dataclass carries a `ProvenanceInfo`** (`provenance.py`):
`backend_name`, `is_stub`, `tool_version`, `run_id`, `timestamp`,
`git_commit`. This is the actual mechanism behind this project's core rule: a stub-produced number and a real-solver-produced number must
never be presented identically — `is_stub` is always there to check. Every
`validation/` report renders it. If you add a new `Result` field that's a
number a real solver would compute but a stub only approximates, flag it
explicitly in `extra` (see `thermal/stub.py`'s
`fallback_conductivity_used_for` / `manufacturability/stub.py`'s
`defect_density_defaulted_uncited` for the established pattern) — don't let
a stub-approximated field look indistinguishable from a solver-computed one.

## Docstring convention (current gap, worth knowing before you add code)

Module-level docstrings in this codebase are consistently rich — they
explain physical assumptions, honest scope limits, and links to the
relevant `docs/DECISIONS.md` entry. Function/method/class-level docstrings
are, as of this writing, mostly absent (a repo-wide spot check found ~70%
of public functions/methods with no docstring at all) — including, notably,
the `interfaces.py` Protocol files that define the stub/real contract
itself. Those four were given real docstrings in the same pass that added
this file (documenting `name`/`is_stub`/`run()`'s inputs, outputs, and
units) as a starting example — extending that same discipline to the rest
of the public API (units, what "stub" vs "real" means for that specific
function, not just the module) is open work, not solved. If you're touching
a function that lacks one, adding a short docstring while you're there
(inputs/outputs/units, one line on stub-vs-real scope if relevant) is
better than leaving it for a dedicated pass that may never come.

## Testing

`tests/` mirrors `src/quantum_foundry/` by *what's being tested*
(`tests/materials/`, `tests/dft/`, `tests/transport/`, ...), plus
`tests/scripts/` (`.bats`/shell) and `tests/e2e/`. Tests that need a real
heavy solver installed are marked `@pytest.mark.requires_real_solver` and
excluded from the default CI job:

```bash
pytest -m "not requires_real_solver"   # what CI runs on every PR
pytest                                  # full suite; needs real backends installed
ruff check src/ tests/
mypy src/quantum_foundry
```

All three must pass before a PR can merge. The real-solver suite runs on a
maintainer-controlled machine, triggered manually by a maintainer.

## Pull requests

- Branch from `main`, keep each PR to one logical change, and add tests.
- Record implementation-architecture decisions (module boundaries, data
  contracts, environment/CI setup) as a dated entry in `docs/DECISIONS.md`.
- Add a line to `CHANGELOG.md` under "Unreleased".
- Fill in the PR template, including which results (if any) come from a real
  solver vs. a stub.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying that you wrote the change or
otherwise have the right to submit it under the project's Apache-2.0
license, as described at <https://developercertificate.org/>. Add the
sign-off with:

```bash
git commit -s -m "your message"
```

which appends `Signed-off-by: Your Name <you@example.com>` using your git
identity. A CI check blocks PRs with unsigned commits. To fix an unsigned
branch: `git rebase --signoff main` and force-push your branch.

## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0 (see `LICENSE`).
