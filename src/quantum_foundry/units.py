"""Shared unit conventions used across the pipeline.

Canonical units (do not silently convert — every field name states its unit):
- Length: angstrom (lattice constants), nanometer (device geometry)
- Energy: eV
- Mass: units of the free electron mass m0
- Resistance: ohm*um (contact resistance, per standard TCAD convention)
- Mobility: cm^2/(V*s)
- Thermal conductivity: W/(m*K)
- Current density: uA/um
"""
from __future__ import annotations

ELECTRON_MASS_M0_KG = 9.1093837015e-31
BOLTZMANN_CONSTANT_EV_PER_K = 8.617333262e-5
ELEMENTARY_CHARGE_C = 1.602176634e-19
