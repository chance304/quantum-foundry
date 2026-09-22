# Examples

Runnable from the repo root after `pip install -e .`. They all use the stub
backends, so no heavy solvers are needed.

| Script | What it shows |
|---|---|
| `01_single_device.py` | One MoS₂ device through all five pipeline stages, with per-stage provenance and the BEOL/M3D thermal-budget checks |
| `02_np_channel_search.py` | The n/p channel-material search and its Pareto fronts |

The CLI covers the same ground: `qf run MoS2_monolayer --backend stub` and
`qf heterostructure-search --format markdown`.
