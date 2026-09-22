# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
Entries below `0.2.0` are reconstructed retroactively (2026-07-21, standards
audit) from real git history — this project never bumped its version
per-milestone before that point; going forward, each milestone lands with
its own entry and version bump.

## [Unreleased]

## [0.3.0] — 2026-09-23 — first public release

### Added
- Released under **Apache-2.0**: `LICENSE`, `NOTICE` (CC BY 4.0 attribution
  for JARVIS-DFT, C2DB and Materials Project seed data) and
  `THIRD_PARTY_LICENSES.md`.
- Open-source contributor scaffolding: DCO sign-off requirement and CI check,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue/PR templates, `CITATION.cff`,
  Dependabot config, `examples/`, and `docs/ROADMAP.md`.

### Changed
- `thermal/mesh_generation.py` now drives gmsh out-of-process through a
  generated `.geo` script instead of importing its (GPL) Python API; the
  written mesh is validated with meshio.
- CI: the self-hosted `real-solvers` job is manual-trigger only, so it never
  runs on pull requests.
- `setuptools` build floor raised to 83.
- README, CONTRIBUTING and CLAUDE.md rewritten for public contributors.

### Removed
- Internal `TASKLOG.md` / `SESSION_LOG.md` (superseded by `docs/ROADMAP.md`,
  `docs/DECISIONS.md` and this changelog).

### Added (pre-release work, previously unreleased)
- `CONTRIBUTING.md`: the stub/real backend pattern (`Protocol` +
  `stub.py` + real backend(s) + `get_backend()` registry) written up for a
  new contributor, dev workflow, testing conventions, and a flagged-open
  license/ownership question.
- Real docstrings for all 4 `interfaces.py` Protocol files (`dft`,
  `transport`, `thermal`, `manufacturability`) — `is_stub` semantics and
  `run()`'s inputs/outputs/units, previously undocumented at the function
  level despite rich module-level docs elsewhere.
- `README.md`: a real, verified Setup section (stub-only plain-venv path
  and real-backend conda path) — previously had no setup instructions at
  all.
