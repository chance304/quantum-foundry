"""Unit tests for hotspot_backend.py's pure-Python logic (no real binary
needed -- the real end-to-end run lives in tests/e2e/test_real_pipeline.py,
marked requires_real_solver since it needs the built HotSpot binary and
takes real wall-clock time)."""
import tempfile
from pathlib import Path

import pytest

from quantum_foundry.dft.stub import EffectiveMassDFTStub
from quantum_foundry.materials.registry import MaterialsDB
from quantum_foundry.thermal.hotspot_backend import (
    _MIN_DIE_SIDE_M,
    _pad_to_die_footprint,
    _write_layer_files,
    default_stacked_stack_from_geometry,
)
from quantum_foundry.thermal.results import MaterialStack, ThermalLayer
from quantum_foundry.transport.results import DeviceGeometry, DeviceTier
from quantum_foundry.transport.stub import LongChannelMOSFETStub


def test_small_device_gets_padded_to_min_die_footprint():
    blocks, was_padded = _pad_to_die_footprint("channel", 1e-7, 2e-8, "channel_fill")
    assert was_padded is True
    names = [b[0] for b in blocks]
    assert "channel" in names
    assert any("fill" in n for n in names)


def test_padded_blocks_tile_the_full_die_with_no_gaps():
    width_m, length_m = 1e-7, 2e-8
    blocks, _ = _pad_to_die_footprint("channel", width_m, length_m, "channel_fill")
    total_area = sum(w * h for _name, w, h, _x, _y in blocks)
    assert total_area == pytest.approx(_MIN_DIE_SIDE_M**2)


def test_device_already_at_or_above_min_die_is_not_padded():
    blocks, was_padded = _pad_to_die_footprint("channel", _MIN_DIE_SIDE_M, _MIN_DIE_SIDE_M, "channel_fill")
    assert was_padded is False
    assert blocks == [("channel", _MIN_DIE_SIDE_M, _MIN_DIE_SIDE_M, 0.0, 0.0)]


def test_no_overlap_between_real_device_and_fill_blocks():
    width_m, length_m = 1e-7, 2e-8
    blocks, _ = _pad_to_die_footprint("channel", width_m, length_m, "channel_fill")
    device = next(b for b in blocks if b[0] == "channel")
    _, dw, dh, dx, dy = device
    for name, w, h, x, y in blocks:
        if name == "channel":
            continue
        # every fill block should start at or beyond the device's extent in
        # at least one axis (the corner+strip tiling this function uses)
        assert x >= dx + dw or y >= dy + dh


def test_write_layer_files_flags_specific_heat_fallback_when_no_material_data():
    # No seeded material has specific_heat_capacity_J_per_m3K yet (real
    # schema gap, added 2026-07-22) -- every layer should fall back and be
    # flagged, distinctly from the (separately tracked) thermal-conductivity
    # fallback list.
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
    )
    transport_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    stack = MaterialStack(layers=[
        ThermalLayer("MoS2_monolayer", geometry.channel_thickness_nm, "channel"),
        ThermalLayer("HfO2", geometry.gate_oxide_thickness_nm, "gate_oxide"),
    ])

    with tempfile.TemporaryDirectory() as tmp:
        _, _, k_fallback_used, c_fallback_used, _ = _write_layer_files(
            Path(tmp), stack, [transport_result], db
        )

    assert set(c_fallback_used) == {"MoS2_monolayer", "HfO2"}
    # MoS2 has a real cited thermal_conductivity_W_mK, so it should NOT be
    # in the (separate) conductivity fallback list, while HfO2 (no seeded
    # value) correctly is.
    assert "MoS2_monolayer" not in k_fallback_used
    assert "HfO2" in k_fallback_used


# --- M9b: multi-tier (CFET/M3D) thermal model, added 2026-07-27 ---


def _cfet_geometry() -> DeviceGeometry:
    return DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
        stacked_tiers=[
            DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
            DeviceTier(channel_material_id="WS2_monolayer", channel_thickness_nm=0.65, carrier_type="hole"),
        ],
    )


