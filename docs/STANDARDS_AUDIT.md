# Standards Audit — 2026-07-21

Repo-wide audit: what real external standards/methodologies each layer should
be judged against, where the current implementation falls short, and a
prioritized gap-filling backlog. Written ahead of bringing in
real textbooks/literature to anchor future work — this audit uses
best-current-knowledge domain references, explicitly confidence-flagged per
this project's own citation ethos (never present a claim as settled fact
without saying how sure we are). Items below marked **[LIT]** are exactly
the kind of thing the incoming literature should confirm, correct, or
supply a citation for — that's the intended handoff point.

## How to read this

- **Confidence**: high / medium / low — how sure the auditing pass is that
  the named standard/reference actually applies as described. Low-confidence
  physical claims (e.g. specific meV numbers) are flagged as indicative, not
  citation-grade, and should not be used in published material until a
  real source confirms them.
- **Tags** on each backlog item:
  - **[LIT]** — needs a real citation/paper/textbook value to close; exactly
    what incoming literature should target.
  - **[ENG]** — pure software-engineering fix, no domain literature needed.
  - **[DECISION]** — needs a scoping call (how much rigor is worth building
    now vs. later), not just a citation.
- **New vs. tracked**: whether this is a genuinely new finding from this
  audit, or a reframing/re-prioritization of something `docs/ROADMAP.md` already
  had.

---

## 1. Materials / DFT / Validation layer

**Standards referenced:**
- DFT methodology provenance (functional, k-mesh, SOC) as practiced by
  JARVIS-DFT/C2DB/Materials Project/AFLOW's own documentation — high
  confidence this is the right yardstick, since values aren't comparable
  across functionals (e.g. OptB88-vdW vs. HSE band gaps).
- FAIR data principles (Wilkinson et al. 2016, *Scientific Data*) — high
  confidence on the citation, medium on how strictly it should apply to a
  research-software repo vs. a published dataset.
- TMD valley/spin-orbit physics, Kormanyos et al.'s k·p review class (this
  lead is already named in `wse2_monolayer.yaml`'s own `open_items` — not
  introduced by this audit) — medium-high confidence on the physics
  (K-valley degeneracy, large SOC splitting in MoS2/WS2/WSe2), low
  confidence on exact meV magnitudes without a page-verified source.
- ASME V&V 10/20's verification-vs-validation distinction — high confidence
  this is the correct framework name; clause-level detail not verified.

**Findings (new unless marked tracked):**

1. `materials/schema.py`'s `Citation` has no field for which DFT functional
   produced a value (PBE/OptB88-vdW/HSE) — every seeded material mixes
   `band_gap_eV` (OptB88-vdW) with `extra.jarvis_extra_properties.hse_bandgap_eV`
   right next to it, with nothing structured linking a value to its method.
   High confidence.
2. No dataset-snapshot/access-date field on `Citation` — `year` captures
   publication year, not fetch date; if JARVIS-DFT's figshare snapshot
   revises, there's no way to detect staleness. High confidence gap exists;
   FAIR framing is this audit's own application.
3. The stub DFT's parabolic-band caveat is generic; nothing ties it to the
   fact that MoS2/WS2/WSe2 specifically have degenerate K-valleys and large
   K-point SOC splitting — i.e. the single-band model isn't just "less
   accurate" for these materials, it structurally can't represent the
   physics they were chosen for. Medium-high confidence on the physics, low
   on specific numbers — **[LIT]** candidate.
4. `validation/schema.py`'s `SimulatedValue` has no uncertainty/CI field
   (only `ExperimentalValue` does); nothing in `validation/` establishes
   solver convergence (verification) before comparing to experiment
   (validation) — conflates the two per ASME V&V 10/20. High confidence.
5. **[Tracked, reframed]** WS2's anomalous 612.59 m0 electron mass
   (`docs/ROADMAP.md` line ~37) may be a parabolic-fit artifact near a
   non-parabolic/multi-valley band, not purely a database sourcing error —
   a C2DB cross-check alone may not resolve it; may need a real k·p or GW
   comparison. Medium confidence.
6. **[Tracked, confirmed accurate]** 4-of-6 validation benchmarks with no
   confirmed source paper, and the 10%/30% verdict thresholds' own
   in-code "arbitrary" caveat — both already honestly flagged, not
   re-reported as new.

---

## 2. Device Transport & Thermal/Mechanical layer

**Standards referenced:**
- Sze & Ng, *Physics of Semiconductor Devices*; Selberherr, *Analysis and
  Simulation of Semiconductor Devices* — drift-diffusion/Poisson
  self-consistency, explicit mobility models. High confidence.
- Kaasbjerg et al.'s phonon-limited mobility calculations for MoS2 — correct
  2D-TMD mobility reference class. High confidence.
