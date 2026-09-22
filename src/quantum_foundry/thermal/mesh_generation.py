"""3D mesh generation for the layered device stack -- M5's first real code.

Builds the "minimal first 3D case" from `docs/M5_PLAN.md`: a truncated Si
substrate under a SiO2 gate-oxide layer, with the 2D-material channel (e.g.
MoS2) modeled as a thin *surface* at the SiO2/ambient interface rather than
a thin 3D solid. This is physically defensible per `docs/M5_PLAN.md`'s
"Mesh generation" section -- the monolayer's own through-thickness thermal
resistance is negligible next to its interface resistance to SiO2 -- and it
avoids the degenerate-element problem a true sub-nanometer 3D solid layer
would create next to a micron-scale substrate (the exact scale-mismatch
problem `thermal/hotspot_backend.py`'s own `_pad_to_die_footprint()` had to
solve for the compact model).

Requires gmsh's headless "nox" build, not the plain PyPI wheel -- see
`pyproject.toml`'s `mesh-generation` extra for why and how to install it.
Verified working 2026-08-03 (`docs/M10_PLAN.md`'s "Verification pass"):
this exact geometry construction, physical-group tagging, and meshio/XDMF
export were run end-to-end before this module was written.

**Real, flagged limitation, not hidden**: this is the *minimal first case*
`docs/M5_PLAN.md` scopes. The channel heat source covers the entire SiO2
top face (footprint == channel footprint) -- it does not yet implement the
die-footprint-padding scale-mismatch handling `hotspot_backend.py`'s
`_pad_to_die_footprint()` needed for the compact model. A production-scale
device (nm-scale channel inside a much larger real chip) would likely need
the same treatment here; not built, since no real FEniCSx/Elmer backend
consumes this mesh yet to make that requirement concrete.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..transport.results import DeviceGeometry

# Physical group names -- shared constants so downstream FEniCSx/Elmer
# backends (M5, not yet built) can look these up by name via meshio's
# field_data/cell_sets rather than fragile gmsh tag numbers. Verified
# 2026-08-03 that these survive a real gmsh -> meshio -> XDMF round trip.
VOLUME_SIO2 = "sio2"
VOLUME_SI_SUBSTRATE = "si_substrate"
SURFACE_CHANNEL_HEAT_SOURCE = "channel_heat_source"
SURFACE_SUBSTRATE_BOTTOM_DIRICHLET = "substrate_bottom_dirichlet"
SURFACE_ADIABATIC_BOUNDARY = "adiabatic_boundary"


class MeshGenerationError(RuntimeError):
    """Raised when the geometry construction doesn't produce what this
    module expects (e.g. fragmenting the two boxes doesn't yield exactly
    two volumes) -- a real construction failure, not a silently-wrong mesh.
    """


@dataclass(frozen=True)
class LayeredSlabGeometry:
    """The minimal first 3D case from `docs/M5_PLAN.md`: one rectangular
    footprint, a SiO2 gate-oxide layer over a truncated Si substrate, with
    the channel material modeled as a surface at their shared top face.

    All lengths in micrometers -- gmsh's OCC kernel has no inherent unit,
    and this project's existing `DeviceGeometry` uses nanometers for
    device-scale fields, so `default_slab_geometry_from_device()` below
    does the nm -> um conversion explicitly rather than mixing scales
    silently.
    """

    footprint_length_um: float
    footprint_width_um: float
    sio2_thickness_um: float
    substrate_truncation_depth_um: float
    mesh_characteristic_length_um: float


def default_slab_geometry_from_device(
    device: DeviceGeometry,
    substrate_truncation_depth_um: float = 20.0,
    mesh_characteristic_length_um: float | None = None,
) -> LayeredSlabGeometry:
    """Bridges the existing transport-layer `DeviceGeometry` into the
    minimal 3D FEA slab geometry.

    `substrate_truncation_depth_um` defaults to 20um, the middle of
    `docs/M5_PLAN.md`'s recommended 10-50um range -- a Phase-1 default, not
    a physically-derived value, same discipline as
    `thermal/hotspot_backend.py`'s own padding constants.
    """
    footprint_length_um = device.channel_length_nm / 1000.0
    footprint_width_um = device.channel_width_nm / 1000.0
    sio2_thickness_um = device.gate_oxide_thickness_nm / 1000.0
    if mesh_characteristic_length_um is None:
        # Coarse default sized to the footprint, not the sub-nm channel --
        # deliberately not tied to channel_thickness_nm, since the channel
        # is modeled as a surface here, not meshed as its own thin solid.
        mesh_characteristic_length_um = min(footprint_length_um, footprint_width_um) / 4.0
    return LayeredSlabGeometry(
        footprint_length_um=footprint_length_um,
        footprint_width_um=footprint_width_um,
        sio2_thickness_um=sio2_thickness_um,
        substrate_truncation_depth_um=substrate_truncation_depth_um,
        mesh_characteristic_length_um=mesh_characteristic_length_um,
    )


def build_layered_slab_mesh(geometry: LayeredSlabGeometry, output_msh_path: Path) -> Path:
    """Builds and meshes the two-volume stack, writes a real gmsh `.msh`
    file with named physical groups for both volumes and all three
    boundary regions (channel heat source, substrate Dirichlet bottom,
    adiabatic lateral/remaining faces) -- see module docstring for the
    physical design this implements.

    gmsh runs as a separate process driven by a generated `.geo` script,
    never imported in-process -- the same arm's-length pattern this project
    already uses for HotSpot and Elmer. gmsh is GPL-licensed; keeping it
    behind a subprocess boundary keeps this Apache-2.0 package free of any
    in-process linkage to it (see THIRD_PARTY_LICENSES.md).
    """
    output_msh_path = Path(output_msh_path)
    geo_path = output_msh_path.with_suffix(".geo")
    geo_path.write_text(_layered_slab_geo_script(geometry))

    completed = subprocess.run(
        [*_gmsh_command(), str(geo_path), "-3", "-format", "msh4", "-o", str(output_msh_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    gmsh_output = completed.stdout + completed.stderr
    error_lines = [line for line in gmsh_output.splitlines() if "Error" in line]
    if completed.returncode != 0 or error_lines or not output_msh_path.exists():
        raise MeshGenerationError(
            f"gmsh failed (exit code {completed.returncode}): "
            + ("; ".join(error_lines) or gmsh_output.strip()[-2000:])
        )
    _check_physical_groups(output_msh_path)
    return output_msh_path


def _gmsh_command() -> list[str]:
    """Locates the gmsh executable: `QF_GMSH_BINARY` if set, else `gmsh`
    on PATH, else the one the nox pip package installs next to the running
    interpreter (covers a venv that isn't activated). The pip package's
    launcher is a Python script with an `#!/usr/bin/env python` shebang, so
    it is run with the current interpreter rather than trusting PATH to
    resolve `python`."""
    override = os.environ.get("QF_GMSH_BINARY")
    if override:
        return [override]
    found = shutil.which("gmsh")
    if found is None:
        beside_interpreter = Path(sys.executable).parent / "gmsh"
        if not beside_interpreter.exists():
            raise MeshGenerationError(
                "gmsh executable not found -- install gmsh's headless build "
                "(see pyproject.toml's mesh-generation extra) or set QF_GMSH_BINARY."
            )
        found = str(beside_interpreter)
    with open(found, "rb") as launcher:
        first_line = launcher.readline()
    if first_line.startswith(b"#!") and b"python" in first_line:
        return [sys.executable, found]
    return [found]


def _layered_slab_geo_script(geometry: LayeredSlabGeometry) -> str:
    """Generates the gmsh `.geo` script for the layered slab.

    SiO2 sits at z >= 0 and the truncated Si substrate at z < 0. Volumes and
    boundary surfaces are selected by bounding-box location rather than by
    gmsh's own tag assignment order, which isn't part of its documented
    contract. The two boxes are fragmented so they share a conformal
    interface mesh -- required for a continuous-Galerkin heat solve across
    the SiO2/Si boundary (no gap, no duplicate nodes at the shared face).
    """
    length = geometry.footprint_length_um
    width = geometry.footprint_width_um
    top_z = geometry.sio2_thickness_um
    bottom_z = -geometry.substrate_truncation_depth_um
    return f"""SetFactory("OpenCASCADE");
General.Terminal = 1;
eps = 1e-6;
L = {length!r};
W = {width!r};
T = {top_z!r};
B = {bottom_z!r};
Box(1) = {{0, 0, 0, L, W, T}};
Box(2) = {{0, 0, B, L, W, -B}};
BooleanFragments{{ Volume{{1}}; Delete; }}{{ Volume{{2}}; Delete; }}

sio2() = Volume In BoundingBox{{-eps, -eps, -eps, L + eps, W + eps, T + eps}};
si() = Volume In BoundingBox{{-eps, -eps, B - eps, L + eps, W + eps, eps}};
If (#sio2() != 1 || #si() != 1)
  Error("Expected exactly one SiO2 and one Si substrate volume after fragmenting");
EndIf

top() = Surface In BoundingBox{{-eps, -eps, T - eps, L + eps, W + eps, T + eps}};
bottom() = Surface In BoundingBox{{-eps, -eps, B - eps, L + eps, W + eps, B + eps}};
If (#top() == 0 || #bottom() == 0)
  Error("Expected to find top and bottom boundary surfaces");
EndIf
lateral() = Surface{{:}};
lateral() -= top();
lateral() -= bottom();

Physical Volume("{VOLUME_SIO2}") = sio2();
Physical Volume("{VOLUME_SI_SUBSTRATE}") = si();
Physical Surface("{SURFACE_CHANNEL_HEAT_SOURCE}") = top();
Physical Surface("{SURFACE_SUBSTRATE_BOTTOM_DIRICHLET}") = bottom();
Physical Surface("{SURFACE_ADIABATIC_BOUNDARY}") = lateral();

Mesh.MeshSizeMax = {geometry.mesh_characteristic_length_um!r};
"""


def _check_physical_groups(msh_path: Path) -> None:
    """Reads the written mesh back (via meshio, not gmsh) and confirms every
    named physical group and real 3D elements are present -- a construction
    failure raises here rather than leaving a silently-wrong mesh."""
    import meshio

    mesh = meshio.read(msh_path)
    expected = {
        VOLUME_SIO2,
        VOLUME_SI_SUBSTRATE,
        SURFACE_CHANNEL_HEAT_SOURCE,
        SURFACE_SUBSTRATE_BOTTOM_DIRICHLET,
        SURFACE_ADIABATIC_BOUNDARY,
    }
    missing = expected - set(mesh.field_data)
    if missing or "tetra" not in mesh.cells_dict:
        raise MeshGenerationError(
            f"gmsh wrote {msh_path} but it is missing physical groups {sorted(missing)} "
            f"or 3D tetrahedral elements (cell types: {sorted(mesh.cells_dict)})."
        )


def convert_msh_to_xdmf(msh_path: Path, xdmf_path: Path) -> Path:
    """Converts a gmsh `.msh` file to XDMF+HDF5 via `meshio`, for FEniCSx
    ingestion (`thermal/results.py`'s `FieldHandle.format="xdmf_hdf5"`).
    Needs `h5py` installed (`pyproject.toml`'s `mesh-generation` extra) --
    verified 2026-08-03 that the named physical groups this module writes
    (volumes and boundary surfaces) survive this conversion intact via
    meshio's `field_data`/`cell_sets`.
    """
    import meshio

    mesh = meshio.read(msh_path)
    meshio.write(xdmf_path, mesh)
    return xdmf_path
