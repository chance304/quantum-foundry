# M5 Plan: 3D Thermal/Mechanical FEA (Design Only)

*This is a design document, not an implementation — see `docs/ROADMAP.md` for milestone status. Nothing here has been built yet. Written 2026-07-21, planned alongside the M3 real-pipeline/materials-scale-up/self-hosted-CI work.*

M5's real 3D FEA layer (FEniCSx primary solver + Elmer coupled thermo-mechanical) is a genuinely bigger undertaking than the compact/lumped thermal models already built (`thermal/stub.py`, `thermal/hotspot_backend.py`). This document lays out the concrete design so implementation doesn't start from a blank page.

## Mesh generation

Use `gmsh`'s Python API (pip-installable) to build the layered device geometry, then convert to XDMF via `meshio` for FEniCSx ingestion — this is exactly what the already-designed `FieldHandle.format = "xdmf_hdf5"` (see `thermal/results.py`) anticipates.

**Attempted 2026-07-23, real sandbox blocker found:** `gmsh`/`meshio` install cleanly via pip (`pyproject.toml`'s `mesh-generation` extra), but `gmsh`'s native library `dlopen`'s `libGLU.so.1` at import time — even for headless mesh generation with no GUI/rendering involved. This sandbox genuinely lacks that system library and has no working sudo (interactive password required, none available) to install it — confirmed via `ldconfig -p`/`dpkg -l`, not a first-try guess. See `tests/e2e/test_real_pipeline.py::test_gmsh_import_fails_in_this_sandbox_missing_libglu` and `docs/DECISIONS.md`. This is a sandbox-environment limitation, same class as DEVSIM's missing-BLAS blocker — the self-hosted CI runner (normal root access) is expected to install `libglu1-mesa` (or equivalent) and not hit this. **No mesh-generation code has been written yet** — writing it against an import that can't be verified to even succeed would mean untested code, which this project doesn't do.

**Update 2026-08-03 (`docs/M10_PLAN.md`):** a real fix was found and verified (in an isolated venv, outside this repo's own sandbox — still needs a from-scratch re-run here) that doesn't need the self-hosted runner at all. `gmsh` publishes an official headless "nox" (no-X11/no-OpenGL) dev build built without the FLTK/GUI path that pulls in `libGLU`; reproduced the exact `libGLU` failure with a plain `pip install gmsh` first (confirming the test case above still applies to that path), then confirmed `pip install -i https://gmsh.info/python-packages-dev-nox --pre gmsh` resolves to `4.15.0.dev1+nox` (satisfies this project's existing `>=4.12,<5` pin), imports clean, and generates a real 3D tetrahedral mesh — `meshio` then reads that mesh and writes real XDMF+HDF5, needing only the (trivial, pure-Python) `h5py` package. **The `--pre` flag is required** — without it, pip silently rejects every version on that index as a prerelease and the install fails outright. Full detail, including this gotcha and what's left to wire into `pyproject.toml`/`scripts/setup_env.sh`, in `docs/M10_PLAN.md` Phase 0. DEVSIM's separate BLAS/LAPACK blocker is unrelated and unaffected by this.

**Real design challenge:** a true MoS₂ monolayer is ~0.65nm thick against a ~285nm SiO₂ layer and a Si substrate that's effectively semi-infinite (hundreds of µm). A naive single mesh spanning all three would need enormous aspect-ratio elements or absurd element counts. This is not a hypothetical concern — this session's real HotSpot integration work (see `docs/DECISIONS.md`) hit an early, milder version of the exact same problem: even HotSpot's *compact* grid model became numerically/performance-problematic once a 300µm substrate layer was included alongside a 0.65nm channel layer in the same stack.

**Recommendation:** mesh the monolayer as a thin **surface** (a 2D manifold in a 3D mesh, or a boundary condition carrying the Joule-heating source and the Kapitza interface term — see below) rather than a thin 3D solid. This is physically defensible since MoS₂'s own through-thickness thermal resistance is negligible next to its interface resistance to SiO₂, and it avoids the degenerate-element problem entirely. Truncate the Si substrate at a finite depth (e.g. 10–50µm) with a Dirichlet fixed-temperature bottom boundary rather than modeling the full wafer.

## Boundary conditions

- **Bottom of the truncated Si substrate:** Dirichlet, fixed ambient temperature (or a convective/heat-sink Robin BC if a real packaging thermal-resistance number is available).
- **Top and lateral faces:** adiabatic (zero heat flux) as the Phase-1 default, with natural-convection Robin BCs as a documented refinement once cited h-values exist.
- **Heat source:** a single steady-state Joule-heating surface source on the channel layer, magnitude taken directly from a real `TransportResult.power_density_W_per_um2` — this is the natural point where the transport layer's real (DEVSIM/Kwant) output feeds M5's 3D thermal layer, closing the loop the architecture doc's data-flow diagram already implies.

## Interfacial (Kapitza) thermal resistance

A real physics gap, already flagged in an earlier session's research — TDTR/Raman-measured MoS₂/SiO₂ interface thermal resistance values exist in the literature and must be cited at implementation time, not invented now (same discipline as the seeded-benchmark citation work in `validation/benchmarks/`).

Two implementation approaches to weigh at implementation time:

- **(a) Proper interior-penalty formulation** (Nitsche-type discontinuous Galerkin), encoding a genuine temperature discontinuity at the interface. Physically correct, more FEniCSx implementation work.
- **(b) Pragmatic thin high-resistivity "interface layer"** of matched thickness/conductivity (`k_eff = t_thin / R_Kapitza`) inserted into an otherwise-standard continuous-Galerkin mesh. Much simpler to implement with FEniCSx's default Poisson/heat solver, small pragmatic error from finite thickness.

**Recommendation: start with (b)** for the first real case, with (a) as a flagged stretch goal once (b)'s results are cross-validated.

## FEniCSx ↔ Elmer coupling

Rather than building a fragile custom bridge that reads FEniCSx's XDMF/HDF5 temperature field and re-injects it into Elmer as a mechanical load, use **Elmer's own native multi-physics coupling** (its `HeatSolver` + `StressSolve` in a single `.sif` input file) for the coupled thermal+mechanical run, and keep the FEniCSx solve as an **independent thermal-only verification path** on the same underlying mesh (generate the mesh once with `gmsh`, convert it two ways — to XDMF for FEniCSx, and via `ElmerGrid` for Elmer — so both solvers see the identical geometry).

Treat "FEniCSx thermal-only" vs. "Elmer's own thermal solve" as a genuine cross-validation opportunity (do the two agree on `max_junction_temp_C`?) rather than a strict one-way dependency — this fits the project's own honesty culture better than inventing a custom, unverified coupling bridge. This does mean `ThermalResult.field_handle` from the Elmer path is Elmer-native output, not literally FEniCSx's own field — a nuance worth stating plainly when this section becomes real, rather than implying a single pipeline artifact flows unchanged through both solvers.

## Mesh convergence study (added 2026-07-22, docs/STANDARDS_AUDIT.md Tier 2)

The FEniCSx-vs-Elmer cross-solver check above (do the two agree on
`max_junction_temp_C`?) is a real, useful V&V technique, but it's *only*
code-to-code agreement — it doesn't establish that either solver's result
is actually mesh-independent. Per ASME V&V 10/20, mesh convergence is the
**verification** half (is the discrete solution converging to the
continuous one?), distinct from **validation** (does it match reality?) —
these were being conflated by only having a cross-solver check.

**Before any FEniCSx/Elmer result is trusted enough to compare against a
real experimental benchmark** (`validation/`'s `BenchmarkEntry`s), run a
convergence study on the minimal first 3D case below:

1. At least 3 refinement levels on the same geometry/BCs — e.g. `gmsh`'s
   characteristic length parameter halved at each step (coarse → medium →
   fine).
2. Report `max_junction_temp_C`'s % change between successive levels
   (coarse→medium, medium→fine).
3. **Convergence criterion (placeholder, revisit once real numbers
   exist):** treat the result as mesh-converged if the finest two levels'
   % change is under 2%. This threshold isn't citation-grade — it's a
   reasonable starting point to revisit once an actual convergence curve
   exists, not a value taken from a specific V&V standard's clause.
4. Only a mesh-converged result should ever populate
   `validation/schema.py`'s `SimulatedValue.uncertainty` (schema field
   added 2026-07-22) or be compared against an `ExperimentalValue` in a
   `BenchmarkEntry` — an unconverged result is a numerical artifact, not a
   physical prediction, regardless of what it says.

This convergence study is itself the real, concrete answer to "what does
'verified' mean for a `SimulatedValue`" (`docs/STANDARDS_AUDIT.md`'s
uncertainty/verification-vs-validation finding) — deliberately not defined
in the abstract in `validation/schema.py` itself, since no real solver in
this pipeline runs one yet.

## Minimal first 3D case

One MoS₂-monolayer-on-285nm-SiO₂-on-(truncated)Si device stack — the same "bare SiO₂" back-gated FET geometry already implicit in the existing `mos2_mobility_bare_sio2` benchmark's naming (see `validation/benchmarks/`), so this M5 case has a natural real-data target to validate against later.

- Single rectangular Joule-heating surface source sized to the channel footprint, magnitude from a real `TransportResult.power_density_W_per_um2`.
- Steady-state only (no transient/heat-capacity data yet — that's a further scope increase, not part of this minimal case).
- Outputs: max junction temperature (cross-checked between FEniCSx and Elmer per above) and peak interfacial stress at the MoS₂/SiO₂ boundary — the latter needs cited coefficient-of-thermal-expansion values for MoS₂ vs. SiO₂ vs. Si (another real citation task for M5, not invented now, same discipline as the Kapitza-resistance value).

## Lesson carried forward from this session's HotSpot work

Building the *compact* thermal model (`thermal/hotspot_backend.py`) this session surfaced a concrete, real instance of the scale-mismatch problem this document anticipates: a device stack combining a sub-nanometer channel layer with a hundreds-of-micron substrate layer created real numerical/performance problems even in HotSpot's simplified grid model, independent of any system-load issues encountered separately. That's direct, first-hand evidence (not a hypothetical) that M5's "mesh the monolayer as a thin surface, truncate the substrate" recommendation above is the right call, not just a theoretical concern.
