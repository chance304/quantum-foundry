#!/bin/sh
# One-time setup of a GitHub Actions self-hosted runner on a persistent
# machine you control (NOT this repo's dev sandbox, NOT a cloud VPS --
# your own always-on or on-demand machine, per the 2026-07-21 decision to
# run CI locally, see docs/DECISIONS.md).
#
# Usage: scripts/setup_github_runner.sh <registration-token> [runner-name]
#
# Get <registration-token> from: repo Settings -> Actions -> Runners ->
# New self-hosted runner. Tokens expire ~1 hour after being issued -- fetch
# a fresh one right before running this script, never hardcode or commit it.
set -eu

TOKEN="${1:?Usage: $0 <registration-token> [runner-name]}"
RUNNER_NAME="${2:-quantum-foundry-runner}"
REPO_URL="https://github.com/chance304/quantum-foundry"
RUNNER_DIR="$HOME/actions-runner"
# Verify the latest release at https://github.com/actions/runner/releases
# before relying on this pinned version -- re-check periodically.
RUNNER_VERSION="2.319.1"

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo "Downloading GitHub Actions runner v${RUNNER_VERSION}..."
curl -o actions-runner.tar.gz -L \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
tar xzf actions-runner.tar.gz

echo "Registering runner with label 'quantum-foundry' (matches ci.yml's runs-on)..."
./config.sh --url "$REPO_URL" --token "$TOKEN" \
    --name "$RUNNER_NAME" --labels quantum-foundry,linux,self-hosted --unattended

echo "Installing as a systemd service, running as $(whoami) (NOT root --"
echo "the service needs to run as whichever user owns the conda environment)..."
sudo ./svc.sh install "$(whoami)"
sudo ./svc.sh start

cat <<'EOF'

Runner registered and started as a systemd service.

IMPORTANT: systemd services do NOT source ~/.bashrc, so conda/mamba's shell
integration is not automatically available to the service. ci.yml's
`real-solvers` job sets `shell: bash -l {0}` (a login shell) as its default
for exactly this reason -- that's what makes `conda run`/`conda activate`
actually find the environment in each workflow step. Do not remove that
`defaults: run: shell:` block from ci.yml.

Next steps:
  1. Run scripts/setup_env.sh on THIS machine to create the conda
     environment and vendor HotSpot (if not already done).
  2. Run scripts/preflight.sh to confirm all real-backend prerequisites are
     actually present before the first CI run depends on them.
  3. Push to main or open a PR to trigger ci.yml's real-solvers job and
     confirm it picks up this runner (check the Actions tab -- the job
     should show as running on a self-hosted runner, not ubuntu-latest).

To check the runner service status later: sudo ./svc.sh status
To stop it: sudo ./svc.sh stop
EOF
