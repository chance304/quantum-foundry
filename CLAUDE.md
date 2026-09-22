# Quantum Foundry

A multi-physics semiconductor device simulator (ab-initio → device transport → thermal/mechanical → manufacturability/yield) for post-silicon and 3D-stacked devices. Judged on one thing above all: accuracy against real experimental/fab data, honestly reported.

## How to operate in this repo

1. Read `docs/ROADMAP.md` first — what's built, what's next, what's blocked.
2. Read `docs/ARCHITECTURE.md` for the data-flow/contract summary before touching pipeline code.
3. Read `docs/DECISIONS.md` for why the code looks the way it does before changing module boundaries.
4. Follow `CONTRIBUTING.md`: DCO sign-off on every commit (`git commit -s`), a `docs/DECISIONS.md` entry for architecture calls, a `CHANGELOG.md` line, and update `docs/ROADMAP.md` when an item closes.

## The one rule that matters most

**Never present a generated-looking number as if a real solver produced it.** Every `Result` dataclass in this codebase carries a `ProvenanceInfo` with an `is_stub` flag — the validation report must always show whether a number came from a stub or a real backend. Every non-computed materials constant (especially contact resistance) must carry a `Citation` to a named paper or database. Honest, provable accuracy beats an impressive-looking demo.

## Architecture at a glance

Five layers, wired by `orchestration/pipeline.py`, each behind a `Protocol` + `get_backend(name)` factory so a stub backend and a real backend are interchangeable via config alone:

1. **`materials/`** — materials database (`MaterialRecord`, per-field `Citation`), sourced from JARVIS-DFT, C2DB, Materials Project.
2. **`dft/`** — ab-initio layer. Stub: physically-grounded effective-mass stand-in. Real: Quantum ESPRESSO + Wannier90.
3. **`transport/`** — device transport. Real-but-lightweight from day one: DEVSIM (drift-diffusion) + Kwant (NEGF).
4. **`thermal/`** — thermal/mechanical. Real-but-lightweight from day one: HotSpot compact model. Deferred: FEniCSx (3D FEA) + Elmer (thermo-mechanical coupling).
5. **`manufacturability/`** — yield. Closed-form Poisson/Murphy + Monte Carlo defect placement.

Sitting alongside the pipeline: **`validation/`** — the actual differentiator. Matches `PipelineResult` output against cited real experimental benchmarks, computes %-error, renders a Markdown report. This is the artifact that makes accuracy claims checkable.

See `docs/ARCHITECTURE.md` for full data contracts and `docs/ROADMAP.md` for milestone status.

## Environment

Heavy scientific tools (Quantum ESPRESSO, Wannier90, DEVSIM, Kwant, FEniCSx) install via `environment.yml` (conda/mamba). Elmer has no reliable conda-forge package — it runs via `docker/elmer.Dockerfile`. Run `scripts/preflight.sh` before any `--backend real` run; it refuses to proceed if a required tool is missing rather than silently falling back.

## Testing

`tests/` mirrors `src/quantum_foundry/`, split by *what's being tested* (materials, dft, transport, thermal, manufacturability, validation, orchestration), plus `tests/scripts/` (`.bats`, shell scripts) and `tests/e2e/`. Tests requiring a real heavy solver are marked `requires_real_solver` and excluded from CI (`pytest -m "not requires_real_solver"`).
