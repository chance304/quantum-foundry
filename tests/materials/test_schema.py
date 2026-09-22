import dataclasses

from quantum_foundry.materials.schema import Citation, MaterialRecord


def test_material_record_minimal_construction():
    record = MaterialRecord(material_id="Test_material", formula="TeMa")
    assert record.material_id == "Test_material"
    assert record.lattice_constant_angstrom is None
    assert record.citations == {}
    assert record.extra == {}


def test_citation_for_returns_none_when_missing():
    record = MaterialRecord(material_id="Test_material", formula="TeMa")
    assert record.citation_for("band_gap_eV") is None


def test_citation_for_returns_matching_citation():
    citation = Citation(source="JARVIS-DFT", identifier="JVASP-664")
    record = MaterialRecord(
        material_id="MoS2_monolayer",
        formula="MoS2",
        band_gap_eV=1.658,
        citations={"band_gap_eV": citation},
    )
    assert record.citation_for("band_gap_eV") is citation


def test_material_record_is_frozen():
    record = MaterialRecord(material_id="Test_material", formula="TeMa")
    try:
        record.band_gap_eV = 1.0  # type: ignore[misc]
        raised = False
    except dataclasses.FrozenInstanceError:
        raised = True
    assert raised, "MaterialRecord should be immutable (frozen dataclass)"
