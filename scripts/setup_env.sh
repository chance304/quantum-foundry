#!/bin/sh
# Create or update the quantum-foundry conda/mamba environment, and vendor
# HotSpot (small unpackaged C project, not conda/pip-distributable).
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

conda_bin=""
if command -v mamba >/dev/null 2>&1; then
    conda_bin="mamba"
elif command -v conda >/dev/null 2>&1; then
    conda_bin="conda"
else
    echo "ERROR: neither mamba nor conda found on PATH." >&2
    exit 1
fi

if "$conda_bin" env list | grep -q '^quantum-foundry '; then
    echo "Updating existing quantum-foundry environment..."
    "$conda_bin" env update -n quantum-foundry -f environment.yml --prune
else
    echo "Creating quantum-foundry environment..."
    "$conda_bin" env create -f environment.yml
fi

hotspot_dir="$repo_root/.vendor/hotspot"
if [ ! -d "$hotspot_dir" ]; then
    echo "Vendoring HotSpot (compact thermal model, unpackaged)..."
    mkdir -p "$repo_root/.vendor"
    # Pinned to a specific commit (not the mutable default branch) so a
    # future upstream change/force-push can't silently alter what gets
    # built and run here -- same supply-chain rationale as SHA-pinning
    # third-party GitHub Actions in ci.yml. Re-verify and bump deliberately
    # if HotSpot needs to be updated. (2026-08-04 security/supply-chain audit)
    hotspot_pinned_sha="f18831e48cef5d62580585cca0d7fab6c71bc3cc" # master, as of 2026-08-04
    git clone https://github.com/uvahotspot/HotSpot.git "$hotspot_dir"
    ( cd "$hotspot_dir" && git checkout "$hotspot_pinned_sha" )
    ( cd "$hotspot_dir" && make )
    # HotSpot ships template.config, not hotspot.config -- thermal/hotspot_backend.py
    # expects the latter name. Verified real gap 2026-07-21 (this line was
    # previously missing entirely; hotspot_backend.py would fail loudly with a
    # clear "config not found" error, not silently, but the fix belongs here).
    cp "$hotspot_dir/template.config" "$hotspot_dir/hotspot.config"
else
    echo "HotSpot already vendored at $hotspot_dir, skipping."
fi

echo "Installing gmsh's official headless 'nox' build for M5's mesh-generation step..."
# The plain PyPI gmsh wheel dlopen's libGLU.so.1 at import time even for
# headless mesh generation -- verified missing (and unfixable without root)
# in every sandbox tried so far, see docs/DECISIONS.md. The nox build avoids
# this entirely (verified 2026-08-03, docs/M10_PLAN.md's "Verification
# pass"), but it's a prerelease-only index, hence --pre and the separate -i
# here rather than folding it into pyproject.toml's mesh-generation extra.
"$conda_bin" run -n quantum-foundry pip install \
    -i https://gmsh.info/python-packages-dev-nox --pre "gmsh>=4.12,<5"

echo "Done. Run scripts/preflight.sh to verify everything is actually usable."
