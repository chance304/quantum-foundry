# M10 Plan: 3D Simulation Engine — Research Findings + Implementation Todolist (Design Only)

*This is a design/research document, not an implementation — see `docs/ROADMAP.md` for milestone status. Nothing here has been built. Written 2026-08-03 to scope a real "3D simulation engine" for the project. Matches the design-first precedent already set by `docs/M5_PLAN.md`, `docs/M9_PLAN.md`, and `docs/CLOUD_BURST_PLAN.md`.*

## Verification pass (2026-08-03, same day) — auditing the findings below against hard evidence, not search summaries

The initial research pass below (findings #1-#7) was written from web search/fetch results — this project's own established standard (see the Kapitza-resistance citation work in `docs/M9_PLAN.md`) is to distrust search summaries and verify primary sources directly. Did that here, in an isolated venv outside this repo, before the findings below were allowed to stand as-is. Three real corrections came out of it:

- **Finding #1 (gmsh-nox) is now CONFIRMED working, with an important integration gotcha found.** Reproduced the exact `OSError: libGLU.so.1: cannot open shared object file` on a plain `pip install gmsh` in a clean venv on a box that has `libGL`/mesa but not `libGLU` — the same failure class as `tests/e2e/test_real_pipeline.py::test_gmsh_import_fails_in_this_sandbox_missing_libglu`. Then confirmed `pip install -i https://gmsh.info/python-packages-dev-nox gmsh` imports clean, initializes, and generates a real 3D tetrahedral mesh (verified: box geometry, 341 nodes, 1159 tets, `gmsh.model.mesh.generate(3)` completes) — zero GL dependency. Also verified the full downstream step: `meshio` reads the `.msh` output and writes real XDMF+HDF5 (`thermal/results.py`'s `FieldHandle.format="xdmf_hdf5"` target format) — needs `h5py` as an extra pip dependency (trivial, pure-Python, not a system-library blocker like libGLU). **The gotcha:** this repo's existing `pyproject.toml` pin (`gmsh>=4.12,<5`) fails outright against the nox index without `--pre` — pip excludes dev/prerelease builds by default, and every version on that index is a `.devN+nox` build. Tested directly: `pip install -i https://gmsh.info/python-packages-dev-nox "gmsh>=4.12,<5"` errors with "Could not find a version that satisfies the requirement"; adding `--pre` resolves it correctly to `4.15.0.dev1+nox` and imports fine. **Action needed, not yet done**: `pyproject.toml`'s `mesh-generation` extra needs `--pre` wired into whatever installs it (`scripts/setup_env.sh` most likely), or the nox index won't actually get picked up even by someone who reads this doc and tries the fix. Still needs re-verification inside this repo's own dev sandbox (proven here in an equivalent-but-different environment, not literally this repo's CI) — but the mechanism itself, and the exact pitfall, are now hard-verified, not a hopeful lead.

- **Finding #5 (3D-ICE) license reconfirmed via GitHub's own license API (`gpl-3.0`, standard `COPYING` file) — but a real integration-cost finding was missed the first pass.** 3D-ICE is a C project (`Makefile`, `bison`/`flex` codegen, bundles `superlu_mt-4.0.0.zip`), not a pip/conda-installable Python package like every other tool in this stack (DEVSIM, Kwant, FEniCSx all install via `environment.yml`/pip). Building it means a real from-source C build step, closer in cost to Elmer's own still-unbuilt Docker path than to a `pip install`. Worth stating plainly in the evaluation spike, not glossed over as "just install it and compare."

- **Finding #6 (NanoTCAD ViDES) is downgraded — do not treat as a live near-term candidate without a lot more diligence.** Both plausible official URLs failed independently: `vides.nanotcad.com` resolves to a TLS certificate for an unrelated Italian business (`autotappezzeria.eu`) — the domain has almost certainly lapsed and been re-registered by someone else — and `nanohub.org/tools/vides` refused the connection outright (tested twice, including with a browser user-agent, both timed out). No official GitHub repo exists. Two **unofficial** mirrors were found: `aravindhk/Vides` (stale since 2020) and `manishthatte/NanoTCAD_ViDES` (actively updated, last push 2026-04, explicitly patched for current Python/NumPy/GCC) — but GitHub reports both as license `"Other"`, meaning no machine-recognized open-source grant, not a confirmed permissive/copyleft license. **Revised recommendation:** this is no longer a "confirm the license, then spike it" item — the tool's own official presence appears to be gone, and the only maintained fork's licensing is genuinely unclear. Treat as a low-confidence lead requiring real legal/provenance diligence before spending any engineering time on it, not a near-term evaluation spike alongside 3D-ICE.

- **Finding #3 (CTE citation) — got the paper's real identity, but found a real, unresolved numeric discrepancy that must not be papered over.** Confirmed the full citation: Yang, Lin, Long et al., "Thermal expansion coefficient of monolayer MoS2 determined using temperature-dependent Raman spectroscopy combined with finite element simulations," *Microstructures* 2021;1:2021002, DOI 10.20517/microstructures.2021.02. But two independent extraction passes of this same paper returned two different TEC values — 24.4×10⁻⁶ K⁻¹ (from a search-result summary) vs. 7.13×10⁻⁵ K⁻¹ i.e. 71.3×10⁻⁶ K⁻¹ (from a full-text fetch, attributed to the paper's Figure 6/Table 2) — a ~3x discrepancy on the same claimed source. Per this project's own rule (never cite a search-summarized number — read the primary PDF directly, exactly as the Kapitza-resistance citation work already did), **neither number should be used** until someone directly reads the actual PDF and confirms which figure/table the real value comes from. Flagging the discrepancy itself is the correct move here, not picking whichever number sounds more plausible.

## What "3D simulation engine" actually means here

Not a new layer — this milestone is the thing M5 and M9 were already scoping toward, named as one initiative: the two genuinely-3D physics gaps still open across the codebase, both currently blocked on the same root cause (no self-hosted CI runner registered yet):

| Piece | Milestone | Status before this doc |
|---|---|---|
| 3D mesh generation (`gmsh`/`meshio`) | M5 | Blocked: `libGLU.so.1` missing in every sandbox tried |
| FEniCSx thermal-only 3D FEA | M5 | Not built — blocked on mesh generation |
| Elmer coupled thermo-mechanical FEA | M5 | Not built — blocked on mesh generation; `docker/elmer.Dockerfile` scaffolded, never built |
| Real coupled DEVSIM 3D electrostatics (CFET shared-gate) | M9d | Blocked: missing BLAS/LAPACK, no conda in sandbox |
| Real 3D FEniCSx/Elmer multi-tier FEA (stacked geometry) | M9e | Blocked: same as M5's FEA rows, applied per-tier |

This doc's job: (1) bring back real research on the current (Aug 2026) open-source landscape for these pieces — confirming, correcting, or extending `docs/M5_PLAN.md`'s tool choices — and (2) turn that into one sequenced, actionable todolist spanning M5+M9's remaining runner-blocked work plus two new candidate technologies found this pass.

## Research findings (2026-08-03 pass)

**1. The `gmsh`/`libGLU` blocker may have a real fix that doesn't need the self-hosted runner at all.** `gmsh` publishes an official headless "nox" (no-X11/no-OpenGL) dev build from its own package index, built without the FLTK/GUI code path that pulls in `libGLU` even for pure mesh generation:

```
pip install -i https://gmsh.info/python-packages-dev-nox --force-reinstall --no-cache-dir gmsh
```

This is gmsh's own published index (gmsh.info), not a third-party package — a real candidate fix, **not yet verified in this sandbox or any of this project's environments**. If it works, M5's mesh-generation step (and M9d's DEVSIM-via-gmsh 3D meshing, since DEVSIM interfaces with gmsh for unstructured 3D meshes) could unblock *before* the self-hosted runner exists, leaving only DEVSIM's separate BLAS/LAPACK gap and QE/Wannier90's conda requirement genuinely runner-dependent. Caveat: "nox" builds track gmsh's dev/nightly index, not a numbered PyPI release — pin and record the exact working version once verified, and don't assume feature parity with the mainline `gmsh` wheel without checking.

