# Roadmap

What's built, what's next, and what's blocked. Milestone numbers (M1–M11)
match the entries in `docs/DECISIONS.md` and `CHANGELOG.md`. Items marked
**good first issue** need no heavy solver installed.

## Built

- **M1** Materials layer: typed schema, per-field citations, 10 seeded materials (JARVIS-DFT / C2DB / Materials Project / named papers).
- **M2** Validation layer: 6 literature benchmarks, %-error reporting, stub-vs-real provenance in every report.
- **M3** Real backends: Kwant NEGF transport, HotSpot compact thermal model, Poisson/Murphy/negative-binomial yield.
- **M6** n/p channel-material search and Pareto ranking (`qf heterostructure-search`).
- **M7** Behavioural Verilog-A export (`qf export-verilog-a`).
- **M8** NGMM-style chiplet collateral export (`qf export-chiplet`), clearly disclaimed as unverified against any official schema.
- **M9a–c** Multi-tier devices (CFET/GAA/M3D): per-tier orchestration, multi-tier HotSpot thermal with Kapitza interface layers, and an explicitly flagged Kwant path.
- **M11** 3D mesh generation for the layered device stack (gmsh, run out-of-process) with XDMF export for FEniCSx.

## Next: needs a real-solver environment

These need the conda environment from `scripts/setup_env.sh` (and in some
cases HPC-scale compute).

- **DEVSIM drift-diffusion**: `transport/devsim_backend.py`'s `_setup_drift_diffusion()` is still `NotImplementedError`. Needs a BLAS/LAPACK-equipped environment to verify the import first.
- **M5 3D FEA**: real FEniCSx/Elmer thermal solves on the M11 mesh, followed by a mesh-convergence study (≥3 refinement levels, placeholder <2% criterion on `max_junction_temp_C`). Plan in `docs/M5_PLAN.md` and `docs/M10_PLAN.md`.
- **M9d** Coupled DEVSIM electrostatics for stacked tiers; **M9e** real 3D FEA for stacked tiers. See `docs/M9_PLAN.md`.
- **Ab-initio**: Quantum ESPRESSO + Wannier90 backend (design only today).
- **Ephemeral compute burst** for the heavy runs: design in `docs/CLOUD_BURST_PLAN.md`.
- **`conda-lock.yml`**: generate it by actually running `conda-lock lock` against a validated `environment.yml` (never hand-write it).

## Next: research and data (good first issues)

- Source a citable **catastrophic defect density (D0)** for CVD-grown 2D-TMD films. Atomic point-defect densities are the wrong quantity for the yield model. `poisson_murphy.py` refuses to run without one rather than inventing it.
- Source a citable **Stapper clustering parameter (α)** for 2D-TMD wafer-scale growth. Si CMOS values (0.3–5) exist; none specific to 2D TMDs were found.
- Source citable **Matthiessen's-rule scattering coefficients** for MoS₂/WS₂/WSe₂ CVD films (`transport/mobility_degradation.py`).
- Reconcile **JVASP-653 vs JVASP-652** for WSe₂: two JARVIS-DFT runs disagree on band gap, lattice constant and dielectric constant.
- Transcribe **HfO₂/ZrO₂ lattice parameters** from Materials Project mp-352 / mp-2858 (needs an `MP_API_KEY`).
- Fold **black phosphorus** into `jarvis_dft.py`'s auto-fetch once anisotropic `extra` fields are supported.
- **Docstrings**: roughly 70% of public functions lack one (module docstrings are thorough). Add inputs/outputs/units when you touch a function.

## Known issues

- **`dibl_mV_V` in `transport/kwant_backend.py` is not real DIBL.** The potential model has no Vds dependence, so the value is a measurement-method artifact. It is flagged in the output and must not be read as physics until real Vds electrostatics exist.
- **The internal SiO₂/Si interface is tagged `adiabatic_boundary` in the M11 mesh.** The "everything except top and bottom" rule also captures the internal fragment face at z = 0. It is harmless for FEniCSx (`ds` only integrates exterior facets), but an Elmer boundary condition on that tag would wrongly insulate the interface. Fix before the M5 Elmer backend consumes the mesh.
- **Data contracts predate the real solvers.** Expect real backends to need fields not modelled yet (e.g. DEVSIM doping profiles). Use the `extra` escape hatch on each `Result` and log the revision in `docs/DECISIONS.md`.

## External programs (context, not commitments)

- **DARPA NGMM Design Challenge**: a solicitation is expected around Q1 FY27. That is inferred from the program plan, not a published date. `ngmm_compat/` exports are best-effort, disclaimed, and unverified against any official schema. See `docs/NGMM_COMPATIBILITY.md`.
- Never upgrade `ngmm_compat`'s packaging-compatibility placeholders to an affirmative claim without a real citation. The 2D-material bonding question is genuinely unresolved.