def test_default_stacked_stack_has_one_channel_layer_per_tier_and_interfaces_between():
    stack = default_stacked_stack_from_geometry(_cfet_geometry())
    roles = [layer.role for layer in stack.layers]
    # 2 tiers -> 2 channel layers, exactly 1 interface between them (not
    # before the first or after the last), plus the existing gate_oxide/
    # substrate wrapping default_stack_from_geometry() already has.
    assert roles == ["channel", "tier_interface", "channel", "gate_oxide", "substrate"]
    channel_materials = [layer.material_id for layer in stack.layers if layer.role == "channel"]
    assert channel_materials == ["MoS2_monolayer", "WS2_monolayer"]


def test_default_stacked_stack_requires_stacked_tiers():
    plain_geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    with pytest.raises(ValueError, match="stacked_tiers"):
        default_stacked_stack_from_geometry(plain_geometry)


def test_write_layer_files_gives_each_tier_its_own_real_power_not_borrowed():
    # The real bug M9 scoping found: a single TransportResult's power
    # applied to every "channel"-role layer would be wrong for two
    # independently-operating stacked tiers. Verify each tier's ptrace
    # power comes from its own TransportResult.
    db = MaterialsDB()
    geometry = _cfet_geometry()
    mos2 = db.get("MoS2_monolayer")
    ws2 = db.get("WS2_monolayer")
    mos2_dft = EffectiveMassDFTStub().run(mos2, {"carrier_type": "electron"})
    ws2_dft = EffectiveMassDFTStub().run(ws2, {"carrier_type": "hole"})
    mos2_transport = LongChannelMOSFETStub().run(mos2, mos2_dft, geometry, {"carrier_type": "electron"})
    ws2_transport = LongChannelMOSFETStub().run(ws2, ws2_dft, geometry, {"carrier_type": "hole"})
    assert mos2_transport.power_density_W_per_um2 != ws2_transport.power_density_W_per_um2  # real, not coincidental

    stack = default_stacked_stack_from_geometry(geometry)
    with tempfile.TemporaryDirectory() as tmp:
        _, ptrace_path, _, _, _ = _write_layer_files(
            Path(tmp), stack, [mos2_transport, ws2_transport], db,
            {"kapitza_resistance_m2K_per_W": 1e-8},
        )
        ptrace_lines = ptrace_path.read_text().splitlines()

    units = ptrace_lines[0].split("\t")
    powers = {name: float(p) for name, p in zip(units, ptrace_lines[1].split("\t"))}
    mos2_power_w = mos2_transport.power_density_W_per_um2 * (
        geometry.channel_width_nm * geometry.channel_length_nm * 1e-6
    )
    ws2_power_w = ws2_transport.power_density_W_per_um2 * (
        geometry.channel_width_nm * geometry.channel_length_nm * 1e-6
    )
    assert powers["channel_0"] == pytest.approx(mos2_power_w)
    assert powers["channel_2"] == pytest.approx(ws2_power_w)


def test_write_layer_files_refuses_tier_interface_without_kapitza_param():
    db = MaterialsDB()
    geometry = _cfet_geometry()
    mos2, ws2 = db.get("MoS2_monolayer"), db.get("WS2_monolayer")
    mos2_dft = EffectiveMassDFTStub().run(mos2, {"carrier_type": "electron"})
    ws2_dft = EffectiveMassDFTStub().run(ws2, {"carrier_type": "hole"})
    mos2_transport = LongChannelMOSFETStub().run(mos2, mos2_dft, geometry, {"carrier_type": "electron"})
    ws2_transport = LongChannelMOSFETStub().run(ws2, ws2_dft, geometry, {"carrier_type": "hole"})
    stack = default_stacked_stack_from_geometry(geometry)

    with tempfile.TemporaryDirectory() as tmp, pytest.raises(ValueError, match="kapitza_resistance_m2K_per_W"):
        _write_layer_files(Path(tmp), stack, [mos2_transport, ws2_transport], db, {})


def test_write_layer_files_rejects_transport_result_count_mismatch():
    db = MaterialsDB()
    geometry = _cfet_geometry()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    transport_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    stack = default_stacked_stack_from_geometry(geometry)  # 2 channel layers

    with tempfile.TemporaryDirectory() as tmp, pytest.raises(ValueError, match="1:1"):
        _write_layer_files(Path(tmp), stack, [transport_result], db, {"kapitza_resistance_m2K_per_W": 1e-8})