**2. DEVSIM's blocker is unrelated to gmsh's and unaffected by the above** — still needs a real BLAS/LAPACK (conda, or the self-hosted runner's normal package manager). No no-root fix found for this one. Unchanged from `docs/DECISIONS.md`'s existing finding.

**3. Real candidate citation found for the CTE (thermal expansion) gap** — `docs/STANDARDS_AUDIT.md` line 289 and `docs/M5_PLAN.md`'s "peak interfacial stress" note both flag this as genuinely unsourced. Candidates found this pass (**not yet verified to this project's citation-completeness standard — full author/year/DOI/figure-ref still needed before use, same discipline as every other seeded citation**):
   - Monolayer MoS₂ in-plane CTE ≈ 24.4×10⁻⁶ K⁻¹ — candidate source: "Thermal expansion coefficient of monolayer MoS₂ determined using temperature-dependent Raman spectroscopy combined with finite element simulations" (*Microstructures*, 2021, oaepublish.com/articles/microstructures.2021.02). Note this is markedly larger than bulk MoS₂'s in-plane CTE (~5.0×10⁻⁶ K⁻¹ reported elsewhere) — a real monolayer-vs-bulk discrepancy to state explicitly if used, not smoothed over (same honesty pattern as this project's other anomalous-value flags, e.g. WS2's effective mass).
   - SiO₂ (amorphous thin film) CTE ≈ 0.5×10⁻⁶ K⁻¹ — needs a specific thin-film source, not a generic bulk-quartz number.
   - Si CTE ≈ 2.6×10⁻⁶ K⁻¹ — well-established, easiest of the three to pin to a standard reference.
   This closes real research legwork but is a lead list, not finished citations — whoever implements M5's stress calculation still has to fetch each paper and confirm the exact figure/table per this project's citation rule.