- Datta, *Quantum Transport: Atom to Transistor* / *Electronic Transport in
  Mesoscopic Systems* — NEGF/Landauer-Büttiker standard. High confidence.
- Skadron et al. (ISCA 2003) + HotSpot 3.0/6.0 technical reports — defines
  HotSpot's intended chip-level grid-model envelope. High confidence
  (already cross-checked against real HotSpot source/examples this session).
- ASME V&V 10 / Zienkiewicz-class FEA texts — mesh convergence, BC
  sensitivity, reference-case validation. High confidence as the right
  yardstick for the M5 plan.
- Eric Pop group / TDTR-Raman thermometry as the source class for MoS2/SiO2
  Kapitza resistance — medium confidence only; no specific paper verified.
  `docs/M5_PLAN.md` correctly defers this to a real citation rather than
  inventing one — already good practice, not a gap.

**Findings (new unless marked tracked):**

1. `devsim_backend.py`'s design names no mobility model at all for the
   eventual `_setup_drift_diffusion()` implementation — undecided between a
   bulk model (Caughey-Thomas) and a 2D-specific phonon-limited model
   (Kaasbjerg-class), and no quantum-correction (density-gradient) term is
   discussed for a 0.65nm monolayer channel, where bulk DD assumptions
   themselves are questionable. High confidence this is a real, currently
   open decision. **[LIT] + [DECISION]**.
2. `kwant_backend.py`'s leads are literal periodic copies of the channel
   lattice — effectively a wide-band-limit-adjacent contact choice made by
   construction, never stated as a deliberate physics assumption vs. real
   self-consistent contact self-energies. High confidence. **[ENG]** (just
   needs the assumption named in `extra`/docstring).
3. `hotspot_backend.py` has no interfacial (Kapitza) thermal resistance term
   at all — `.lcf`'s `resistivity` is bulk-only, and unlike the
   already-flagged generic-specific-heat gap, this omission isn't flagged
   in `extra` anywhere. For a 2D-material device, interface resistance is
   frequently the *dominant* thermal-resistance term, not a second-order
   correction — every HotSpot Tj today is a likely underestimate. High
   confidence the gap exists; medium on magnitude without a citation.
   **[LIT] for the real value, [ENG] for flagging its absence now.**
4. `docs/M5_PLAN.md` plans FEniCSx-vs-Elmer cross-validation (a legitimate
   code-to-code V&V technique) but has no mesh-convergence study or
   analytical/experimental reference-case step — ASME V&V 10 needs both,
   not just cross-solver agreement. High confidence. **[DECISION]** (add a
   convergence-study deliverable to the M5 plan before implementation).
5. **[Tracked, re-prioritize upward]** `thermal/stub.py`'s absolute-Tj
   scale-mismatch bug (`docs/ROADMAP.md` ~line 46) — M6's heterostructure search
   is now consuming these physically-absurd numbers as a live ordinal
   signal in reported candidate comparisons, so this is no longer a
   latent flaw, it's actively touching decision output.

**Judgment call on HotSpot's operating envelope:** even after
`_pad_to_die_footprint()`, HotSpot is being used correctly *only* within the
architecture's own declared "fast compact-model pre-filter" role — a
coarse, relative signal. It cannot become a source of validation-grade
absolute accuracy on its own (no Kapitza term, generic specific-heat
default, was numerically pathological at real device scale until padded).
This matches what the architecture already says HotSpot is for; no misuse
found beyond that already-acknowledged boundary. Closing gap #3 above
doesn't change this — real nm-scale interface-dominated thermal accuracy is
still M5's job, not HotSpot's.

---

## 3. Manufacturability / Yield layer

**Standards referenced:**
- Poisson yield model; Murphy's yield integral (B.T. Murphy, *Cost-Size
  Optima of Monolithic Integrated Circuits*, Proc. IEEE, 1964) — high
  confidence, and the implemented formulas were checked against the real
  textbook forms: they match exactly (`Y=exp(-D0·A)`,
  `Y=((1-exp(-D0·A))/(D0·A))²`), no math bug found.
- Negative-binomial yield model (C.H. Stapper, *Modeling of Defects in
  Integrated Circuit Photolithographic Patterns*, IBM J. Res. Dev., 1984) —
  high confidence this is the standard "more realistic than Poisson/Murphy"
  model real fabs use, via a clustering parameter α.
- Critical-area analysis as a distinct EDA discipline (layout-geometry-
  derived, not a flat area formula) — high confidence this is the correct
  name for what's currently simplified away.

**Findings:**