- `.pre-commit-config.yaml` — mirrors `ci.yml`'s `lightweight` job exactly
  (`ruff check` + `mypy`), pinned to the exact `ruff`/`mypy` versions
  installed and verified passing this session (`v0.16.1`/`v1.20.2`, both
  already the floor pins in `pyproject.toml`'s `dev` extra). Deliberately
  no `ruff format` hook — this project has never adopted or run a
  formatter (see `pyproject.toml`'s own `[tool.ruff]` comment), so adding
  one now would introduce a new, unreviewed repo-wide reformat rather than
  enforce an existing standard.
- `src/quantum_foundry/py.typed` (PEP 561 marker), declared in
  `pyproject.toml`'s new `[tool.setuptools.package-data]` table and
  confirmed present in a real built wheel (`python -m build --wheel`,
  inspected the resulting zip) — this package's type hints are already
  consistent enough to pass `mypy` clean repo-wide; the marker is what lets
  a type checker running against a future caller see that, rather than
  silently treating `quantum_foundry` as untyped. No confirmed external
  consumer of this repo as a library was found this pass — a low-risk
  hygiene addition, not a claim one exists.

### Fixed
- Engineering-standards audit pass (2026-08-04, parallel to sibling audits
  covering materials-data provenance/security/physics-fidelity/docs — this
  one scoped to software-engineering hygiene only). `ruff check src/ tests/`
  had 34 real, current errors (confirmed by directly running it, not a
  stale CI log) — now 0. 29 were auto-fixable (`I001` import sorting x12,
  `RUF022` unsorted `__all__` x8, `UP017`/`UP035` deprecated-import-style
  x8, `RUF100` unused-noqa x1); the remaining 5 were read and fixed by
  hand, not blind-applied: `RUF007` (`zip()` → `itertools.pairwise()` in
  `transport/extraction.py`), `ISC004` (parenthesized an implicitly-
  concatenated f-string pair in `ngmm_compat/chiplet_export.py`), `C408`
  (`dict(...)` → `{...}` literal in `transport/kwant_backend.py`) — all
  three semantically identical, verified via `ruff --unsafe-fixes --diff`
  before applying; `BLE001` (`tests/materials/test_schema.py`'s frozen-
  dataclass immutability test caught bare `Exception` — narrowed to the
  real, specific `dataclasses.FrozenInstanceError` actually raised);
  `PLW1510` (`thermal/hotspot_backend.py`'s `subprocess.run()` had no
  explicit `check=` — added `check=False` with a comment, since the
  surrounding code already inspects `proc.returncode` and raises its own
  `RuntimeError` with captured stdout/stderr, so implicit `check=True`
  would have been the wrong fix here, not just a silenced warning).
  `mypy src/quantum_foundry` was already clean (0 errors) — verified, not
  assumed, against a fresh `uv`-managed Python 3.14 environment (this
  repo's own `requires-python = ">=3.11"` floor isn't satisfiable with the
  sandbox's default Python 3.10; 3.14 was the cached interpreter prior
  sessions in this project also used). Full test suite
  (`pytest -m "not requires_real_solver"`) still green after every fix:
  185 passed, 13 deselected.
- `README.md`'s Status section claimed "Lightweight CI (GitHub-hosted) is
  green" — was false at the time this was written (`ruff check` failed on
  `main` with 34 findings, verified via `gh run view` against the 3 most
  recent CI runs); now genuinely true again per the engineering-standards
  fix immediately above, which zeroed those 34 findings out.
- `gmsh`'s plain PyPI wheel needs `libGLU.so.1`, missing (and unfixable
  without root) in every sandbox tried so far -- switched to gmsh's own
  official headless "nox" build instead, installed explicitly (a separate
  index + `--pre`, since every version on that index is a prerelease) in
  `scripts/setup_env.sh` and `.github/workflows/ci.yml`'s `real-solvers`
  job. `pyproject.toml`'s `mesh-generation` extra no longer lists `gmsh`
  (can't express "different index + prerelease" in a plain dependency
  string) -- only `meshio`/`h5py` now. Removed
  `tests/e2e/test_real_pipeline.py::test_gmsh_import_fails_in_this_sandbox_missing_libglu`,
  whose pass/fail depended on which gmsh variant happened to be installed
  rather than on this repo's code; the new `tests/thermal/test_mesh_generation.py`
  is the real, current verification.
- `transport/mobility_degradation.py`'s `scattering_coefficient_cm2` parameter
  was dimensionally mislabeled: `mu_defect = C / defect_density_per_cm2`
  actually requires `C` in `(V*s)^-1`, not `cm^2`, since
  `cm^2/(V*s) / cm^-2` doesn't cancel that way. Renamed to
  `scattering_coefficient_per_Vs` in `mobility_degradation.py`,
  `transport/stub.py` (variable and the `params` dict key), and both
  affected test files -- caught while researching a real citable value for
  this parameter, not a cosmetic rename.
- WS2/WSe2 anomalous electron effective masses corrected: both were
  confirmed anomalous (`ws2_monolayer.yaml`'s JVASP-658 was 612.59 m0,
  `wse2_monolayer.yaml`'s JVASP-652 was 105.23 m0, both previously left
  in place or null) by two independent, directly-read sources (Kormanyos
  et al. 2015, Shi et al. 2013, both ~0.22-0.29 m0). Corrected to 0.26/
  0.28 m0 respectively; original JARVIS-DFT values preserved in
  `extra.superseded_values` for traceability. WSe2 now runs in both
  transport carrier roles for the first time.
- `mos2_subthreshold_swing` benchmark's uncited 60.0 mV/dec value (likely
  the Boltzmann theoretical limit misattributed as a measurement)
  corrected to 63.0 mV/dec, citing a real, directly-read near-ideal
  measurement (Vu et al. 2018).
- `transport/verilog_a_export.py`'s exported Verilog-A compact model had
  no V(d,s) dependence at all -- `I(d,s)` was a function of `V(g,s)` only,
  so the model output a fixed nonzero current even at Vds=0 (unphysical,
  and a real SPICE DC-convergence risk). Fixed by scaling the looked-up
  current by `tanh(V(d,s)/VDS_SAFETY_V)`, a numerical-safety smoothing
  factor, not a new fitted device parameter -- negligible effect at every
  real bias point this project's backends use. Found via a 2026-07-27
  standards-audit re-pass (`docs/STANDARDS_AUDIT.md`).

