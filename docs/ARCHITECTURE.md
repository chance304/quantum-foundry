# Architecture

## Positioning for adjacent programs (readiness, not current scope)

Research 2026-07-20 confirmed three real external programs worth staying compatible with, without building for them now:

- **DARPA NGMM** (Next-Generation Microelectronics Manufacturing, $840M, 3D heterogeneous integration) — the near-term Shopping Notice **DARPA-SN-26-69** (deadline 2026-07-31) was evaluated and declined as a target (poor fit: immature toolkit, no 2D materials on its supported list, video-only submission). The real target is the later **NGMM Design Challenge Program** (~Q1 FY27, ~6 months out) — see `docs/NGMM_COMPATIBILITY.md` for full reasoning and the `ngmm_compat/` compatibility layer (§ below) built toward it.
- **CHIPS NAPMP** (NIST, up to $1.6B) — real program; confirmed focus areas include Power Delivery and Thermal Management, and Co-design/EDA. No confirmed live 2026 solicitation window found. Readiness implication: same EDA-interoperability point as above; power-delivery/IR-drop modeling is out of current scope but would be a real gap if NAPMP is pursued directly.
- **imec/TSMC/ASML 300mm 2D-material CMOS** — the 94% operational-transistor figure is real (confirmed against the actual VLSI Symposium 2026 announcement) and already anchors this project's n/p-asymmetry strategy (see README). A reported "public open call for simulation-tool ecosystem partners" could **not** be confirmed from primary sources, so nothing here depends on one.

Two concrete readiness items tracked in `docs/ROADMAP.md`: (1) plan for an EDA-compatible export path (SPICE/Verilog-A compact models) out of the transport layer, at M6+ — not blocking current milestones; (2) keep `device_geometry`/thermal-layer design explicit about *heterogeneous* multi-material stacks (Si logic + 2D-material layer + packaging), not just monolithic 2D-on-Si, matching DARPA/NAPMP's 3DHI framing — this is already implicit in the original three-phase architecture (M3D/CFET were named from the start) and just needs to stay explicit as transport/thermal backends get built.

## Data flow

```
MaterialRecord (materials/, per-field Citation)
        │
        ▼
   DFTResult (dft/, incl. TightBindingHandle for Kwant)
        │
        ▼
TransportResult (transport/ — Ion, Ioff, SS, mobility, Rc, power density)
        │
        ▼
  ThermalResult (thermal/ — junction temp, thermal resistance, optional stress)
        │
        ▼
   YieldResult (manufacturability/ — yield fraction, defect density, model used)
        │
        ▼
 PipelineResult (orchestration/ — aggregates all of the above + config)
        │
        ├──► validation/ (matches against cited real benchmarks, computes %-error, renders report)
        └──► orchestration/sweep.py + pareto.py (parameter sweeps, Pareto fronts, heterostructure search)
```

`orchestration.Pipeline.run()` wires all four solver stages via `RunConfig`/`StageConfig` — it never imports a concrete backend class, only `get_backend(name, **params)` factories. Swapping a stub for a real solver is a one-line config change.

## The stub/real seam

Each solver stage (`dft`, `transport`, `thermal`, `manufacturability`) exposes:

- A `Protocol` in `interfaces.py` (e.g. `DFTBackend`) defining the stage's contract.
- A `stub.py` implementation — physically-grounded where cheap (uses real `MaterialRecord` fields), not ab-initio/FEA-accurate.
- One or more real backends (`qe_wannier.py`, `devsim_backend.py`, `kwant_backend.py`, `fenicsx_backend.py`, `elmer_backend.py`, `hotspot_backend.py`, `poisson_murphy.py`, `monte_carlo.py`).
- A registry in `__init__.py`: `get_backend(name, **params) -> Backend`.

Every `Result` dataclass carries a shared `ProvenanceInfo`:

```python
@dataclass(frozen=True)
class ProvenanceInfo:
    backend_name: str
    is_stub: bool
    tool_version: str | None
    run_id: str
    timestamp: datetime
    git_commit: str | None
```