**4. The Kapitza resistance gap is already closed — reuse it, don't re-research it.** `docs/M9_PLAN.md` (this same branch, commit `ef6776f`) already found and cited a real value: Zheng, McClellan, Pop & Koh, *ACS Appl. Mater. Interfaces* 2022 (arXiv:2204.06975), R_eqm(MoS₂/SiO₂, 300K) ≈ 3.9×10⁻⁸ m²·K/W. That was sourced for M9's inter-tier bonding-dielectric analog use, but it's the same physical MoS₂/SiO₂ interface `docs/M5_PLAN.md`'s original FEA design needs — wire the same citation through both places rather than sourcing it twice.

**5. New candidate technology — 3D-ICE** (EPFL, `github.com/esl-epfl/3d-ice`, GPLv3, v4.0 released late 2025). A compact thermal model purpose-built for vertically-stacked 3D ICs with inter-tier (optionally liquid-cooled) thermal resistance networks, validated against real measured 3D ICs (<10% average error per the published validation). This is a much closer domain match to this project's own "3D-stacking simulator" framing than adapting HotSpot (a single-die floorplan tool) was — M9b already did that adaptation by hand (`run_stacked()`, custom Kapitza-layer extension). Worth a real head-to-head evaluation, not an assumed replacement: does 3D-ICE's purpose-built inter-tier network formulation do better than the custom extension already built and working? **Flag before adopting: GPLv3 is copyleft.** This project is Apache-2.0, so 3D-ICE could only ever be driven as a separate executable (the same subprocess boundary used for gmsh, Elmer and HotSpot), never linked or imported.