### Added
- `thermal/mesh_generation.py` -- M5's first real code. Builds
  `docs/M5_PLAN.md`'s "minimal first 3D case" (truncated Si substrate under
  a SiO2 layer, channel material modeled as a surface, not a 3D solid) via
  gmsh's OCC kernel, with named physical groups for both volumes and all
  three boundary regions, and converts to XDMF+HDF5 via `meshio` for
  future FEniCSx ingestion. Verified end-to-end: real tagged mesh
  generated, physical-group names confirmed to survive the `meshio`/XDMF
  round trip, `default_slab_geometry_from_device()` bridges from the
  existing `DeviceGeometry` schema. See `tests/thermal/test_mesh_generation.py`.
- MoTe2/WTe2 monolayers seeded with real data for the first time (both
  were honest all-null placeholders, confirmed absent from JARVIS-DFT):
  found the real p-6m2 (1H, semiconducting) phase on C2DB's current live
  site, band gap/effective masses read directly, lattice constant/work
  function derived from other directly-reported C2DB numbers. Both now
  qualify for heterostructure search in both carrier roles.
  `materials/sources/c2db.py`'s stale download URL and guessed uid-naming
  convention corrected in its docstring.
- 3 validation benchmarks (`mos2_mobility_bare_sio2`, `mos2_mobility_optimized`,
  `mos2_subthreshold_swing`) upgraded from "TODO -- search-summary sentence"
  to real, directly-read citations (Liu et al. 2015; Radisavljevic et al.
  2011; Vu et al. 2018).
- The remaining 3 benchmarks (`mos2_rc_ni_uhv`, `mos2_rc_edge_contact_record`,
  `mos2_ion_edge_contact_120nm`) upgraded from `verified: false`/TODO
  figure refs to real, directly-read papers: Sun, Kim et al., *ACS Nano*
  2024 (Figure 1g, 500 ohm*um UHV-Ni contact resistance, exact match) and
  Xiao, Xiong et al., *Research* 2025 (Figure 4E/F: Rc = 1.25 +/- 0.46
  kOhm*um, uncertainty band now populated where it was null before;
  Figure 4B/4C: 436 uA/um on-current at Vds=1V/Lch=120nm, exact match).
  The edge-contact paper's seed year (2026) was wrong -- corrected to
  2025, its real publication date. All 6 seeded benchmarks now carry
  `verified: true` with a real figure/table anchor.
- `thermal/beol_budget.py`'s BEOL/M3D thermal-budget citations upgraded
  from "widely-cited, not clause-cited" to real, directly-verified
  sources: M3D's 300C limit now cites Xie et al., *Nat. Commun.* 14, 5952
  (2023) -- a MoS2-specific monolithic-3D precedent, matching this
  project's own anchor material. BEOL's 400C limit now names CEA-Leti/
  Batude's CoolCube(TM) research body as the real reference class.
- `manufacturability/monte_carlo.py`'s `dies_per_wafer()` docstring now
  names the real, standard gross-dies-per-wafer (GDW) formula it
  implements, confirmed via independent re-derivation.
- M9: real multi-tier/multi-gate device physics for CFET/GAA/M3D (hard
  requirement, 2026-07-27). `orchestration/pipeline.py`'s `Pipeline.run()`
  now runs dft+transport once per `DeviceGeometry.stacked_tiers` entry
  (M9a). `thermal/hotspot_backend.py` gained `run_stacked()`/
  `default_stacked_stack_from_geometry()`: each stacked tier gets its own
  real power (fixing a bug found while building this — one tier's power
  was previously silently applied to every "channel"-role layer) plus a
  synthetic Kapitza inter-tier interface layer, reusing `docs/M5_PLAN.md`'s
  already-designed technique (M9b). `kwant_backend.py` now reports
  `geometry.gate_type` honestly in `extra` rather than inventing an uncited
  "GAA is stronger" physics multiplier (M9c). See `docs/M9_PLAN.md`/
  `docs/ROADMAP.md` for full detail; M9d (DEVSIM)/M9e (FEniCSx) remain blocked
  on the self-hosted runner, same as M5.

