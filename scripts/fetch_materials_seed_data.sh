#!/bin/sh
# Refresh cached materials seed data from JARVIS-DFT, C2DB, and Materials
# Project. Delegates to the actual source modules (src/quantum_foundry/
# materials/sources/) rather than hardcoding API calls here, so there is one
# place that owns each source's real query/parsing logic.
#
# Materials Project requires an API key: set MP_API_KEY before running, or
# this will skip that source with a warning (never fabricate MP data).
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

echo "Refreshing JARVIS-DFT seed data..."
python -m quantum_foundry.materials.sources.jarvis_dft --refresh

echo "Refreshing C2DB seed data..."
python -m quantum_foundry.materials.sources.c2db --refresh

if [ -n "${MP_API_KEY:-}" ]; then
    echo "Refreshing Materials Project seed data..."
    python -m quantum_foundry.materials.sources.materials_project --refresh
else
    echo "MP_API_KEY not set — skipping Materials Project refresh." >&2
fi

echo "Done. Seed data written to src/quantum_foundry/materials/sources/seed_data/."