This is not optional plumbing — it's how the validation report can always state whether a number came from a stub or a real solver, per this repo's core rule (see `CLAUDE.md`).

## Data contracts

**Materials layer** (`materials/schema.py`):

```python
@dataclass(frozen=True)
class Citation:
    source: str                  # "JARVIS-DFT" | "C2DB" | "Materials Project" | named paper
    identifier: str               # JVASP-id, C2DB uid, MP-id, or DOI
    year: int | None
    figure_or_table_ref: str | None
    url: str | None

@dataclass(frozen=True)
class MaterialRecord:
    material_id: str
    formula: str
    lattice_constant_angstrom: float
    band_gap_eV: float
    effective_mass_electron: float    # units of m0
    effective_mass_hole: float
    dielectric_constant: float | None
    thermal_conductivity_W_mK: float | None
    work_function_eV: float | None
    citations: dict[str, Citation]    # per-field traceability
```

**DFT layer** (`dft/results.py`):

```python
@dataclass
class TightBindingHandle:
    format: str                   # "wannier90_hr" | "analytic_effective_mass"
    path: Path | None             # set only when format == "wannier90_hr"
    loader: Callable[[], Any]     # lazy: returns a Kwant-consumable Hamiltonian builder

@dataclass
class DFTResult:
    material_id: str
    band_gap_eV: float
    effective_mass_electron: float
    effective_mass_hole: float
    lattice_constant_angstrom: float
    tight_binding_hamiltonian: TightBindingHandle | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
```

**Transport layer** (`transport/results.py`):

```python
@dataclass
class TransportResult:
    device_geometry: "DeviceGeometry"
    ion_uA_per_um: float
    ioff_uA_per_um: float
    subthreshold_swing_mV_dec: float
    mobility_cm2_Vs: float
    contact_resistance_ohm_um: float
    power_density_W_per_um2: float
    iv_curve: list[tuple[float, float]]
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
```

**Thermal layer** (`thermal/results.py`):

```python
@dataclass
class FieldHandle:
    format: str                   # "xdmf_hdf5" | "lumped_scalar"
    path: Path | None
    loader: Callable[[], Any]

@dataclass
class ThermalResult:
    max_junction_temp_C: float
    thermal_resistance_K_per_W: float
    stress_MPa: float | None      # only mechanical-capable backends (Elmer) populate this
    field_handle: FieldHandle | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
```

**Manufacturability layer** (`manufacturability/results.py`):

```python
@dataclass
class YieldResult:
    yield_fraction: float
    defect_density_per_cm2: float
    critical_area_um2: float | None
    model: str                    # "poisson" | "murphy" | "monte_carlo"
    confidence_interval: tuple[float, float] | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
```

**Validation layer** (`validation/schema.py`) — the differentiator:

```python
@dataclass(frozen=True)
class Citation:
    authors: str
    year: int
    title: str
    venue: str
    doi: str | None
    figure_or_table_ref: str        # required, not optional
    url: str | None = None

@dataclass(frozen=True)
class ExperimentalValue:
    quantity: str                    # canonical name, e.g. "contact_resistance"
    value: float
    unit: str
    uncertainty: float | None
    conditions: dict[str, Any]       # e.g. {"material": "MoS2", "contact_metal": "Ni", ...}
    citation: Citation

@dataclass
class SimulatedValue:
    quantity: str
    value: float
    unit: str
    conditions: dict[str, Any]
    provenance: ProvenanceInfo

@dataclass
class BenchmarkEntry:
    id: str
    experimental: ExperimentalValue
    simulated: SimulatedValue | None  # None until a matching pipeline run exists

@dataclass
class AgreementResult:
    benchmark_id: str
    pct_error: float | None
    within_uncertainty: bool | None
    verdict: str                     # "excellent" | "reasonable" | "poor" | "not yet simulated"
```