### Known limitations
- M5 kicked off; ab-initio (QE+Wannier90) has no achievable path in this
  sandbox (no pip path, needs conda). Mesh generation's first real step
  (`gmsh`/`meshio`) installs cleanly but fails to import — `libGLU.so.1` is
  genuinely absent here with no working sudo to install it. New test:
  `tests/e2e/test_real_pipeline.py::test_gmsh_import_fails_in_this_sandbox_missing_libglu`.
  No mesh-generation code written yet — see `docs/M5_PLAN.md`/`docs/DECISIONS.md`.

### Fixed
- `thermal/stub.py`'s Tj scale-mismatch at nm-scale device areas (found
  while building M6) — effective heat-spreading area now floored at a
  synthetic die-footprint size, mirroring `hotspot_backend.py`'s existing
  `_pad_to_die_footprint()` fix, flagged via
  `extra["synthetic_die_area_padding_applied"]`.
- `hotspot_backend.py`'s specific-heat-capacity fallback flag was a
  hardcoded `True` (schema had no such field at all); now a real per-layer
  computed list via the new `MaterialRecord.specific_heat_capacity_J_per_m3K`
  field.

### Added
- `MaterialRecord.specific_heat_capacity_J_per_m3K` (schema-only — no seeded
  material has a real value yet).