1. **New.** No negative-binomial/clustering model exists anywhere in the
   codebase or is mentioned in `docs/ROADMAP.md`/`docs/DECISIONS.md` (confirmed
   via grep — zero hits for "Stapper," "negative binomial," "clustering").
   Poisson/Murphy assume uniform or one fixed clustering shape; real fabs
   use NB precisely because that assumption is usually wrong. High
   confidence this is a real, unacknowledged gap. **[LIT] + [DECISION]**.
2. **New, confirmed by direct read.** `poisson_murphy.py`'s `_require_d0`
   error message says "see docs/ROADMAP.md's D0-sourcing open item" — **no such
   item exists in `docs/ROADMAP.md`** (confirmed via grep, zero hits for "D0").
   Dangling cross-reference. High confidence. **[ENG]**, trivial fix.
   Separately: whether a real citable D0 for CVD-grown 2D-TMD film
   manufacturing even exists in the literature is a genuinely open question
   — not asserting one exists, this is exactly a **[LIT]** target.
3. **Already disclosed, reframe terminology.** `_critical_area_cm2` in both
   `stub.py` and `poisson_murphy.py` is a flat
   `channel_width × channel_length × devices_per_die`, not real
   layout-derived critical-area analysis. `docs/ARCHITECTURE.md` already
   discloses this as a simplification, but frames the fix as "needs Monte
   Carlo / layout detail" rather than naming "critical area analysis" as
   the specific missing EDA discipline. Medium confidence this framing gap
   matters enough to fix. **[ENG]**.

---

## 4. Software Engineering Practices (repo-wide)

**Findings (all new, all high confidence — directly verified this pass):**

1. No lint/type-check tooling anywhere — no ruff/flake8/black/mypy/pyright
   config, no `.pre-commit-config.yaml`. Type hints ARE used consistently
   across spot-checked modules (`provenance.py`, `dft/stub.py`,
   `transport/stub.py`, `thermal/stub.py`, `materials/schema.py`,
   `orchestration/pipeline.py`) — good discipline, just unenforced by
   tooling. **[ENG]**.
2. `pytest-cov` is a listed dev dependency but never actually invoked with
   `--cov` anywhere (`ci.yml` runs bare `pytest`) — installed and unused,
   no coverage threshold enforced. **[ENG]**.
3. Dependency pinning is loose everywhere: `pyproject.toml` uses `>=` only,
   `environment.yml` has zero version pins. `conda-lock.yml`'s absence was
   already tracked. **[ENG]**.
4. **Confirmed stale.** `README.md`'s Status section still says "Kickoff
   only — stack decided, no pipeline code yet," despite M0–M6/M6a being
   real and complete per `docs/ROADMAP.md`. Directly verified by reading both
   files side by side. **[ENG]**, trivial fix.
5. Error-handling / "refuse loudly, never fabricate" consistency check: one
   real inconsistency found — `manufacturability/stub.py` defaults
   `defect_density_per_cm2` to an arbitrary uncited `1.0` with **no flag at
   all** in its output `extra`, unlike `thermal/stub.py`'s
   `fallback_conductivity_used_for` pattern for its own analogous fallback.
   This is the project's own core ethos applied inconsistently. **[ENG]**.
6. `scripts/setup_github_runner.sh` checked against its own stated
   guidance (no hardcoded tokens, explicit warning comment) — passes, no
   issue found.
7. No `CHANGELOG.md`; `pyproject.toml`'s version (0.1.0) has never been
   bumped despite multiple real milestones landing. **[ENG]**.

---

## Consolidated Gap-Filling Backlog (prioritized)

