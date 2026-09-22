"""Real end-to-end tests for mesh_generation.py -- needs gmsh's headless
"nox" build actually installed (see pyproject.toml's mesh-generation extra),
not the plain PyPI wheel, so this is requires_real_solver like every other
real-backend test in this project."""
from pathlib import Path

import pytest

from quantum_foundry.thermal.mesh_generation import (
    SURFACE_ADIABATIC_BOUNDARY,
    SURFACE_CHANNEL_HEAT_SOURCE,
    SURFACE_SUBSTRATE_BOTTOM_DIRICHLET,
    VOLUME_SI_SUBSTRATE,
    VOLUME_SIO2,
    LayeredSlabGeometry,
    MeshGenerationError,
    build_layered_slab_mesh,
    convert_msh_to_xdmf,
    default_slab_geometry_from_device,
)
from quantum_foundry.transport.results import DeviceGeometry

pytestmark = pytest.mark.requires_real_solver

_TOY_GEOMETRY = LayeredSlabGeometry(
    footprint_length_um=1.0,
    footprint_width_um=0.5,
    sio2_thickness_um=0.05,
    substrate_truncation_depth_um=5.0,
    mesh_characteristic_length_um=0.1,
)


def test_build_layered_slab_mesh_produces_real_tagged_mesh(tmp_path: Path):
    msh_path = build_layered_slab_mesh(_TOY_GEOMETRY, tmp_path / "slab.msh")
    assert msh_path.exists()
    assert msh_path.stat().st_size > 0

    # Inspected via meshio, not gmsh -- gmsh only ever runs out-of-process.
    import meshio

    mesh = meshio.read(msh_path)
    assert set(mesh.field_data.keys()) == {
        VOLUME_SIO2,
        VOLUME_SI_SUBSTRATE,
        SURFACE_CHANNEL_HEAT_SOURCE,
        SURFACE_SUBSTRATE_BOTTOM_DIRICHLET,
        SURFACE_ADIABATIC_BOUNDARY,
    }
    # Real tet elements exist in 3D -- not an empty/degenerate mesh.
    assert len(mesh.cells_dict["tetra"]) > 0


def test_build_layered_slab_mesh_rejects_degenerate_geometry(tmp_path: Path):
    zero_footprint = LayeredSlabGeometry(
        footprint_length_um=0.0,
        footprint_width_um=0.5,
        sio2_thickness_um=0.05,
        substrate_truncation_depth_um=5.0,
        mesh_characteristic_length_um=0.1,
    )
    # gmsh's OCC kernel reports "Error : Degenerate box"; the subprocess
    # wrapper surfaces that as a MeshGenerationError carrying gmsh's message.
    with pytest.raises(MeshGenerationError, match="[Dd]egenerate"):
        build_layered_slab_mesh(zero_footprint, tmp_path / "degenerate.msh")


def test_convert_msh_to_xdmf_preserves_named_physical_groups(tmp_path: Path):
    msh_path = build_layered_slab_mesh(_TOY_GEOMETRY, tmp_path / "slab.msh")
    xdmf_path = convert_msh_to_xdmf(msh_path, tmp_path / "slab.xdmf")
    assert xdmf_path.exists()

    import meshio

    mesh = meshio.read(msh_path)
    assert set(mesh.field_data.keys()) == {
        VOLUME_SIO2,
        VOLUME_SI_SUBSTRATE,
        SURFACE_CHANNEL_HEAT_SOURCE,
        SURFACE_SUBSTRATE_BOTTOM_DIRICHLET,
        SURFACE_ADIABATIC_BOUNDARY,
    }
    assert "tetra" in mesh.cells_dict
    assert "triangle" in mesh.cells_dict


def test_default_slab_geometry_from_device_converts_nm_to_um():
    device = DeviceGeometry(
        channel_length_nm=10.0,
        channel_width_nm=5.0,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=285.0,
        gate_oxide_material_id="SiO2",
        channel_material_id="MoS2_monolayer",
    )
    geometry = default_slab_geometry_from_device(device)
    assert geometry.footprint_length_um == pytest.approx(0.01)
    assert geometry.footprint_width_um == pytest.approx(0.005)
    assert geometry.sio2_thickness_um == pytest.approx(0.285)
    # Phase-1 default from docs/M5_PLAN.md's 10-50um recommended range.
    assert geometry.substrate_truncation_depth_um == pytest.approx(20.0)