- WSe2's `effective_mass_hole` (0.43 m0, sourced from JARVIS-DFT JVASP-652,
  a distinct DFT run from this material's other cited fields — see
  `docs/DECISIONS.md`). `effective_mass_electron` deliberately left null
  (JVASP-652's own value, 105.23 m0, looks anomalous — same class of issue
  as WS2's already-flagged 612.59 m0).

### Fixed
- `jarvis_dft.py`'s `JVASP_IDS` no longer lists WSe2 under an ID
  (JVASP-653) confirmed absent from the fetchable `dft_2d` dataset —
  `refresh()` would have raised `LookupError` on it and aborted before
  reaching graphene/hBN/WS2 in the same loop.

### Added
- `dft/stub.py`'s required-fields gate is now carrier-role-aware
  (`params["carrier_type"]`) — a material only needs the effective mass
  for the role actually being requested; omitting `carrier_type` entirely
  keeps the previous conservative behavior (both required), matching every
  pre-existing caller. `DFTResult.effective_mass_electron`/
  `effective_mass_hole` are now `float | None`.
  `orchestration/heterostructure.py` now threads `carrier_type` into the
  DFT stage too (previously only transport) — this is what actually lets
  WSe2 run in the p-role. `qf heterostructure-search` now shows WSe2 on
  the p-type pareto front (3 members: MoS2/WSe2/WS2, still no single
  recommendation — a real trade-off).
- `jarvis_dft.py` can now auto-fetch `black_phosphorus_monolayer` (real
  anisotropic lattice/effective-mass/dielectric data via
  `extra["lattice_parameters"]`/`extra["effective_mass_tensor"]`/
  `extra["dielectric_tensor"]`, matching its existing hand-seeded values).
  `_yaml_merge.py`'s `merge_field()` gained an optional `extra_fields` param
  to support this.

### Fixed
- `dft/stub.py`'s `_make_loader()` always used `effective_mass_electron`
  for the analytic tight-binding Hamiltonian regardless of requested
  carrier — dormant today (M6 only exercises the stub transport backend)
  but wrong for any real hole-carrier Kwant NEGF run.

### Known limitations
- Materials Project's real data (HfO2/ZrO2 lattice parameters) needs an
  `MP_API_KEY` this environment doesn't have — legacy site is down (503),
  new-gen site requires auth (403). Not literature-blocked, credential-blocked.
- `conda-lock.yml` generation needs a real conda environment this sandbox
  doesn't have (`which conda` → not found) — deferred to the self-hosted
  runner, per `docs/ROADMAP.md`.

### Added
- Real V_th extraction (constant-current method) + DIBL (`transport/extraction.py`);
  `kwant_backend.py` now sweeps V_gs at two V_ds points. `TransportResult`
  gained `threshold_voltage_V`/`dibl_mV_V`.
- BEOL <400°C / M3D <300°C hard-stop thermal gates (`thermal/beol_budget.py`);
  `PipelineResult` gained an `extra` dict populated with both checks every run.
- An I_on/I_off > 1e5 functional-transistor gate (`manufacturability/functional_criteria.py`).
- `DeviceGeometry` stacking schema (`DeviceTier`, `gate_type`, `stacked_tiers`)
  — makes CFET/GAA/M3D geometries representable; no solver consumes it yet.
- A real spatial Monte Carlo wafer-yield engine (`manufacturability/monte_carlo.py`,
  backend `"monte_carlo"`) — first backend to populate `YieldResult.confidence_interval`.
  Verified converging to the closed-form Poisson result as N grows.
- Defect-density → mobility coupling via Matthiessen's rule (`transport/mobility_degradation.py`),
  opt-in via `transport/stub.py`'s `defect_density_per_cm2`/`defect_scattering_coefficient_cm2` params.
- A real PPA-Y Pareto-matrix Markdown report (`orchestration/report.py`,
  `qf heterostructure-search --format markdown`).
- Synthetic TLM / van der Pauw PCM structures (`validation/pcm_structures.py`)
  — solves the real van der Pauw transcendental equation via `scipy.optimize.brentq`,
  not the simplified symmetric-sample approximation.

### Fixed
- `monte_carlo.py`'s first implementation materialized an `(n_runs, n_dies)`
  array, which exhausted memory against a small critical area (~34 trillion
  "dies"); fixed by sampling the defect-free-die count directly from
  `Binomial(n_dies, exp(-D0*A))`.
- `pyproject.toml`'s `[tool.mypy]` `python_version` bumped 3.11 → 3.12 —
  numpy 2.5.1's own stubs use PEP 695 syntax mypy 1.20.2 can't parse below
  that. Added `scipy.*` to the deliberate no-type-stubs override list.

### Added
- `qf run` now prints its BEOL/M3D thermal-budget check results every run
  (previously computed and stored in `PipelineResult.extra` but never shown).
- New `qf calibrate <material>` command — a synthetic TLM/van der Pauw
  self-consistency check against the pipeline's real `contact_resistance_ohm_um`,
  using `validation/pcm_structures.py`.
- M7: real behavioral (piecewise-linear lookup-table) Verilog-A export
  (`transport/verilog_a_export.py`, `qf export-verilog-a`) — portable IEEE
  1364.1 syntax, not a BSIM-CMG parameter fit (that needs real multi-bias
  DD/NEGF data this sandbox can't produce yet). Landing this genuinely
  unblocks M8 (`ngmm_compat/chiplet_export.py`), not attempted this round.

### Known limitations
- The generated Verilog-A is confirmed syntactically well-formed but NOT
  compiled/run through a real SPICE/Verilog-A simulator — none is
  available in this sandbox.

### Added
- M8: real NGMM chiplet-collateral export (`ngmm_compat/chiplet_export.py`'s
  `export_chiplet_collateral()`/`write_bundle()`, `qf export-chiplet`) —
  unblocked by M7. Writes a real `manifest.yaml`/`compact_model.{va,stub}`/
  `SUMMARY.md` bundle from an actual `PipelineResult`; degrades to an
  honestly-labeled placeholder (never crashes) if the transport result's
  `iv_curve` is too sparse for a real Verilog-A export.

### Known limitations
- `export_chiplet_collateral()`'s `benchmark_registry` param is accepted
  but only counted, not quantity-matched against the pipeline run — real
  matching needs a `SimulatedValue` built from `PipelineResult`, a
  separate cross-schema mapping question not solved here.

### Added
- Closed all 4 Tier 2 (scoping-decision) items from
  `docs/STANDARDS_AUDIT.md`: `transport/devsim_backend.py` gained a real,
  unit-tested `caughey_thomas_mobility()` function (the mobility-model
  decision for its eventual drift-diffusion implementation — the equation
  setup itself stays `NotImplementedError`, unverifiable in this sandbox);
  `docs/M5_PLAN.md` gained a "Mesh convergence study" section (real ASME
  V&V 10 verification step, distinct from the existing FEniCSx-vs-Elmer
  cross-solver check); `manufacturability/poisson_murphy.py` gained a
  negative-binomial (Stapper 1984) yield model
  (`NegativeBinomialYieldBackend`, requires a caller-supplied
  `clustering_parameter_alpha`, same discipline as `defect_density_per_cm2`);
  `validation/schema.py`'s `SimulatedValue` gained an `uncertainty` field
  for parity with `ExperimentalValue` (still `None` everywhere — no real
  verification/convergence check exists yet, deliberately not invented).

## [0.2.0] - 2026-07-21

### Added
- Repo-wide standards audit (`docs/STANDARDS_AUDIT.md`) against real DFT-
  provenance, TCAD/NEGF/FEA, yield-modeling, and software-engineering
  standards, with a prioritized 3-tier gap-filling backlog.
- M6: n/p channel-material search (`orchestration/heterostructure.py`,
  `qf heterostructure-search` CLI) targeting the 2D-CMOS n/p-asymmetry gap.
- `carrier_type` param (electron/hole) on `transport/stub.py`, required for
  M6 to model p-type transport at all.
- ruff + mypy wired into CI's lightweight job; `--cov-fail-under=70` gate.
- Upper-bound version pins on all `pyproject.toml` dependencies (interim
  reproducibility measure ahead of a real `conda-lock.yml`).

### Fixed (Tier 1 standards-audit backlog)
- `thermal/hotspot_backend.py`'s realistic-scale (100nm-device) performance
  bug via `_pad_to_die_footprint()` — a real device is now embedded in a
  synthetic die footprint instead of being treated as the entire chip.
- Dangling `docs/ROADMAP.md` cross-reference in `poisson_murphy.py`'s D0 error
  message (the referenced item didn't exist — now does).
- Inconsistent "refuse loudly vs. silently default" behavior:
  `manufacturability/stub.py` now flags its uncited D0 default in `extra`,
  matching `thermal/stub.py`'s existing fallback-flagging pattern.
- Unflagged physics simplifications now explicitly documented:
  `kwant_backend.py`'s idealized same-material contact model, and
  `hotspot_backend.py`'s missing Kapitza (interfacial) thermal resistance
  term, both via `extra` fields and docstring notes.
- Stale `README.md` "Status" section (said "no pipeline code yet" with
  M0–M6a long since built).
- `docs/ARCHITECTURE.md`'s critical-area simplification now named as its
  own distinct gap (critical area analysis), separate from the Monte Carlo
  defect-placement deferral it was previously conflated with.

## [0.1.1] - 2026-07-21 (M3a–d, materials/physics scale-up)

### Added
- Real M3 pipeline: `dft/`, `transport/`, `thermal/`, `manufacturability/`,
  `orchestration/` — stub layer end-to-end plus real backends (Kwant NEGF,
  HotSpot compact thermal, closed-form Poisson/Murphy yield).
- Materials database scaled from 4 to 10 real, cited 2D materials/dielectrics
  (MoS2, WSe2, WS2, HfO2, ZrO2, hBN, graphene, black phosphorus, MoTe2/WTe2
  honest null placeholders).
- Self-hosted GitHub Actions CI runner scaffolding
  (`scripts/setup_github_runner.sh`, `.github/workflows/ci.yml`'s
  `real-solvers` job).
- `docs/M5_PLAN.md`: design-only plan for the M5 3D thermal/mechanical FEA
  milestone.

### Known limitations
- `transport/devsim_backend.py` installs but cannot import in this sandbox
  (missing BLAS/LAPACK symbols; a sandbox limitation, not a code defect).

## [0.1.0] - 2026-07-20

### Added
- Initial scaffolding: `CLAUDE.md`, `docs/DECISIONS.md`,
  `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `pyproject.toml`,
  `pytest.ini`, `environment.yml`.
- M1: real materials layer (`materials/`), seeded from JARVIS-DFT/C2DB/
  Materials Project.
- M2: validation/benchmark layer (`validation/`), 6 seeded benchmark YAMLs.
- M6a: NGMM compatibility layer (`ngmm_compat/`) — materials-library export
  and packaging-compatibility placeholder.
