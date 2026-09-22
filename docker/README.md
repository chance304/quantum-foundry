# docker/

## elmer.Dockerfile

Elmer FEM (coupled thermo-mechanical solver) has no reliable conda-forge feedstock, unlike the rest of this project's real backends (Quantum ESPRESSO, Wannier90, DEVSIM, Kwant, FEniCSx — all in `environment.yml`). Rather than fight a source build on every developer/CI machine, it's containerized once here. See `docs/DECISIONS.md` for the reasoning.

**Status:** scaffolded, not yet built or verified against a real Elmer run (M0, this session). Building and smoke-testing this image is part of M5 (deep validation), when `thermal/elmer_backend.py` actually needs to call it.

Build:

```sh
docker build -t quantum-foundry-elmer -f docker/elmer.Dockerfile .
```

`thermal/elmer_backend.py` shells out to this image (`docker run`) unless `scripts/preflight.sh` finds an `ElmerSolver` binary already on `PATH` — see that script for the exact detection order.
