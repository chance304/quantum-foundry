# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub's
[private vulnerability reporting](https://github.com/chance304/quantum-foundry/security/advisories/new)
(Security tab → "Report a vulnerability"). Include what you found, how to
reproduce it and the impact you expect. You should get an acknowledgement
within 7 days.

## Scope

In scope: the `quantum_foundry` package, its CLI, the CI workflows and the
setup scripts in `scripts/`. Vulnerabilities in the external solvers
Quantum Foundry drives (Kwant, DEVSIM, gmsh, Elmer, HotSpot, Quantum
ESPRESSO and others) should be reported to those projects directly.

## Supported versions

Only the latest release on `main` receives security fixes.
