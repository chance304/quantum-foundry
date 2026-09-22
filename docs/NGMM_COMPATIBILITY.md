# NGMM Compatibility

*Positioning notes for DARPA's Next-Generation Microelectronics Manufacturing (NGMM) program. This document is quantum-foundry's own reconstruction/reasoning from public sources — nothing here is confirmed by DARPA or TIE unless explicitly stated.*

---

## 1. Program background

Two real DARPA source documents were read directly (2026-07-20), both marked "Distribution Statement A: Approved for public release; distribution unlimited": the DARPA-SN-26-69 Shopping Notice, and an "NGMM Program Update and Accomplishments" deck (Michael Holmes, NGMM Managing Director).

**DARPA-SN-26-69** (a near-term "Shopping Notice," open 2026-04-16 to 2026-07-31) — **evaluated and declined as a target**. It asks for solutions that "exercise the early-stage version of the NGMM 3D Assembly Design Kit (3D-ADK)... with commercial EDA tools," i.e. teams test-driving DARPA's own immature toolkit, not submitting an independent simulator. Submission is a video uploaded via DARPAConnect's ERIS portal, titled `DARPA-SN-26-69: [Your Solution Title]`, plus a notification email — a different deliverable shape entirely from what this project builds. Its stated supported-materials list (Si, glass, GaN, InP, GaAs, SiC, ferrite, HgCdTe) includes zero 2D materials. Poor fit on timeline, format, and materials grounds.

**NGMM Design Challenge Program** — the real target. A formal, later program: external teams (1) design test structures/microsystems using the 3D-ADK, (2) fabricate baseline components; then TIE's NGMM Center (3) performs the actual 3D heterogeneous integration, (4) runs testing/reliability analysis, and (5) updates the models/ADK based on results. Per NGMM's own program-plan timeline, the **"Design Challenge Solicitation"** is expected at the Phase 1 → Phase 2 transition, around **Q1 FY27 (~January 2027)**. **This date is an estimate inferred from the phase-transition framing, not a published deadline** — re-verify periodically (tracked in `docs/ROADMAP.md`).

---

## 2. Our reconstruction of the 3D-ADK structure

**Caveat, stated plainly: quantum-foundry has not seen NGMM's real schema. This is our own reconstruction from a public architecture diagram, not verified documentation.**

TIE provides a "TNC Interface PDK" (design rule manual + material library) and a "TNC Assembly Design Kit" (assembly rules). Together these form the "3D-ADK" (3D reference flows + physical verification), consumed by a "Customer/External Designer" as "3D Microsystem Design" (chiplet collateral + top-level information), supported by a "Customer Engagement" process (IP management + technical support). This gives quantum-foundry two natural export targets — a **material library** and **chiplet collateral** — described in §5.

---

## 3. Exemplar microsystems and tier targeting

NGMM's roadmap is driven by three "exemplar" 3DHI microsystems, each a literal 3-tier stack, threaded together by "Edge Compute":

| Exemplar | Tiers | Sponsor(s) |
|---|---|---|
| RF Phased Array Radar | Antenna / PA / Beamformer | RTX, U.S. Air Force |
| Focal Plane Array (FPA) Imager | Detector / ROIC / Processor | U.S. Space Force |
| Compact Power Converter | Analog Passives / Power Switch / Control Logic | DARPA, U.S. Army |

**Recommendation (quantum-foundry's own framing, not DARPA/TIE-confirmed): target the FPA Imager's "Processor" tier**, not Compact Power Converter's "Control Logic":

- HgCdTe (the FPA's Detector-tier material, per NGMM's own supported-materials list) is thermally sensitive. An ultra-thin, low-power 2D-material logic tier gives a coherent "why thinness/power matters exactly here" story, and maps directly onto quantum-foundry's own planned `ThermalResult` (junction temp, thermal resistance).
- "Processor" sits most directly on NGMM's own "Edge Compute" thread connecting all three exemplars.
- Compact Power Converter's Control Logic tier pairs with a GaN power switch — 2D-material FETs haven't been demonstrated at those operating voltages/currents; a wider physics gap, not narrower.

Control Logic is logged here as a considered-and-deprioritized alternative, not deleted — cheap to keep documented, costly to lose the reasoning if silently dropped.

**This exemplar-tier choice is quantum-foundry's own speculative framing, not DARPA/TIE-confirmed. Don't present it as settled.**

---

## 4. OPEN QUESTION — NOT SOLVED: bonding/packaging compatibility

**Whether a 2D-material logic die can actually be Cu-Cu/hybrid-bonded or thermocompression-bonded into an NGMM-style mixed-material 3D stack is genuinely unresolved.** This is outside quantum-foundry's current device-level scope (DFT → transport → thermal → yield for a single device, not multi-die packaging/bonding physics). `ngmm_compat/packaging_open_questions.py` attaches an explicit "unresolved_open_question" flag to every material in the NGMM export — this is a flagged gap, not an assessed answer, and must never be upgraded to an affirmative compatibility claim without a real citation.

---

## 5. Export formats

### Materials library (`ngmm_compat/materials_export.py`) — buildable and built now

Reshapes `MaterialRecord` (materials/schema.py) into `NGMMMaterialLibraryEntry`/`NGMMMaterialLibrary`. Every property carries its source citation's `verified` flag forward — an export can never look more confident than its source. `on_ngmm_supported_materials_list` is computed and always present (currently `False` for every seeded material — the honest signal that this export is format-plumbing, not a materials-acceptance claim). Every entry/library carries `NGMM_SCHEMA_DISCLAIMER` verbatim (see `disclaimers.py`).

### Chiplet collateral (`ngmm_compat/chiplet_export.py`) — interface sketched, not yet implemented

Needs `orchestration.pipeline.PipelineResult`, which doesn't exist yet (milestone M3, not started). The interface (`ChipletManifest`, `CompactModelStub`, `ChipletCollateralBundle`) is sketched now for review; real implementation lands at milestone **M8**, once M3 exists. The compact-model file is deliberately named `compact_model.stub` (not `.sp`/`.va`) while `is_placeholder=True`, so it can never be mistaken for an EDA-importable netlist before milestone M7 (SPICE/Verilog-A export) actually lands.

---

## 6. Risks / open items

1. **Overclaiming schema compatibility** — an export could be misread as "NGMM-compatible" rather than "our own best-effort guess." Mitigated structurally (disclaimer travels with every serialized artifact) but a real presentation risk in any deck or proposal built from these exports.
2. **Materials-list mismatch** — none of quantum-foundry's seeded materials are on NGMM's own supported-materials list; `on_ngmm_supported_materials_list=False` must stay visible, never filtered out.
3. **Exemplar-tier choice and ~Q1 FY27 timing are both estimates**, not confirmed facts — must not be stated as settled.
4. **Bonding-compatibility gap is genuinely unresolved** (§4) — never silently upgraded to an affirmative claim.
5. **Chiplet-export scope-creep risk** — only the interface sketch lands before M3 stabilizes, to avoid rework (same "interface churn" risk already tracked generally in `docs/ROADMAP.md`).
