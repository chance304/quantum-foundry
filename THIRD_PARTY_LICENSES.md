# Third-party licenses

Quantum Foundry's own code is licensed under Apache-2.0 (see `LICENSE`). It
does **not** bundle or statically link any of the tools below. Core runtime
dependencies are pip-installed; the heavy scientific backends are optional,
installed separately (conda, Docker, or a pinned clone), and detected at
runtime by `scripts/preflight.sh`. Anything GPL-licensed is only ever run as
a separate process or container, never imported into the Python process.

## Core Python dependencies (installed by pip)

| Package | License | How it is used |
|---|---|---|
| NumPy | BSD-3-Clause | imported |
| SciPy | BSD-3-Clause | imported |
| PyYAML | MIT | imported |
| Typer | MIT | imported (CLI) |

## Optional extras (installed by pip)

| Package | Extra | License | How it is used |
|---|---|---|---|
| jarvis-tools | `materials-sources` | MIT (NIST) | imported, to fetch JARVIS-DFT data |
| meshio | `mesh-generation` | MIT | imported, mesh I/O |
| h5py | `mesh-generation` | BSD-3-Clause | imported via meshio (XDMF/HDF5) |

## Optional scientific backends (installed separately)

| Tool | License | How it is used |
|---|---|---|
| Kwant | BSD-2-Clause | imported (atomistic NEGF transport) |
| DEVSIM | Apache-2.0 | imported (drift-diffusion transport) |
| ASE | LGPL-2.1-or-later | imported, unmodified, to read C2DB data |
| mp-api | BSD-3-Clause (modified) | imported, to query the Materials Project |
| FEniCSx / DOLFINx | LGPL-3.0-or-later | planned 3D FEA backend, not yet invoked |
| gmsh | GPL-2.0-or-later | **subprocess only**: a generated `.geo` script is passed to the `gmsh` executable |
| Elmer | GPL-2.0 / LGPL-2.1 | **container only**: runs inside `docker/elmer.Dockerfile` |
| HotSpot | BSD-style academic license (University of Virginia) | **subprocess only**: cloned at a pinned commit by `scripts/setup_env.sh`, not committed |
| Quantum ESPRESSO | GPL-2.0-or-later | planned ab-initio backend, subprocess only, not yet invoked |
| Wannier90 | GPL-2.0-or-later | planned, subprocess only, not yet invoked |

## Data

Seed materials data derived from JARVIS-DFT, C2DB and the Materials Project
is used under CC BY 4.0. Attribution is in `NOTICE`, and every value carries
its own per-field citation in the seed-data files.
