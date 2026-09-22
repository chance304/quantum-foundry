import pytest

from quantum_foundry.materials.citations import (
    CitationCompletenessError,
    assert_citations_complete,
    missing_citations,
)
from quantum_foundry.materials.schema import Citation, MaterialRecord


def test_missing_citations_empty_when_no_values_set():
    record = MaterialRecord(material_id="Test_material", formula="TeMa")
    assert missing_citations(record) == []


def test_missing_citations_flags_uncited_value():
    record = MaterialRecord(material_id="Test_material", formula="TeMa", band_gap_eV=1.5)
    assert missing_citations(record) == ["band_gap_eV"]


def test_missing_citations_ignores_non_citable_identity_fields():
    record = MaterialRecord(material_id="Test_material", formula="TeMa")
    # material_id/formula are identity fields, never expected to need a Citation
    assert "material_id" not in missing_citations(record)
    assert "formula" not in missing_citations(record)


def test_assert_citations_complete_passes_when_all_cited():
    record = MaterialRecord(
        material_id="Test_material",
        formula="TeMa",
        band_gap_eV=1.5,
        citations={"band_gap_eV": Citation(source="Test paper", identifier="doi:10.0/test")},
    )
    assert_citations_complete(record)  # should not raise


def test_assert_citations_complete_raises_on_uncited_value():
    record = MaterialRecord(material_id="Test_material", formula="TeMa", band_gap_eV=1.5)
    with pytest.raises(CitationCompletenessError):
        assert_citations_complete(record)