**Tier 1 — quick, no literature needed, do anytime. DONE 2026-07-21 (see
`CHANGELOG.md` [0.2.0] and `docs/DECISIONS.md`'s matching entry):**
- [x] [ENG] Fix `poisson_murphy.py`'s dangling "see docs/ROADMAP.md's D0-sourcing
      open item" reference — added the real item to `docs/ROADMAP.md`, reworded
      the error message to point at it by name.
- [x] [ENG] Rewrite `README.md`'s Status section (stale since M0).
- [x] [ENG] Flag `manufacturability/stub.py`'s uncited `1.0` D0 default in
      its `extra` dict (`defect_density_defaulted_uncited`), matching
      `thermal/stub.py`'s fallback-flagging pattern.
- [x] [ENG] Name the `kwant_backend.py` lead model explicitly as
      "ideal semi-infinite same-material contacts (WBL-equivalent)" in its
      docstring and `extra["contact_model"]`.
- [x] [ENG] Flag Kapitza resistance's absence in `hotspot_backend.py` via
      `extra["kapitza_resistance_included"] = False`.
- [x] [ENG] Reframe the critical-area simplification in
      `docs/ARCHITECTURE.md` to name "critical area analysis" as the
      specific missing EDA discipline, distinct from the Monte Carlo defect-
      placement deferral.
- [x] [ENG] Add ruff + mypy config, wire into `ci.yml`'s lightweight job.
      (mypy required 6 small real fixes to actually pass clean — see
      `docs/DECISIONS.md`.)
- [x] [ENG] Add `--cov=quantum_foundry --cov-fail-under=70` to CI (70% is
      the real measured coverage of the lightweight job's test selection,
      not an arbitrary number).
- [x] [ENG] Add upper-bound version pins to `pyproject.toml` as an interim
      measure before `conda-lock.yml` exists (already tracked separately).
- [x] [ENG] Add `CHANGELOG.md`; bump version at each future milestone
      (0.1.0 → 0.2.0 this pass).

**Tier 2 — needs a scoping decision, not just a citation:**
- [ ] [DECISION] Pick and document `devsim_backend.py`'s eventual mobility
      model (2D phonon-limited vs. bulk) and whether a quantum-correction
      term is in scope for the first implementation.
- [ ] [DECISION] Add an explicit mesh-convergence-study deliverable to
      `docs/M5_PLAN.md` (e.g. 3 refinement levels, % change in
      `max_junction_temp_C` reported) before implementation starts.
- [ ] [DECISION] Decide whether a negative-binomial (Stapper 1984) yield
      model is worth adding alongside Poisson/Murphy, and if so scope it.
- [ ] [DECISION] Add `uncertainty`/`confidence_interval` to
      `validation/schema.py`'s `SimulatedValue`; define what "verified"
      (solver convergence) means before a validation comparison is trusted,
      per the ASME V&V 10/20 verification-vs-validation split.

**Tier 3 — genuinely blocked on real literature (the incoming textbooks
should target these first):**
- [ ] [LIT] Add `functional`/`soc_included` fields to `Citation`; backfill
      for all 10 seeded materials from each source's own stated methodology.
- [ ] [LIT] Add `dataset_snapshot_id`/`accessed_date` fields to `Citation`;
      backfill from existing fetch-date knowledge already in source-module
      docstrings/comments.
- [ ] [LIT] Get a page-verified citation (Kormanyos et al. or equivalent)
      for MoS2/WS2/WSe2 K-valley degeneracy and SOC splitting magnitudes;
      use it to quantify (not just qualitatively flag) how badly the
      single-band parabolic stub biases results for these specific
      materials.
- [ ] [LIT] Cross-check WS2's anomalous 612.59 m0 electron mass against a
      real k·p or GW source, not just another database lookup — it may be
      a physical (non-parabolic-band) artifact rather than a sourcing gap.
- [ ] [LIT] Source a real Kapitza (interfacial) thermal resistance value
      for MoS2/SiO2 (or the nearest available 2D-material/oxide interface)
      before M5 implementation.
- [ ] [LIT] Source real CTE (thermal expansion) values for MoS2/SiO2/Si
      for M5's stress calculation.
- [ ] [LIT] Determine whether a real, citable defect density (D0) exists
      anywhere in the literature for CVD-grown 2D-TMD films specifically —
      genuinely underexplored; may end up documented as "no known source,"
      not necessarily found.

---

*This audit's own confidence flags apply recursively: treat every "high
confidence" claim above as a strong recommendation, not a citation in
itself — Tier 3 items exist precisely because a real paper/textbook hasn't
verified them yet.*

---

# Audit Update — 2026-07-27

Second pass, covering everything built since 2026-07-21 that the first
audit couldn't have seen: M6 (heterostructure/Pareto search), M6a/M7/M8
(NGMM materials/chiplet export, Verilog-A export), the architecture-audit
roadmap's 8 items (V_th/DIBL extraction, BEOL/M3D gates, Monte Carlo yield,
Matthiessen's-rule mobility, PPA-Y report, TLM/van der Pauw), and M9
(CFET/GAA/M3D multi-tier device physics). Same confidence/tag conventions
as above.

## 5. Heterostructure search, exports, and the architecture-audit roadmap (M6-M8)

**Standards referenced:**
- Multi-objective Pareto-front optimization as the standard technique for
  PPA-class trade-off analysis (no single winner when objectives conflict)
  — high confidence this is the right framework; `pareto.py`/`report.py`
  already implement and render it correctly, no gap found.
- IEEE 1364.1 (Verilog-AMS/Verilog-A language standard) — high confidence
  this is the right yardstick for `verilog_a_export.py`'s syntax.
- Basic two-terminal-device compact-model correctness: I(V_ds=0)=0 (no
  driven current with zero potential difference) and correct sign behavior
  under V_ds reversal — high confidence this is a real, textbook-level
  requirement (Sze & Ng; also a standard SPICE DC-convergence concern —
  a voltage-independent current source has zero output conductance
  everywhere, a known non-convergence risk), not a project-specific
  invention.
- van der Pauw (1958) and standard TLM linear-regression extraction — high
  confidence; `validation/pcm_structures.py` was checked directly against
  the real transcendental equation and citation, both correct, no gap
  found.
- Gross-dies-per-wafer (GDW) yield-engineering estimation with edge-loss
  correction — medium-high confidence this is a real, standard fab
  estimation formula (`manufacturability/monte_carlo.py`'s
  `dies_per_wafer()`), not exactly page-verified against one named
  textbook this pass.

**Findings:**

1. **New, high confidence, FIXED this pass.** `transport/verilog_a_export.py`'s
   generated Verilog-A made `I(d,s)` a function of `V(g,s)` alone, with
   **no `V(d,s)` dependence at all** — the model would output a fixed
   nonzero drain current even at V_ds=0V, violating the basic requirement
   above and creating a real SPICE DC-convergence risk if the file were
   ever dropped into an actual simulator. Fixed by scaling the looked-up
   current by `tanh(V(d,s)/VDS_SAFETY_V)`, a numerical-safety smoothing
   factor (not a new physical/fitted parameter, and negligible at every
   real bias point this project's backends use — see the module's own
   docstring for the derivation). Verified via two new tests
   (`test_export_verilog_a_scales_current_by_vds_not_independent_of_it`,
   `test_vds_safety_smoothing_is_zero_at_origin_and_negligible_at_real_bias_points`).
   Still deliberately not a triode-region physical model — that would
   need a `Vdsat` this project doesn't have, and would re-open the
   "fitting against under-resolved data" problem the module's own original
   scope decision already rejected.
2. **New, validated (no fix needed).** Checked M9's decision (see below)
   not to invent a GAA "gate coupling strength" multiplier against real
   literature: GAA-vs-planar/FinFET SS/DIBL improvements are real and
   directionally well-established (circumferential gate control), but
   specific numbers vary substantially by paper, node, and geometry (no
   single universal citable body-factor constant found) — **confirms**
   the decision to flag `gate_type_physics_modeled=False` honestly rather
   than fabricate a number was correct, not a gap.
3. **New, informational.** `manufacturability/monte_carlo.py`'s
   `dies_per_wafer()` formula was independently re-derived and confirmed
   to match the real, standard GDW-with-edge-loss shape
   (`pi*R^2/A - pi*(2R)/sqrt(2*A)`) — correct math, just not previously
   named as a known formula class in the docstring. Citation-naming note
   added (medium-high confidence on the reference class, not one exact
   textbook page).
4. **Re-checked, no new gap.** `ngmm_compat/{materials_export,
   packaging_open_questions,chiplet_export,disclaimers}.py` and
   `orchestration/report.py` re-read against the NGMM disclaimer
   discipline and Markdown-report conventions already established — both
   solid, citation/disclaimer handling consistent, nothing new found.
5. **Re-checked, no new gap.** `transport/extraction.py` (constant-current
   V_th, log-space interpolation, DIBL formula) independently re-derived
   against Sze & Ng's standard definitions — both match exactly.

---

## 6. M9 — Multi-tier/multi-gate device physics (CFET/GAA/M3D)

**Standards referenced:**
- CEA-Leti's sequential-3D-integration body of work (P. Batude et al.,
  CoolCube(TM) program) as the real reference class for BEOL's 400-450C
  copper/low-k thermal-budget ceiling — medium-high confidence on the
  reference class, not one clause.
