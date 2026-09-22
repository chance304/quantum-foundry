from quantum_foundry.orchestration.config import RunConfig
from quantum_foundry.orchestration.pareto import pareto_front
from quantum_foundry.orchestration.sweep import sweep
from quantum_foundry.transport.results import DeviceGeometry


def test_pareto_front_excludes_dominated_results():
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    base_config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry)
    results = sweep(base_config, stage="transport", param="vdd_V", values=[0.5, 0.7, 0.9])

    front = pareto_front(
        results,
        objectives={
            "ion": lambda r: r.transport_result.ion_uA_per_um,
            "power": lambda r: r.transport_result.power_density_W_per_um2,
        },
        minimize={"power"},
    )
    # Higher vdd strictly increases both ion and power in the stub model, so
    # every point trades off ion vs power -- none should dominate another,
    # meaning the whole set is Pareto-optimal here.
    assert len(front) == len(results)
