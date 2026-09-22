"""Run one device through the full pipeline (stub backends) and print every
stage's result together with its provenance.

    python examples/01_single_device.py

Stub backends are fast and need no heavy solvers, but their numbers are
stand-ins: every result says so via ``provenance.is_stub``.
"""
from quantum_foundry.orchestration.config import RunConfig
from quantum_foundry.orchestration.pipeline import Pipeline
from quantum_foundry.transport.results import DeviceGeometry

geometry = DeviceGeometry(
    channel_length_nm=20.0,
    channel_width_nm=100.0,
    channel_thickness_nm=0.65,  # MoS2 monolayer
    gate_oxide_thickness_nm=2.0,
    gate_oxide_material_id="HfO2",
    channel_material_id="MoS2_monolayer",
    substrate_material_id="Si",
)
result = Pipeline().run(RunConfig(material_id="MoS2_monolayer", device_geometry=geometry))

stages = {
    "dft": result.dft_result,
    "transport": result.transport_result,
    "thermal": result.thermal_result,
    "yield": result.yield_result,
}
for name, stage in stages.items():
    p = stage.provenance
    print(f"{name:10s} backend={p.backend_name:12s} stub={p.is_stub}")

print()
print(f"Ion             {result.transport_result.ion_uA_per_um:.3g} uA/um")
print(f"Junction temp   {result.thermal_result.max_junction_temp_C:.1f} C")
print(f"Yield           {result.yield_result.yield_fraction:.3f}")
for check in (result.extra["beol_budget_check"], result.extra["m3d_layer_transfer_check"]):
    status = "PASS" if check.passed else "FAIL"
    print(f"{check.limit_name}: {status} (margin {check.margin_C:+.1f} C)")