- Xie, Jia, Nie et al., "Monolithic 3D integration of 2D transistors and
  vertical RRAMs in 1T-4R structure for high-density memory," *Nature
  Communications* 14, 5952 (2023), doi:10.1038/s41467-023-41736-2 — high
  confidence, directly verified (full text read via PMC, not a search
  summary) as a real, MoS2-specific M3D thermal-budget precedent.
- Zheng, McClellan, Pop & Koh, "Non-equilibrium Phonon Thermal Resistance
  at MoS2/Oxide and Graphene/Oxide Interfaces," *ACS Appl. Mater.
  Interfaces* 2022 (arXiv:2204.06975) — high confidence, directly verified
  (arXiv PDF text extracted via `pypdf` after WebFetch's own summarizer
  failed on the binary stream) as the source for M9b's Kapitza-resistance
  candidate value.

**Findings:**

1. **New, high confidence, FIXED this pass.** `thermal/beol_budget.py`'s
   `M3D_LAYER_TRANSFER_MAX_TEMP_C = 300.0` upgraded from "widely-cited
   industry figure, not clause-cited" (2026-07-21 audit's own honest
   flag) to a real, specific, directly-verified citation: Xie et al. 2023
   states "the highest temperature among all the processes being the
   PECVD isolation oxide growth at 300C" for a monolithic 3D stack of
   **MoS2** transistors and HfOx VRRAMs — a materially-relevant precedent
   given this project's own MoS2-anchored device thesis, not just an
   analogous industry number. `BEOL_MAX_TEMP_C = 400.0` similarly upgraded
   to name CEA-Leti/Batude's CoolCube(TM) research body as the real
   reference class, though no single clause was pinned down this pass.
