# M9 Plan: Multi-Tier/Multi-Gate Device Physics — CFET, GAA, M3D (Design Only)

*This is a design document, not an implementation — see `docs/ROADMAP.md` for milestone status. Nothing here has been built yet. Written 2026-07-27, following the 2026-07-27 decision (see `docs/DECISIONS.md`) that real CFET/GAA/M3D physics and real stacked-chip thermal design are hard requirements, not backlog.*

## Why this exists

`DeviceGeometry.gate_type`/`stacked_tiers` (`transport/results.py`, added 2026-07-22) make CFET/GAA/M3D geometries *representable*. Verified directly (grep across the whole codebase) that nothing consumes either field except `ngmm_compat/chiplet_export.py`'s metadata passthrough — every real backend (`kwant_backend.py`, `devsim_backend.py`, `hotspot_backend.py`) implicitly models a single planar, single-gate channel regardless of what geometry is passed in. A device labeled CFET/GAA/M3D today silently gets single-planar physics back. This plan scopes what's actually needed to close that gap, and — unlike M5 — finds that a real, substantial slice of it is buildable **right now, without the self-hosted CI runner**.

## The three layers that need to change

### 1. Orchestration (`orchestration/pipeline.py`) — no sandbox blocker

Today `Pipeline.run()` assumes exactly one `DeviceGeometry` per run, producing exactly one `TransportResult`. A stacked device (`DeviceGeometry.stacked_tiers: list[DeviceTier]`) needs the transport stage invoked **once per tier** — each `DeviceTier` carries its own `channel_material_id`/`carrier_type`, so each tier is a distinct transport problem (e.g. a CFET's n-channel tier and p-channel tier are genuinely different materials/carriers, not one calculation run twice).

**Scope:** `Pipeline.run()` gains a branch — if `stacked_tiers` is set, run the transport (and DFT, for carrier-role-aware materials like WSe2) stage once per `DeviceTier`, collect a `list[TransportResult]` instead of one. Single-tier behavior (the only real case today) is unchanged — `stacked_tiers is None` keeps today's exact code path, matching this project's existing additive-only discipline on this field.

**No new dependency, no environment blocker** — this is pure Python restructuring of code that already exists and already runs in the current sandbox.

### 2. Thermal (`thermal/hotspot_backend.py`, `thermal/results.py`) — no sandbox blocker for the compact-model half

Found while reading the existing backend closely: `MaterialStack.layers` (`thermal/results.py`) already models a stack of `ThermalLayer`s by `role` (`"channel"` | `"gate_oxide"` | `"substrate"` | `"contact_metal"`), and `hotspot_backend.py`'s `is_powered = layer.role == "channel"` (line 166) would, in principle, mark *every* channel-role layer as power-dissipating if a stack had more than one. But `run(transport_result: TransportResult, stack: MaterialStack, params)` (line 208) takes a **single** `TransportResult` and applies its one `power_density_W_per_um2` value to every channel-role unit — physically wrong for a CFET's two independently-operating tiers, which have different Ion/Ioff/power from item 1's per-tier transport results.

**Scope:**
- Change `hotspot_backend.run()`'s signature to accept `transport_results: list[TransportResult]` positionally matched to the stack's channel-role layers (one per stacked tier), instead of a single `TransportResult`. Each tier's own real `power_density_W_per_um2` powers its own layer in the `.ptrace` file — no more borrowing one tier's power for another.
- Add an interfacial (Kapitza-style) `ThermalLayer` between adjacent tiers in `MaterialStack`, reusing the **exact technique already recommended in `docs/M5_PLAN.md`'s "Interfacial (Kapitza) thermal resistance" section** for the MoS2/SiO2 interface: a thin, high-resistivity layer sized so `k_eff = t_thin / R_Kapitza`. This is not new physics — it's the same approach applied at N-1 tier boundaries instead of one substrate interface. **Real candidate `R_Kapitza` value found 2026-07-27** (see `docs/ROADMAP.md`'s Kapitza item): Zheng, McClellan, Pop & Koh, *ACS Appl. Mater. Interfaces* 2022 (arXiv:2204.06975) gives R_eqm(MoS2/SiO2, 300K) ≈ 3.9×10⁻⁸ m²·K/W, derived from the paper's own stated R_int≈31 m²·K/GW and R_int/R_eqm=0.8. Used here as the best-available real analog for an inter-tier bonding-dielectric interface — no direct measurement of an actual wafer-bonded/layer-transfer interface was found, so this is a flagged approximation, not a perfect match. Still a caller-supplied param, never a hardcoded default (see `hotspot_backend.py`'s `run_stacked()`).

**No new dependency** — HotSpot itself is already built and working in this sandbox (unlike gmsh/FEniCSx/DEVSIM). This is the near-term, real, buildable piece of "stacked thermal design."

**What stays blocked on the runner:** the *3D FEA* half of stacked thermal design (real FEniCSx/Elmer multi-tier mesh, as opposed to HotSpot's compact multi-tier extension above) still needs `gmsh`, which still needs `libGLU.so.1` and the self-hosted runner — unchanged from M5's existing blocker. HotSpot's compact multi-tier model is the real Phase-1 answer to "stacked thermal design," with FEniCSx/Elmer as the eventual higher-fidelity cross-check once M5 unblocks, exactly the same "compact model now, full FEA later" relationship `docs/ARCHITECTURE.md` already establishes between `thermal/stub.py`/`hotspot_backend.py` and M5.

### 3. Transport (`transport/kwant_backend.py`, `transport/devsim_backend.py`) — split: one real near-term option, one blocked

Two genuinely different device families need two different answers:

**GAA (gate-all-around):** the real physics change is a gate wrapping the channel on all sides, which changes electrostatic screening/subband quantization — not a second stacked channel. `kwant_backend.py` already models a single-gate 2D lattice (`_make_potential()`, uniform Vgs coupling, no real 2D Poisson gate electrostatics even for the existing single-gate case — flagged in the module's own docstring). A first, honestly-approximate GAA treatment: strengthen/uniform-ize the existing gate-coupling term to model the wrap-around gate's stronger electrostatic control, explicitly flagged as *not* real 3D confinement/subband quantization (which would need a true 3D lattice, a much bigger lift). This is buildable now — Kwant already runs in this project's sandbox (built from source, 2026-07-21) — but needs a from-source Kwant install repeated in *this* clone/environment first (checked: `kwant` is not installed here yet).

**CFET (two vertically stacked, independently-doped/gated channels):** this is genuinely two coupled transport problems, not one. Two options, ordered by how real vs. approximate they are:
- **(a) Decoupled approximation (near-term, buildable now):** run `kwant_backend.py` once per `DeviceTier` (item 1's orchestration change makes this trivial), each tier its own independent 2D lattice/gate potential. This ignores real inter-tier electrostatic coupling (a CFET's shared/adjacent gate stack genuinely couples the two channels' potentials) — a real, named simplification, not presented as more than it is.
- **(b) Real coupled electrostatics:** needs a real 2D/3D DEVSIM mesh with two doped regions and a shared gate node — DEVSIM is the natural tool (already scaffolded, already has a real Caughey-Thomas mobility model per the 2026-07-22 Tier-2 decision) but its `_setup_drift_diffusion()` is still `NotImplementedError`, blocked in every sandbox tried so far on missing BLAS/no conda. This is the same blocker M5/DEVSIM already have — unchanged by this plan.

**Recommendation:** build (a) — the decoupled Kwant approximation — as the real Phase-1 CFET/GAA transport answer, explicitly flagged (same discipline as the existing same-material-contact and no-gate-electrostatics flags already in `kwant_backend.py`'s `extra` field) as ignoring inter-tier/wrap-around coupling. Treat DEVSIM's real coupled electrostatics as the eventual higher-fidelity path once the runner unblocks it — mirrors the exact Kwant-now/DEVSIM-later relationship the project's own `docs/ARCHITECTURE.md` "broad but shallow" table already established for single-tier transport.

## Sequencing vs M5

Unlike the original assumption that this whole requirement waits on M5, most of it doesn't:

| Piece | Blocked on runner? | Depends on |
|---|---|---|
| Orchestration: per-tier transport runs | No | Nothing new |
| Thermal: HotSpot multi-tier compact model + Kapitza interface layers | No | Nothing new — a real candidate `R_Kapitza` value was found 2026-07-27 (see above) |
| Transport: decoupled Kwant CFET/GAA approximation | No (but needs Kwant reinstalled in this clone — from-source build, same as 2026-07-21) | Nothing new |
| Transport: real coupled DEVSIM CFET electrostatics | **Yes** | Same DEVSIM/BLAS blocker as before |
| Thermal: real 3D FEniCSx/Elmer multi-tier FEA | **Yes** | Same gmsh/libGLU blocker as M5 |

**Recommendation:** start the three unblocked rows now, in parallel with — not sequenced after — M5's own runner-blocked work. Naming this milestone **M9** (next after M8) rather than folding it into M5, since it's a distinct capability with its own partially-independent unblocked path, but its two blocked rows should land alongside M5's equivalent pieces once the runner exists (same environment, same session, real efficiency to do both at once).

## What this plan deliberately does not do

No code has been written this round — this is scoping, matching this project's own established pattern (`docs/M5_PLAN.md`, `docs/CLOUD_BURST_PLAN.md` were both design-only passes before implementation). `docs/ROADMAP.md` is updated alongside this doc to turn the previous single backlog line into these five scoped, individually-sequenced tasks.
