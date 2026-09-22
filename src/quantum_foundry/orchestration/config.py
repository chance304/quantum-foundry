"""Run configuration for the pipeline. StageConfig picks a backend by name
(the same names each layer's get_backend() registers) plus arbitrary params
for that backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..thermal.results import MaterialStack
from ..transport.results import DeviceGeometry


@dataclass
class StageConfig:
    backend: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunConfig:
    material_id: str
    device_geometry: DeviceGeometry
    material_stack: MaterialStack | None = None  # None -> derived from device_geometry
    dft: StageConfig = field(default_factory=lambda: StageConfig(backend="stub"))
    transport: StageConfig = field(default_factory=lambda: StageConfig(backend="stub"))
    thermal: StageConfig = field(default_factory=lambda: StageConfig(backend="stub"))
    manufacturability: StageConfig = field(default_factory=lambda: StageConfig(backend="stub"))