2. **Tracked, partially resolved this pass (see `docs/DECISIONS.md`
   2026-07-27).** M9b's `kapitza_resistance_m2K_per_W` requirement — a
   real candidate value (R_eqm(MoS2/SiO2, 300K) ~= 3.9e-8 m^2*K/W) was
   found and directly verified from Zheng et al. 2022, closing this
   audit's own Tier 3 item ("Source a real Kapitza (interfacial) thermal
   resistance value for MoS2/SiO2 ... before M5 implementation") for the
   *substrate*-interface case, and reused as the best-available analog for
   M9's *inter-tier bonding* interface case. Still flagged as an analog,
   not a direct measurement of an actual wafer-bonded interface — no such
   paper was found. Not hardcoded as a default anywhere.
3. **Re-checked, no new gap.** `orchestration/pipeline.py`'s per-tier
   orchestration (M9a) and `thermal/hotspot_backend.py`'s multi-tier
   compact model (M9b) re-read against this audit's own standards
   (never-fabricate-a-constant, refuse-loudly-not-silently-default,
   flag-every-simplification) — both hold up; the real bug M9b's own
   build already found and fixed (one tier's power silently applied to
   every channel-role layer) was exactly this kind of gap, already closed
   before this audit pass started.

---

## Consolidated Gap-Filling Backlog — 2026-07-27 addendum

**Tier 1 — quick, no literature needed. DONE this pass:**
- [x] [ENG] Fix `verilog_a_export.py`'s missing V(d,s) dependence
      (tanh-based numerical-safety smoothing, not a new physical param).
- [x] [LIT] Upgrade `M3D_LAYER_TRANSFER_MAX_TEMP_C`'s citation to Xie et
      al. 2023 (real, MoS2-specific, directly verified).
- [x] [LIT] Upgrade `BEOL_MAX_TEMP_C`'s citation to name CEA-Leti/Batude's
      CoolCube(TM) research body as the real reference class.
- [x] [ENG] Name `dies_per_wafer()`'s formula as a real, standard GDW
      estimation shape in its docstring.
- [x] [LIT] Source and cite a real inter-tier Kapitza-resistance candidate
      value for M9b (Zheng et al. 2022) — see `docs/ROADMAP.md`/`docs/M9_PLAN.md`.

**Tier 2 — no new items this pass** (M9's own scoping already produced its
own Tier-2-equivalent sub-tasks, M9d/M9e, tracked in `docs/ROADMAP.md`).

**Tier 3 — still genuinely open (carried forward, unchanged unless noted):**
- Everything in the 2026-07-21 audit's own Tier 3 list, **except** the
  Kapitza-resistance item, now partially resolved (see Finding 2 above) —
  still needs a real measurement of an actual inter-tier *bonding*
  interface specifically, not just the MoS2/SiO2 substrate analog.
- [ ] [LIT] Pin down one exact clause/page citation for `BEOL_MAX_TEMP_C`
      (400C) if this project ever needs to defend it against a specific
      fab's own qualified spec, rather than the CoolCube(TM) reference
      class named above.
- [ ] [LIT] The same Zheng et al. 2022 paper reports HfO2/Al2O3 interface
      data (Fig. 2b/3b) alongside the MoS2/SiO2 value M9b now cites, but
      those numbers live only in plotted figure pixels, not machine-
      extractable PDF text — a real, bounded follow-up if this project's
      interlayer dielectric choice ever needs to be HfO2-specific.

---

*Same recursive caveat as the 2026-07-21 audit: every "high confidence"
claim above is a strong recommendation, not a citation in itself.*

---

# Audit Update — 2026-08-04 (Documentation & Reproducibility)