**6. New candidate technology — NanoTCAD ViDES** (`vides.nanotcad.com`, "freely available to researchers"). Solves the 3D Poisson equation self-consistently with NEGF quantum transport, purpose-built for 2D-material and arbitrary-heterostructure devices with arbitrary gate geometry — directly on-target for the real, already-flagged gap in M9c's Kwant-based GAA approximation ("not real 3D confinement/subband quantization... would need a true 3D lattice, a much bigger lift") and for Kwant's own known tractability wall (~4,000 sites, hit during this project's own toy-geometry work). **Flag before adopting:** "freely available to researchers" is not confirmed to be an OSI-approved open-source license — this needs an explicit license/redistribution check (same discipline as flag #5) before treating it as a drop-in stack component, unlike Kwant/DEVSIM/FEniCSx which are unambiguously open-source licensed.

**7. Elmer-in-Docker has real, working prior art to crib from.** EOF-Library (`github.com/jvencels/EOF-Library`, couples Elmer+OpenFOAM) publishes real, maintained images (e.g. `eoflibrary/eof_elmer84_of6`) that actually run coupled Elmer solves in containers today. This project's own `docker/elmer.Dockerfile` is scaffolded but never built or run (`docker/README.md`'s own status note) — EOF-Library's Dockerfile structure is a real, working reference to build from rather than starting from zero.

## Implementation todolist

### Phase 0 — Try the no-root unblock first (do this before anything else)
- [x] ~~Attempt the gmsh-nox install and confirm it actually imports/meshes~~ — **done 2026-08-03 in an isolated venv outside this repo** (see "Verification pass" above): reproduced the exact `libGLU` failure on a plain `pip install gmsh`, then confirmed `pip install -i https://gmsh.info/python-packages-dev-nox --pre gmsh` resolves to `4.15.0.dev1+nox` (matching this repo's existing `>=4.12,<5` pin), imports clean, and generates a real 3D tet mesh. **Still needs a from-scratch re-run inside this repo's own dev sandbox/CI image before treating it as fully closed** — proven in an equivalent environment, not literally this repo's own.
- [ ] Wire `--pre` into whatever actually installs the `mesh-generation` extra (`scripts/setup_env.sh`, most likely as a special-cased install line pointing at the nox index) — **found the hard way**: the plain `-i <nox-index> "gmsh>=4.12,<5"` install fails outright without `--pre`, since pip excludes dev/prerelease builds by default and every version on that index is a `.devN+nox` build. This is a real, easy-to-miss integration gotcha, not just "add the index URL."
- [ ] Add `h5py` to the `mesh-generation` extra in `pyproject.toml` — verified needed for `meshio`'s XDMF+HDF5 writer (`FieldHandle.format="xdmf_hdf5"`'s actual target format), currently missing from the extras list.
- [ ] Once wired: retire or rewrite `tests/e2e/test_real_pipeline.py::test_gmsh_import_fails_in_this_sandbox_missing_libglu` to match reality, and log the result in `docs/DECISIONS.md` either way.
- [ ] Re-confirm DEVSIM's BLAS blocker is still the only thing standing between M9d and this same sandbox (separate root cause from gmsh — the nox fix does not touch it)

