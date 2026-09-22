"""Unit tests for materials/sources/_yaml_merge.py's merge_field()."""
import yaml

from quantum_foundry.materials.schema import Citation
from quantum_foundry.materials.sources._yaml_merge import merge_field

_CITATION = Citation(
    source="JARVIS-DFT",
    identifier="JVASP-5983",
    url="https://www.ctcms.nist.gov/~knc6/jsmol/JVASP-5983.html",
    verified=True,
)


def test_extra_fields_merge_without_clobbering_sibling_extra_keys(tmp_path):
    seed_path = tmp_path / "black_phosphorus_monolayer.yaml"
    seed_path.write_text(
        yaml.safe_dump(
            {
                "material_id": "black_phosphorus_monolayer",
                "citations": {},
                "extra": {"crystal_system": "orthorhombic", "space_group": "Pmna"},
            }
        )
    )

    merge_field(
        tmp_path,
        "black_phosphorus_monolayer",
        fields={"band_gap_eV": 0.848},
        citation=_CITATION,
        extra_fields={"lattice_parameters": {"a_angstrom": 3.32246, "b_angstrom": 4.57864}},
    )

    data = yaml.safe_load(seed_path.read_text())
    assert data["band_gap_eV"] == 0.848
    assert data["extra"]["lattice_parameters"] == {"a_angstrom": 3.32246, "b_angstrom": 4.57864}
    # Sibling extra keys another source already wrote must survive untouched.
    assert data["extra"]["crystal_system"] == "orthorhombic"
    assert data["extra"]["space_group"] == "Pmna"
    # extra_fields keys get their own citation, same discipline as flat fields.
    assert data["citations"]["lattice_parameters"]["identifier"] == "JVASP-5983"
    assert data["citations"]["band_gap_eV"]["identifier"] == "JVASP-5983"


def test_no_extra_fields_leaves_extra_dict_untouched(tmp_path):
    seed_path = tmp_path / "mos2_monolayer.yaml"
    seed_path.write_text(
        yaml.safe_dump(
            {
                "material_id": "MoS2_monolayer",
                "citations": {},
                "extra": {"some_existing_key": "value"},
            }
        )
    )

    merge_field(
        tmp_path,
        "MoS2_monolayer",
        fields={"band_gap_eV": 1.68},
        citation=_CITATION,
    )

    data = yaml.safe_load(seed_path.read_text())
    assert data["extra"] == {"some_existing_key": "value"}