Third pass, scoped specifically to docs/reproducibility standards (FAIR4RS
for research software, standard OSS-style repo-hygiene and literal "can a new engineer get this
running" reproducibility testing) — not materials data, CI/lint tooling
config, or solver-physics code. Every finding below was directly
reproduced (real `pip install -e .`, real `pytest` runs, real `gh api`/`gh
run view` calls against this repo's actual GitHub state), not assumed from
reading docs.

## 7. Documentation & Reproducibility

**Standards referenced:**
- FAIR4RS Principles (Chue Hong et al. 2022, "FAIR Principles for Research
  Software") — Findable/Accessible/Interoperable/Reusable, applied to an
  open-source research-software repo.
  High confidence this is the right yardstick, medium on how strictly the
  "Findable" axis applies outside a public registry.
- Standard OSS repo-hygiene checklist (README with real setup/usage,
  CONTRIBUTING/onboarding doc, LICENSE or explicit ownership statement,
  accurate status claims) — high confidence as the right shape.
- This project's own established discipline (see Sections 1-6 above,
  `docs/DECISIONS.md`'s audit-pass entries): verify a claim by actually
  running/reading it, never by trusting a prior write-up or search
  summary. Applied here to the write-ups themselves, not just physics
  claims.

**Findings (new, all directly verified this pass):**

1. **Confirmed and fixed.** `README.md` had no Setup/Installation section
   at all — a new engineer reading it top to bottom got project
   description, competitive context, architecture, and status, but zero
   instructions for actually getting the code running. Reproduced the gap
   directly: followed the repo as a first-time contributor would, hit the
   documented Python-version wall (sandbox default `python3` is 3.10,
   `pyproject.toml` requires >=3.11), worked around it with `uv venv
   --python 3.11` against an already-cached 3.11.15 interpreter (no
   network download needed — better than the 3.14-workaround path
   `docs/DECISIONS.md`'s 2026-08-03 entry describes needing, since 3.11 is
   now genuinely cached), then `pip install -e ".[dev]"` and `pytest -m
   "not requires_real_solver"` — both worked cleanly with zero code
   changes needed. **Fixed**: added a real Setup section to `README.md`
   with the exact working commands for both the stub-only path (plain
   venv, no conda) and the real-backend path (`scripts/setup_env.sh`,
   conda-based), matching what this pass and prior sessions actually
   verified works. **[ENG]**.
2. **Confirmed and fixed.** No `CONTRIBUTING.md` or equivalent onboarding
   doc existed. The stub/real backend architecture pattern (`Protocol` in
   `interfaces.py` + `stub.py` + real backend(s) + `get_backend()`
   registry in `__init__.py`) *is* well documented at the design level in
   `docs/ARCHITECTURE.md`'s "The stub/real seam" — that part was already
   good, not a gap. What was missing was a contributor-facing entry point:
   dev-environment setup order, testing workflow (`requires_real_solver`
   marker), how to actually add a new backend, and where to log work
   (`docs/DECISIONS.md`). **Fixed**: added
   `CONTRIBUTING.md`, written from the actual code structure (verified
   against `transport/__init__.py`'s real `_BACKENDS` registry pattern),
   not invented. **[ENG]**.
3. **Confirmed, real gap, partially fixed.** Module-level docstrings are
   consistently rich across this codebase (spot-checked and repo-wide
   `ast`-scanned) — but a full-repo AST scan found only 14/58 modules
   missing a module docstring (mostly `__init__.py`/`interfaces.py` files)
   while **64 of 90 (71%) public functions/methods have no docstring at
   all**, including every `run()` method on every backend class and —
   notably — all four `interfaces.py` Protocol files, which are the exact
   place a new contributor most needs to find `is_stub` semantics, units,
   and inputs/outputs documented, per this project's own transparency
   ethos (`CLAUDE.md`: "the validation report must always show whether a
   number came from a stub or a real backend"). That transparency
   currently lives in runtime `ProvenanceInfo` dataclasses and module
   docstrings, but not consistently in function-level docstrings. **Fixed
   for the 4 `interfaces.py` files** (the core stage contracts —
   `dft/interfaces.py`, `transport/interfaces.py`, `thermal/
   interfaces.py`, `manufacturability/interfaces.py`): added real
   docstrings (verified against each stage's actual `results.py` field
   units and each real backend's actual behavior) documenting `is_stub`
   semantics and `run()`'s inputs/outputs/units. **The remaining ~85%
   is real, honestly-scoped remaining work — not attempted here** (would
   mean touching physics-solver code across every stage, out of this
   pass's scope; see backlog below). **[ENG]**, partially done.
4. **Confirmed, currently live, high severity.** README's Status section
   claimed "Lightweight CI (GitHub-hosted) is green." **This is currently
   false on `main`.** Verified directly via `gh run view` against all
   three most-recent CI runs on `main` (the merge commits for PRs #1, #2,
   #3, current HEAD `4eec6bb`): the `lightweight` job fails at its `ruff
   check src/ tests/` step every time, and reproduced identically in a
   fresh local install (`ruff==0.16.1`, pinned range `>=0.6,<1` per
   `pyproject.toml`): **34 errors** (mostly `I001` import-sort, plus
   `RUF022`/`UP035`/`UP017`/`RUF100`/`RUF007`/`C408`/`PLW1510`/`BLE001`/
   `ISC004`). **Root cause identified, not just the symptom**:
   `pyproject.toml`'s `[tool.ruff]` section has no `select = [...]` at
   all — just a comment claiming "Ruff's own default rule set (E4/E7/E9/F
   ... )". `ruff check --show-settings` against the actual pinned version
   shows the real resolved default is far broader than that comment
   describes (includes `YTT`/`ASYNC`/`S`/`B`/`BLE`/`RUF`/`UP`/`I`/`C4`/
   `ISC`/`PLW` categories, not just `E4`/`E7`/`E9`/`F`) — the comment was
   accurate against whatever ruff version/defaults were current on
   2026-07-21 (`docs/DECISIONS.md` records this as passing clean then) but
   has drifted out of sync with the pinned version's actual behavior
   since. This means "green CI" silently broke at some point after
   2026-07-21 with no docs update reflecting it — exactly the kind of
   claim-vs-reality drift this project's own audit discipline exists to
   catch. **Fixed the doc claim** (`README.md`'s Status section now says
   "currently red," points here). **Did not touch the ruff
   config/behavior itself** — that's a lint-tooling fix, explicitly out of
   this pass's scope, and the actual fix (either pin an explicit `select`
   matching the original E4/E7/E9/F intent, or accept the broader rule set
   and run `ruff check --fix`) is a real scoping decision, not a
   find-and-replace. **[ENG]**, fix identified, not applied — see backlog.
5. **Re-verified, still accurate.** `docs/ROADMAP.md`'s M11 entry claims
   `tests/thermal/test_mesh_generation.py` — "4 tests, all passing"
   against a real `gmsh`-nox-installed environment. Independently
   reproduced from a clean `.venv` (Python 3.11.15, not the 3.14 the
   original session needed): installed gmsh via the documented `pip
   install -i https://gmsh.info/python-packages-dev-nox --pre "gmsh>=4.12,<5"`
   command plus `meshio`/`h5py`, ran the test file directly — **4 passed**,
   confirmed. Without gmsh installed, the same 3 (of 4) gmsh-dependent
   tests fail loudly with `ModuleNotFoundError`, not silently — consistent
   with the `requires_real_solver` marker correctly excluding them from
   lightweight CI. No drift found here.
6. **Resolved (license).** GitHub's API reported `"license": null` for
   this repo because no top-level `LICENSE` file existed. **Fixed**: the
   project is released under Apache-2.0 with `LICENSE`, `NOTICE` and
   `THIRD_PARTY_LICENSES.md` at the repo root, and `pyproject.toml` declares
   the SPDX license expression.

---

## Consolidated Gap-Filling Backlog — 2026-08-04 addendum (docs & reproducibility)

**Tier 1 — quick, no literature/decision needed. DONE this pass:**
- [x] [ENG] Add a real, verified Setup section to `README.md` (stub-only
      plain-venv path + real-backend conda path).
- [x] [ENG] Correct README's Status section: CI is currently red, not
      green (with root cause and pointer to this section).
- [x] [ENG] Add `CONTRIBUTING.md` (stub/real backend pattern for a new
      contributor, dev workflow, testing, logging conventions).
- [x] [ENG] Add real docstrings to all 4 `interfaces.py` Protocol files
      (the core stage contracts) — `is_stub` semantics, `run()` inputs/
      outputs/units.
- [x] [ENG] Re-verify docs/ROADMAP.md's M11 "4 passing mesh-gen tests" claim —
      confirmed still accurate, independently reproduced.

**Tier 2 — needs a scoping decision, not just a fix:**
- [ ] [DECISION] Fix `ruff check`'s 34 current failures on `main`. Two
      real options, a real choice: (a) pin `[tool.ruff]`'s `select` to the
      originally-intended `["E4", "E7", "E9", "F"]` (matches the existing
      comment's stated intent, smallest behavior change), or (b) accept
      the broader resolved-default rule set and run `ruff check --fix`
      (29/34 auto-fixable) plus manually resolve the remaining ~5. Either
      way, update the `[tool.ruff]` comment to describe what's actually
      configured, not a stale claim. Deliberately not done in this pass
      (lint-tooling change, out of scope for a docs/reproducibility audit;
      also touches ~15 source/test files that another concurrent audit
      pass may also be touching).
- [x] ~~[DECISION] License~~ — resolved: Apache-2.0 (see Finding 6 above).

**Tier 3 — genuinely large, not attempted this pass:**
- [ ] [ENG] Extend docstring coverage from the 4 `interfaces.py` files to
      the ~60 remaining public functions/methods without one (`stub.py`/
      real-backend `run()` methods, `orchestration/pipeline.py`'s
      `Pipeline.run()`, `materials/registry.py`'s `MaterialsDB`, etc.) —
      real, bounded, mechanical work, just large enough to warrant its own
      pass rather than being folded into this one.

---

*Same recursive caveat as every prior pass: every "high confidence" claim
above is a strong recommendation, not a citation in itself — and every
"confirmed" finding above was independently reproduced this pass, not
inferred from reading other docs.*
