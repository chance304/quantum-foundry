import re

import pytest

from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry, TransportResult
from quantum_foundry.transport.verilog_a_export import export_verilog_a


def _transport_result(iv_curve, is_stub=True, channel_width_nm=100.0) -> TransportResult:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=channel_width_nm, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    return TransportResult(
        device_geometry=geometry, ion_uA_per_um=max(i for _v, i in iv_curve),
        ioff_uA_per_um=min(i for _v, i in iv_curve),
        subthreshold_swing_mV_dec=70.0, mobility_cm2_Vs=30.0, contact_resistance_ohm_um=1000.0,
        power_density_W_per_um2=1e-6, iv_curve=iv_curve,
        provenance=ProvenanceInfo(backend_name="test", is_stub=is_stub),
    )


def test_export_verilog_a_converts_ua_per_um_to_absolute_amps():
    # channel_width_nm=100 -> width_um=0.1; a 10 uA/um point -> 10*0.1*1e-6 = 1e-6 A
    tr = _transport_result([(0.0, 0.0), (0.5, 10.0)], channel_width_nm=100.0)
    va = export_verilog_a("MoS2_monolayer", tr, vds_V=0.05)
    assert "1e-06" in va or "1.0e-06" in va or "1e-6" in va


def test_export_verilog_a_module_name_is_sanitized():
    tr = _transport_result([(0.0, 0.0), (0.5, 1.0)])
    va = export_verilog_a("MoS2_monolayer", tr, vds_V=0.05)
    assert "module qf_MoS2_monolayer_behavioral(d, g, s);" in va


def test_export_verilog_a_refuses_with_fewer_than_two_points():
    tr = _transport_result([(0.0, 0.0)])
    with pytest.raises(ValueError, match="at least 2"):
        export_verilog_a("MoS2_monolayer", tr, vds_V=0.05)


def _assert_balanced_keywords(va: str) -> None:
    # Word-boundary matched so "backend"/"endmodule" (which contain "end" as
    # a substring but aren't the "end" keyword) don't produce a false count.
    begins = len(re.findall(r"\bbegin\b", va))
    ends = len(re.findall(r"\bend\b", va))
    assert begins == ends
    assert va.count("endmodule") == 1


def test_export_verilog_a_is_syntactically_balanced():
    tr = _transport_result([(0.0, 0.0), (0.2, 1.0), (0.4, 5.0), (0.6, 20.0)])
    va = export_verilog_a("MoS2_monolayer", tr, vds_V=0.05)
    _assert_balanced_keywords(va)
    assert va.count("module ") == 1
    assert '`include "disciplines.vams"' in va


def test_export_verilog_a_labels_stub_vs_real_backend():
    stub_result = _transport_result([(0.0, 0.0), (0.5, 1.0)], is_stub=True)
    real_result = _transport_result([(0.0, 0.0), (0.5, 1.0)], is_stub=False)
    stub_va = export_verilog_a("MoS2_monolayer", stub_result, vds_V=0.05)
    real_va = export_verilog_a("MoS2_monolayer", real_result, vds_V=0.05)
    assert "stub" in stub_va
    assert "real solver" in real_va


def test_export_verilog_a_scales_current_by_vds_not_independent_of_it():
    """Real gap found+fixed 2026-07-27 (standards audit): the original
    version made I(d,s) depend only on V(g,s), so it would output a fixed
    nonzero current even at Vds=0 -- unphysical, and a real SPICE
    convergence risk (zero output conductance everywhere). Verifies the fix
    is actually present: I(d,s) is now scaled by tanh(V(d,s)/...)."""
    tr = _transport_result([(0.0, 0.0), (0.5, 10.0)])
    va = export_verilog_a("MoS2_monolayer", tr, vds_V=0.05)
    assert "tanh(V(d,s)" in va
    assert "i_lookup" in va


def test_vds_safety_smoothing_is_zero_at_origin_and_negligible_at_real_bias_points():
    """Numerical sanity check of the actual smoothing math (tanh(Vds/
    VDS_SAFETY_V)) mirrored in Python, since no real Verilog-A simulator is
    available in this sandbox to execute the generated file directly."""
    import math

    from quantum_foundry.transport.verilog_a_export import _VDS_SAFETY_V

    assert math.tanh(0.0 / _VDS_SAFETY_V) == 0.0
    # Every vds_V this project's real backends actually use (0.05-0.8V)
    # should leave the smoothing factor within 0.1% of 1.0 -- negligible
    # perturbation to the model's real, intended operating point.
    for real_vds_v in (0.05, 0.1, 0.4, 0.7, 0.8):
        assert math.tanh(real_vds_v / _VDS_SAFETY_V) > 0.999


def test_export_verilog_a_real_end_to_end_stub_pipeline():
    from quantum_foundry.orchestration.config import RunConfig
    from quantum_foundry.orchestration.pipeline import Pipeline

    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
    )
    config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry)
    result = Pipeline().run(config)
    va = export_verilog_a("MoS2_monolayer", result.transport_result, vds_V=0.7)

    _assert_balanced_keywords(va)