`validation/registry.py` matches a `PipelineResult` to a `BenchmarkEntry` by `quantity` **and** `conditions` — not name alone, since the seeded benchmarks already include two variants of the same quantity (e.g. two different contact-resistance numbers under different contact conditions) that a naive name-only match would conflate.

## NGMM compatibility layer (`ngmm_compat/`)

Positioning for DARPA's NGMM Design Challenge Program (~Q1 FY27 — see `docs/NGMM_COMPATIBILITY.md` for full reasoning). Not verified against any real NGMM/TIE schema — every export carries `NGMM_SCHEMA_DISCLAIMER` verbatim.

**Materials-library export** (`materials_export.py`) — buildable and built now, since it only depends on the already-real `materials/` layer:

```python
@dataclass(frozen=True)
class NGMMPropertyValue:
    value: Any
    unit: str | None
    citation_source: str | None
    citation_identifier: str | None
    citation_verified: bool          # propagated from Citation.verified — never upgraded

@dataclass(frozen=True)
class NGMMMaterialLibraryEntry:
    name: str
    formula: str
    on_ngmm_supported_materials_list: bool   # computed, always present — currently False for every seeded material
    properties: dict[str, NGMMPropertyValue]
    extra: dict[str, Any]                     # includes packaging_compatibility
    schema_disclaimer: str = NGMM_SCHEMA_DISCLAIMER
```

**Packaging-compatibility placeholder** (`packaging_open_questions.py`) — whether a 2D-material logic die can be bonded into an NGMM-style mixed-material 3D stack is a genuinely unresolved *process* question, deliberately kept out of `materials/schema.py` and attached only at export time into `extra["packaging_compatibility"]`. `status` is restricted to non-affirmative values (`"unresolved_open_question"`) — mirrors this project's citation-completeness discipline applied to a process question instead of a measured constant.

**Chiplet-collateral export** (`chiplet_export.py`) — interface sketched only; real implementation is blocked on `orchestration.pipeline.PipelineResult`, which doesn't exist yet (M3). `CompactModelStub`'s placeholder file is named `compact_model.stub` (not `.sp`/`.va`) until M7 (SPICE/Verilog-A export) lands, so it can never be mistaken for an EDA-importable netlist prematurely.

## "Broad but shallow" Phase-1 scope

The four solver layers are not equally shallow in Phase 1 — some are genuinely cheap to make real immediately, others genuinely need a real device geometry to be worth setting up:

| Layer | Phase-1 content | Why |
|---|---|---|
| Materials | Real data from JARVIS-DFT/C2DB/Materials Project | It's a database, not a solver |
| DFT | Stub: parabolic effective-mass stand-in using real `MaterialRecord` fields | QE is genuinely heavy; no fab geometry yet to justify a real ab-initio run |
| Transport | Real (but simplified geometry): DEVSIM + Kwant | Both pip-installable, run in seconds, no HPC needed |
| Thermal | Real (but simplified): HotSpot compact model | Already the designated fast pre-filter; full 3D FEA needs a real geometry |
| Manufacturability | Real (but simplified): closed-form Poisson/Murphy | One-line formula; Monte Carlo needs layout detail that doesn't exist yet |

See `docs/ROADMAP.md` for the milestone sequence this maps to.

**Two distinct simplifications in the manufacturability layer, not one** (named
explicitly per the 2026-07-21 standards audit, `docs/STANDARDS_AUDIT.md`):
the "Monte Carlo needs layout detail" note above is about *defect placement*
(where defects land within a die); separately, `_critical_area_cm2()` in both
`manufacturability/stub.py` and `poisson_murphy.py` is a flat
`channel_width × channel_length × devices_per_die` formula, not real
**critical area analysis** — the actual EDA discipline (layout-geometry-
derived, accounting for feature spacing and redundancy sensitivity) that a
production yield model would use. Both are real, honestly-scoped Phase-1
simplifications; they're just two different missing disciplines, not one.