### Phase 1 — Mesh generation (M5's first real code; design already written in `docs/M5_PLAN.md`)
- [ ] Build the layered-slab geometry via `gmsh`'s Python API: MoS₂ monolayer as a thin surface/boundary (not a 3D solid), truncated Si substrate (10-50µm) with Dirichlet bottom BC — exact design already in `docs/M5_PLAN.md`
- [ ] Convert to XDMF via `meshio` for FEniCSx (`thermal/results.py`'s `FieldHandle.format="xdmf_hdf5"` already anticipates this)
- [ ] Also emit via `ElmerGrid` from the same `gmsh` geometry, so FEniCSx and Elmer solve on the identical mesh (required for Phase 5's cross-solver check)
- [ ] Test: element count/aspect-ratio sanity checks, both export formats actually load in their respective solvers

### Phase 2 — Close the two real citation gaps before any number is trusted
- [ ] The CTE paper's identity is now confirmed (Yang, Lin, Long et al., *Microstructures* 2021;1:2021002, DOI 10.20517/microstructures.2021.02 — see "Verification pass" above), but **its actual reported value is not** — two extraction passes gave 24.4×10⁻⁶ K⁻¹ and 71.3×10⁻⁶ K⁻¹ for the same claimed figure/table. Read the actual PDF directly (same method as the Kapitza citation's `pypdf` read, not another summarized fetch) before writing any `Citation` record. Still need SiO₂ (thin-film-specific, not bulk quartz) and Si CTE sources too — neither attempted this pass.
- [ ] Wire the existing Kapitza citation (finding #4, already in `docs/M9_PLAN.md`) into M5's FEA interface code — reuse, don't re-derive

### Phase 3 — FEniCSx thermal-only solve
- [ ] Steady-state heat equation on the Phase-1 mesh; single Joule-heating surface source sized from a real `TransportResult.power_density_W_per_um2`
- [ ] BCs per `docs/M5_PLAN.md`: Dirichlet fixed-temp bottom, adiabatic top/lateral (Phase-1 default)
- [ ] Kapitza interface via the "(b) pragmatic thin high-resistivity layer" approach `docs/M5_PLAN.md` already recommends starting with (`k_eff = t_thin / R_Kapitza`)
- [ ] New `thermal/fenicsx_backend.py` behind the existing `ThermalBackend` protocol/registry; populate `FieldHandle`

### Phase 4 — Elmer coupled thermo-mechanical solve
- [ ] Actually build `docker/elmer.Dockerfile` (currently scaffolded, never built) — use EOF-Library's images (finding #7) as a working structural reference
- [ ] Write the `.sif` input (`HeatSolver` + `StressSolve` in one file, Elmer's native multi-physics coupling per `docs/M5_PLAN.md`), same mesh via `ElmerGrid`
- [ ] New `thermal/elmer_backend.py`; this is the only backend that populates `ThermalResult.stress_MPa`

### Phase 5 — Verification (mandatory gate before any result touches `validation/`)
- [ ] Mesh convergence study: ≥3 refinement levels, report `max_junction_temp_C`'s % change between levels, treat <2% (finest two levels) as the Phase-1 convergence criterion — full spec already in `docs/M5_PLAN.md`
- [ ] FEniCSx-vs-Elmer cross-solver check on `max_junction_temp_C` (code-to-code agreement — verification, not validation, per ASME V&V 10/20; `docs/M5_PLAN.md` already makes this distinction explicit)
- [ ] Only a mesh-converged, cross-checked result may populate `SimulatedValue.uncertainty` or be compared against a `BenchmarkEntry`

### Phase 6 — Extend to multi-tier stacking (M9e — same solvers, stacked geometry)
- [ ] Generalize Phases 1-4 to N-tier stacks, reusing M9b's per-tier Kapitza-layer pattern (already built for HotSpot) but with real 3D FEA instead of HotSpot's compact grid
- [ ] Cross-check against M9b's existing `run_stacked()` HotSpot-based results — same "compact model now, full FEA as higher-fidelity cross-check later" relationship the architecture doc already establishes

### Phase 7 — Real coupled DEVSIM 3D electrostatics (M9d)
- [ ] Once BLAS/LAPACK is resolved (self-hosted runner, or any environment with a working conda): implement `devsim_backend.py`'s `_setup_drift_diffusion()` on a real 3D mesh, reusing Phase 1's `gmsh` geometry via DEVSIM's own native `gmsh` interface
- [ ] Real coupled CFET electrostatics (two doped regions, shared gate node) per `docs/M9_PLAN.md` option (b) — the eventual higher-fidelity replacement for M9c's decoupled-Kwant approximation

### Phase 8 — Evaluate the two new-technology candidates (research spikes, not committed adoptions)
- [ ] **3D-ICE spike**: confirm 3D-ICE can be driven purely as an external executable *first* (confirmed via GitHub's license API, not just the project page — see "Verification pass" above) — no point evaluating a tool that turns out to be undeliverable. If cleared: budget real time for a from-source C build (`Makefile`/`bison`/`flex`, bundled `superlu_mt`) — this is not a `pip install`, closer in cost to Elmer's own still-unbuilt Docker path. Then run its own example stacked-IC case and compare its inter-tier network formulation against M9b's HotSpot extension on the same device.
- [ ] **NanoTCAD ViDES — do not schedule this as a near-term spike.** Verified 2026-08-03: the official site (`vides.nanotcad.com`) now resolves to an unrelated business's certificate and `nanohub.org/tools/vides` refuses connections outright — the tool's official presence appears to have lapsed. Only unofficial GitHub forks exist, both licensed `"Other"` (no confirmed grant). If this is ever pursued, the real first step is a legal/provenance review of the actively-maintained fork (`manishthatte/NanoTCAD_ViDES`, last updated 2026-04) — not a physics evaluation — and that review should happen independently of this milestone's sequencing, not blocking Phases 0-7.
- [ ] Both end in a real keep/drop/replace decision logged in `docs/DECISIONS.md` — not left open-ended.

### Phase 9 — The actual master blocker
- [ ] Self-hosted CI runner registration (`scripts/setup_github_runner.sh`) — the one action item that unblocks Phase 4 (Elmer, if Docker-in-CI needs it), Phase 7 (DEVSIM), and QE/Wannier90 ab-initio, all at once. Everything else in this doc is either already unblocked or a research spike.
- [ ] Once registered: re-verify DEVSIM actually imports and conda pulls a correctly-named OpenBLAS (flagged as unverified in `docs/DECISIONS.md`), and re-verify QE/Wannier90 conda-forge packaging is still current.

## Open questions — real decisions, not assumed

- [ ] **3D-ICE's GPLv3 vs. this project's Apache-2.0 license.** Confirmed via GitHub's license API (`gpl-3.0`), not just the project page. Acceptable only behind a process boundary; needs confirming before Phase 8's 3D-ICE spike, not during it.
- [ ] **NanoTCAD ViDES — likely not worth pursuing at all.** Its official site appears to have lapsed (see "Verification pass" above); the only maintained fork's license is unconfirmed (`"Other"` per GitHub). Worth a quick go/no-go so this doesn't linger as an open item nobody actively owns.
- [ ] **Sequencing preference once the runner exists**: does multi-tier stacking (M9d/e) outweigh single-tier 3D FEA fidelity (M5) for whichever gets built first? Both are runner-gated; only one clock will start first in practice.

## Open technical item

- [ ] **`pyproject.toml`'s `mesh-generation` extra needs a real fix, not just a version bump.** Its current pin (`gmsh>=4.12,<5`) silently fails against the gmsh-nox index without `--pre` (pip excludes prereleases by default; every nox-index version is a dev build). Whoever runs Phase 0 needs to know this going in — `scripts/setup_env.sh` is the natural place to special-case this install line, since a standard `pyproject.toml` dependency string can't express "use `--pre` and a different index for just this one package."

## Explicit non-scope for this document

Matches `docs/M5_PLAN.md`/`docs/M9_PLAN.md`/`docs/CLOUD_BURST_PLAN.md`'s own precedent exactly:
- No code written this round.
- No dependency installed, no gmsh-nox fix actually attempted yet — Phase 0 is the first real action, not done here.
- No license decision made on 3D-ICE/NanoTCAD ViDES — flagged, not decided from research alone.
- Self-hosted runner registration itself is out of scope here — needs a maintainer-controlled persistent machine, unchanged from M5/M9's existing framing.
