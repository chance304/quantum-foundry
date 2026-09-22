import pytest
import yaml

from quantum_foundry.materials.citations import CitationCompletenessError
from quantum_foundry.materials.registry import MaterialNotFoundError, MaterialsDB


def test_loads_real_seed_data_without_citation_errors():
    """The checked-in seed_data/*.yaml must all pass citation-completeness —
    this is the actual enforcement of this project's core honesty rule."""
    db = MaterialsDB()
    assert set(db.list_ids()) >= {
        "MoS2_monolayer",
        "WSe2_monolayer",
        "WS2_monolayer",
        "HfO2",
        "ZrO2",
        "graphene_monolayer",
        "hBN_monolayer",
        "black_phosphorus_monolayer",
        "MoTe2_monolayer",
        "WTe2_monolayer",
    }


def test_mos2_real_values_loaded_correctly():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    assert mos2.formula == "MoS2"
    assert mos2.band_gap_eV == pytest.approx(1.658)
    assert mos2.citation_for("band_gap_eV").identifier == "JVASP-664"


def test_ws2_gap_resolved_with_real_cited_data():
    """WS2 was a standing all-null placeholder in an earlier session -- this
    session found a real JARVIS-DFT entry (JVASP-658) for it. This test
    documents the resolution, replacing the old placeholder-state test."""
    db = MaterialsDB()
    ws2 = db.get("WS2_monolayer")
    assert ws2.band_gap_eV == pytest.approx(1.337)
    assert ws2.citation_for("band_gap_eV").identifier == "JVASP-658"
    assert ws2.citation_for("band_gap_eV").verified is True


def test_mote2_and_wte2_now_have_real_c2db_data():
    """MoTe2/WTe2 were confirmed genuinely absent from the JARVIS-DFT
    dft_2d dataset (checked against the full dataset, not just search
    indexing) and stayed honest null placeholders through 2026-07-27.
    RESOLVED 2026-07-28: real C2DB entries found and directly read (the
    1H/p-6m2 semiconducting phase) -- see docs/DECISIONS.md and
    mote2_monolayer.yaml/wte2_monolayer.yaml. Every populated field still
    carries a real citation, never guessed."""
    db = MaterialsDB()
    for material_id in ("MoTe2_monolayer", "WTe2_monolayer"):
        material = db.get(material_id)
        assert material.band_gap_eV is not None
        assert material.effective_mass_electron is not None
        assert material.effective_mass_hole is not None
        for field_name in ("band_gap_eV", "effective_mass_electron", "effective_mass_hole"):
            assert field_name in material.citations
            assert material.citations[field_name].source == "C2DB"


def test_graphene_is_gapless_not_a_citation_gap():
    db = MaterialsDB()
    graphene = db.get("graphene_monolayer")
    assert graphene.band_gap_eV == 0.0
    assert graphene.effective_mass_electron is None  # no parabolic mass for a Dirac cone
    assert graphene.extra["band_structure_type"] == "gapless"


def test_black_phosphorus_uses_extra_for_anisotropic_data():
    db = MaterialsDB()
    bp = db.get("black_phosphorus_monolayer")
    assert bp.lattice_constant_angstrom is None
    assert bp.effective_mass_electron is None
    assert bp.extra["lattice_parameters"]["a_angstrom"] != bp.extra["lattice_parameters"]["b_angstrom"]
    assert "effective_mass_tensor" in bp.extra


def test_get_raises_for_unknown_material():
    db = MaterialsDB()
    with pytest.raises(MaterialNotFoundError):
        db.get("Unobtainium_monolayer")


def test_contains():
    db = MaterialsDB()
    assert "MoS2_monolayer" in db
    assert "Unobtainium_monolayer" not in db


def test_hfo2_uses_extra_for_lattice_parameters_not_scalar_field():
    db = MaterialsDB()
    hfo2 = db.get("HfO2")
    assert hfo2.lattice_constant_angstrom is None
    assert hfo2.extra["crystal_system"] == "monoclinic"


def test_enforcement_catches_an_uncited_value(tmp_path):
    bad_file = tmp_path / "bad_material.yaml"
    bad_file.write_text(
        yaml.safe_dump(
            {
                "material_id": "Bad_material",
                "formula": "Bad",
                "band_gap_eV": 2.0,
                # no citations for band_gap_eV — should be rejected
            }
        )
    )
    with pytest.raises(CitationCompletenessError):
        MaterialsDB(seed_data_dir=tmp_path)


def test_enforce_citations_false_allows_uncited_data(tmp_path):
    bad_file = tmp_path / "bad_material.yaml"
    bad_file.write_text(
        yaml.safe_dump({"material_id": "Bad_material", "formula": "Bad", "band_gap_eV": 2.0})
    )
    db = MaterialsDB(seed_data_dir=tmp_path, enforce_citations=False)
    assert db.get("Bad_material").band_gap_eV == 2.0
