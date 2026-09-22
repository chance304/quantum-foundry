from quantum_foundry.materials.registry import MaterialsDB
from quantum_foundry.materials.schema import Citation, MaterialRecord
from quantum_foundry.ngmm_compat.materials_export import (
    export_material,
    export_material_library,
)


def test_no_seeded_material_is_on_ngmm_supported_list():
    """Honest signal: none of quantum-foundry's 2D TMDs/oxides are on NGMM's
    own stated supported-materials list — this must stay visible, never
    silently filtered out."""
    db = MaterialsDB()
    library = export_material_library(db)
    assert len(library.entries) >= 5
    for entry in library.entries:
        assert entry.on_ngmm_supported_materials_list is False


def test_citation_confidence_propagates_from_source_record():
    db = MaterialsDB()
    mos2_record = db.get("MoS2_monolayer")
    entry = export_material(mos2_record)

    band_gap_prop = entry.properties["band_gap_eV"]
    source_citation = mos2_record.citation_for("band_gap_eV")
    assert band_gap_prop.citation_verified == source_citation.verified
    assert band_gap_prop.citation_source == source_citation.source
    assert band_gap_prop.value == mos2_record.band_gap_eV
    assert band_gap_prop.unit == "eV"


def test_unverified_source_citation_stays_unverified_in_export():
    # Synthetic record, not seed data: this test is about export_material()'s
    # own verified-flag propagation, independent of which real seeded
    # material happens to carry an unverified citation right now. MoS2's
    # thermal_conductivity_W_mK was this test's probe field until 2026-08-04,
    # when the materials-provenance audit fetched and verified its real
    # source (see docs/DECISIONS.md) -- same "probe field gained real
    # sourcing, switch to synthetic data" pattern already hit once before by
    # test_none_fields_are_omitted_not_fabricated (MoTe2, 2026-07-28).
    unverified_record = MaterialRecord(
        material_id="synthetic_unverified",
        formula="XY2",
        thermal_conductivity_W_mK=1.0,
        citations={
            "thermal_conductivity_W_mK": Citation(
                source="synthetic test source",
                identifier="n/a",
                verified=False,
            )
        },
    )
    thermal_citation = unverified_record.citation_for("thermal_conductivity_W_mK")
    assert thermal_citation.verified is False

    entry = export_material(unverified_record)
    assert entry.properties["thermal_conductivity_W_mK"].citation_verified is False


def test_none_fields_are_omitted_not_fabricated():
    # Synthetic all-null record, not seed data: MoTe2 (this test's probe
    # material until 2026-07-28) gained real C2DB-sourced data that day --
    # see docs/DECISIONS.md. This test is about export_material()'s own
    # None-omission behavior, independent of which real materials happen
    # to be fully sourced right now.
    empty_record = MaterialRecord(material_id="synthetic_empty", formula="XY2")
    entry = export_material(empty_record)
    assert entry.properties == {}


def test_packaging_compatibility_is_never_affirmative():
    db = MaterialsDB()
    library = export_material_library(db)
    for entry in library.entries:
        note = entry.extra["packaging_compatibility"]
        assert note["status"] == "unresolved_open_question"
        assert note["verified"] is False


def test_schema_disclaimer_present_on_every_entry_and_library():
    db = MaterialsDB()
    library = export_material_library(db)
    assert library.schema_disclaimer
    assert library.materials_list_caveat
    for entry in library.entries:
        assert entry.schema_disclaimer == library.schema_disclaimer


def test_material_ids_filter():
    db = MaterialsDB()
    library = export_material_library(db, material_ids=["MoS2_monolayer", "HfO2"])
    assert {e.name for e in library.entries} == {"MoS2_monolayer", "HfO2"}
