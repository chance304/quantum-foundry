# Quantum Foundry

[![CI](https://github.com/chance304/quantum-foundry/actions/workflows/ci.yml/badge.svg)](https://github.com/chance304/quantum-foundry/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

An open-source, multi-physics simulator for post-silicon and 3D-stacked
semiconductor devices. It predicts which 2D channel materials, device
geometries (planar, GAA nanosheet, CFET, monolithic 3D) and stacking choices
are worth fabricating, and ranks every candidate on performance, thermal
limits **and** manufacturability together, before anything goes near a fab.

The core rule of the project: **never present a number a solver didn't
actually produce.** Every result carries provenance (`is_stub`, backend,
citation), and every material property that isn't computed cites a named
paper or database.

Project write-up: <https://shobhittripathi.com/quantum-foundry/>

## Why

The June-2026 imec/ASML/TSMC 300mm 2D-material CMOS demonstration established
MoS₂ as the strongest available n-type channel and WSe₂/WS₂ as the strongest
p-type, with no single material doing both well. Quantum Foundry's sweep and
Pareto engine searches material, dielectric and stacking combinations for
that n/p-asymmetry problem, while staying general enough for other materials
and geometries.

## Architecture

1. **Materials database**: a typed schema (bandgap, effective masses,
   mobility, contact resistance $R_c$, thermal conductivity, work function,
   defect density) seeded from [JARVIS-DFT](https://jarvis.nist.gov/) and
   [C2DB](https://cmr.fysik.dtu.dk/c2db/c2db.html), cross-checked against the
   [Materials Project](https://materialsproject.org/) for gate dielectrics
   ($HfO_2$, $ZrO_2$). Every value carries a per-field citation.
2. **Multi-physics pipeline**: each layer sits behind a Protocol with a fast
   stub backend and a real-solver backend:
   - **Ab-initio:** [Quantum ESPRESSO](https://www.quantum-espresso.org/) + [Wannier90](http://www.wannier.org/)
   - **Device transport:** [DEVSIM](https://devsim.com/) (drift-diffusion) + [Kwant](https://kwant-project.org/) (atomistic NEGF)
   - **Thermal/mechanical:** [FEniCSx](https://fenicsproject.org/) (3D FEA) + [Elmer](https://www.elmerfem.org/) (coupled thermo-mechanical) + [HotSpot](https://github.com/uvahotspot/HotSpot) (fast compact-model pre-filter)
   - **Manufacturability/yield:** custom Monte Carlo plus closed-form Poisson/Murphy yield models. No mature open-source package exists for this layer.
3. **Sweeps and Pareto optimization**: parameter sweeps across materials,
   stacking and dielectrics, with PPA + thermal + yield trade-off reports.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and
[`docs/DECISIONS.md`](docs/DECISIONS.md) for why each choice was made.

## Quickstart

Requires Python 3.11+. The stub pipeline needs no heavy solvers:

```bash
uv venv --python 3.11 .venv && source .venv/bin/activate   # or python3.11 -m venv .venv
pip install -e ".[dev]"
qf --help
qf run MoS2_monolayer --backend stub
pytest -m "not requires_real_solver"
```

See [`examples/`](examples/) for runnable scripts.

**Real backends** (Quantum ESPRESSO, Wannier90, DEVSIM, Kwant, FEniCSx,
HotSpot) need `conda`/`mamba`: run `scripts/setup_env.sh`, which builds the
`quantum-foundry` environment from `environment.yml`, clones HotSpot at a
pinned commit and installs gmsh's headless build for mesh generation. Elmer
runs in a container (`docker/elmer.Dockerfile`). Before any
`--backend real` run, `qf preflight` reports what is actually available and
refuses to proceed silently if something required is missing.

## Status

| Layer | State |
|---|---|
| Materials database | 10 cited 2D materials and dielectrics |
| Validation/benchmarks | 6 literature benchmarks, each anchored to a figure/table |
| Transport | Kwant NEGF **real**; DEVSIM backend written, needs a BLAS-equipped runner |
| Thermal | HotSpot compact model **real** (incl. multi-tier stacks with Kapitza interfaces); 3D mesh generation **real**; FEniCSx/Elmer FEA designed, not built |
| Stacked devices (CFET/GAA/M3D) | per-tier orchestration and multi-tier thermal **real**; coupled 3D electrostatics not built |
| Yield | Monte Carlo + Poisson/Murphy **real** |
| Ab-initio | designed, not built |

Anything not marked real runs through a stub and is labelled as such in every
output. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's next.

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md)
(every commit needs a DCO sign-off) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Report security issues privately as
described in [`SECURITY.md`](SECURITY.md).

## Citing

If you use Quantum Foundry in research, please cite it using
[`CITATION.cff`](CITATION.cff).

## License

Apache-2.0. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE) (including CC BY 4.0
attribution for bundled materials data) and
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
