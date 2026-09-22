"""Unit tests for materials/sources/jarvis_dft.py's field-extraction logic.

Deliberately does NOT import jarvis-tools or hit the network -- jarvis-tools
is an optional, non-dev dependency (pyproject.toml's materials-sources
extra), not installed in the lightweight CI job. _extract_fields() is a
pure function specifically so this logic stays testable without it; see
its docstring in jarvis_dft.py.
"""
from quantum_foundry.materials.sources.jarvis_dft import _extract_fields

# A synthetic row shaped like the real jarvis-tools dft_2d dataset record
# for black_phosphorus_monolayer (JVASP-5983) -- values confirmed 2026-07-22
# against the actual installed jarvis-tools dataset (see docs/DECISIONS.md),
# matching the pre-existing hand-seeded black_phosphorus_monolayer.yaml to
# rounding.
_BLACK_PHOSPHORUS_ROW = {
    "jid": "JVASP-5983",
    "optb88vdw_bandgap": 0.848,
    "epsx": 3.0519,
    "epsy": 4.4231,
    "epsz": 2.0532,
    "atoms": {"abc": [3.32246, 4.57864, 30.71665]},
    "effective_masses_300K": {
        "n": [1.31, 0.19, 1554.26],
        "p": [3.25, 0.16, 308.59],
    },
}

# A synthetic isotropic row shaped like a hexagonal TMD (e.g. MoS2) -- a=b,
# so only the [0] component matters for lattice/mass extraction.
_ISOTROPIC_ROW = {
    "jid": "JVASP-664",
    "optb88vdw_bandgap": 1.68,
    "epsx": 8.5,
    "atoms": {"abc": [3.19, 3.19, 24.0]},
    "effective_masses_300K": {
        "n": [0.51, 0.51, 3.0],
        "p": [0.62, 0.62, 3.2],
    },
}


def test_anisotropic_material_gets_tensor_extra_fields_not_scalars():
    result = _extract_fields("black_phosphorus_monolayer", _BLACK_PHOSPHORUS_ROW)

    # Isotropic scalar fields must stay absent -- a real anisotropic
    # material has no single correct value for these.
    assert "lattice_constant_angstrom" not in result["fields"]
    assert "effective_mass_electron" not in result["fields"]
    assert "effective_mass_hole" not in result["fields"]
    assert "dielectric_constant" not in result["fields"]

    # band_gap_eV is a real isotropic scalar -- still extracted normally.
    assert result["fields"]["band_gap_eV"] == 0.848

    extra = result["extra_fields"]
    assert extra["lattice_parameters"] == {"a_angstrom": 3.32246, "b_angstrom": 4.57864}
    assert extra["effective_mass_tensor"] == {
        "electron": {"armchair_x": 1.31, "zigzag_y": 0.19},
        "hole": {"armchair_x": 3.25, "zigzag_y": 0.16},
    }
    assert extra["dielectric_tensor"] == {
        "epsx_armchair": 3.0519,
        "epsy_zigzag": 4.4231,
        "epsz_out_of_plane": 2.0532,
    }


def test_isotropic_material_still_gets_flat_scalar_fields():
    result = _extract_fields("MoS2_monolayer", _ISOTROPIC_ROW)

    assert result["fields"]["band_gap_eV"] == 1.68
    assert result["fields"]["dielectric_constant"] == 8.5
    assert result["fields"]["lattice_constant_angstrom"] == 3.19
    assert result["fields"]["effective_mass_electron"] == 0.51
    assert result["fields"]["effective_mass_hole"] == 0.62
    assert result["extra_fields"] == {}
