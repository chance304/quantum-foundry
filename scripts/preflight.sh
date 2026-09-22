#!/bin/sh
# Verify real-backend prerequisites are present. Exits non-zero (and refuses
# `qf run --backend real`, per the caller's own check) if anything required
# is missing — this deliberately does NOT silently fall back to stubs.
set -eu

missing=0

check_cmd() {
    name="$1"
    cmd="$2"
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "  [ok]      $name ($cmd)"
    else
        echo "  [missing] $name ($cmd not on PATH)"
        missing=1
    fi
}

check_py_module() {
    name="$1"
    module="$2"
    if python -c "import $module" >/dev/null 2>&1; then
        echo "  [ok]      $name (python -c 'import $module')"
    else
        echo "  [missing] $name (python -c 'import $module' failed)"
        missing=1
    fi
}

echo "Ab-initio (Quantum ESPRESSO + Wannier90):"
check_cmd "Quantum ESPRESSO pw.x" pw.x
check_cmd "Wannier90" wannier90.x

echo "Device transport (DEVSIM + Kwant):"
check_py_module "devsim" devsim
check_py_module "kwant" kwant

echo "Thermal (FEniCSx + HotSpot):"
check_py_module "dolfinx (FEniCSx)" dolfinx
if [ -x "$(dirname -- "$0")/../.vendor/hotspot/hotspot" ]; then
    echo "  [ok]      HotSpot (.vendor/hotspot/hotspot)"
else
    echo "  [missing] HotSpot (.vendor/hotspot/hotspot not built — run scripts/setup_env.sh)"
    missing=1
fi

echo "Thermal (Elmer, via Docker):"
if command -v docker >/dev/null 2>&1; then
    if docker image inspect quantum-foundry-elmer >/dev/null 2>&1; then
        echo "  [ok]      Elmer image (quantum-foundry-elmer)"
    elif command -v ElmerSolver >/dev/null 2>&1; then
        echo "  [ok]      ElmerSolver found on PATH (skipping Docker image)"
    else
        echo "  [missing] Elmer image not built — see docker/README.md"
        missing=1
    fi
else
    echo "  [missing] docker not found on PATH (needed for Elmer unless ElmerSolver is natively installed)"
    missing=1
fi

if [ "$missing" -ne 0 ]; then
    echo ""
    echo "One or more real-solver prerequisites are missing. Real-backend runs" >&2
    echo "will be refused. Run scripts/setup_env.sh, or use --backend stub." >&2
    exit 1
fi

echo ""
echo "All real-backend prerequisites present."
