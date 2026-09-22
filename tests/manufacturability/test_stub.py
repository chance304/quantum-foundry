from quantum_foundry.manufacturability.stub import TrivialYieldStub
from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry, TransportResult


def _transport_result() -> TransportResult:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    return TransportResult(
        device_geometry=geometry, ion_uA_per_um=100.0, ioff_uA_per_um=0.01,
        subthreshold_swing_mV_dec=70.0, mobility_cm2_Vs=30.0, contact_resistance_ohm_um=1000.0,
        power_density_W_per_um2=1e-6, iv_curve=[],
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )


def test_stub_yield_fraction_bounded():
    result = TrivialYieldStub().run(_transport_result(), {})
    assert 0.0 <= result.yield_fraction <= 1.0
    assert result.model == "trivial_linear"
    assert result.provenance.is_stub is True
