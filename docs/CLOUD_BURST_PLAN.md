# Cloud Burst Plan: Ephemeral HPC Compute (Design Only)

*This is a design document, not an implementation — mirrors `docs/M5_PLAN.md`'s own framing exactly. Nothing here has been built; see `docs/ROADMAP.md` for real status. Written 2026-07-23, evaluating a proposal to run this project's future heavy solvers on on-demand, auto-destroying cloud infrastructure instead of a permanently-active cluster.*

## Is this the right fit? A real evaluation, not a rubber stamp

The proposed architecture — an orchestration layer that provisions cloud compute on demand, runs a containerized solver, stages data through object storage, and tears the infrastructure back down to zero — is a legitimate, well-established pattern for exactly this class of workload (bursty, expensive-if-idle HPC/AI jobs). It directly answers a tension already on record in this project's own Deployment & DevOps notes: a persistent HPC cluster is what M5 will eventually need, but nothing today justifies paying for one to sit idle. Burst-on-demand is the actual mechanism that makes "defer the cluster, don't pay for idle time" work in practice, not just a nice-sounding deferral.

**But nothing in this codebase needs it yet.** Every real backend verified so far — Kwant (NEGF transport), HotSpot (compact thermal), Poisson/Murphy/Stapper and the Monte Carlo yield engine — ran in seconds to under a minute on one ordinary machine, no GPU, no cluster, ever. The only two backends that would ever justify this architecture are both **M5, currently 0% implemented, design-only**: real Quantum ESPRESSO + Wannier90 ab-initio, and real FEniCSx/Elmer 3D FEA at production mesh scale.

**Decision: plan this now, build it when M5 starts.** Building orchestration, storage staging, and container images today — before the backends they'd wrap exist — would be infrastructure with nothing real to run, the same anti-pattern this project has deliberately avoided everywhere else (`docs/M5_PLAN.md` itself is "a design document, not an implementation," for exactly this reason).

## Layer 1: Orchestration — SkyPilot, not Pulumi

**Recommendation: SkyPilot.** Both are real, legitimate open-source tools, but they're shaped for different problems:

- **SkyPilot** is purpose-built for one-shot, bursty AI/HPC jobs: `sky launch`/`sky exec` with a task spec (CPU/GPU/memory requirements), automatic multi-cloud provider selection by cost/availability (AWS, GCP, Azure, Lambda Labs, RunPod, Nebius, ...), and native `autostop`/`autodown`. This matches "run one job on one ephemeral machine, then destroy it" directly, with no extra abstraction to carry.
- **Pulumi's** Automation API (`stack.up()`/`stack.destroy()`) is a general infrastructure-as-code engine, better suited to longer-lived, multi-resource infrastructure — a persistent service, a database, a queue. Quantum Foundry has none of those and isn't expected to; adopting Pulumi would mean carrying stack-state management for a shape of infrastructure this project doesn't have.

This is a real trade-off, not "Pulumi is worse" — if Quantum Foundry ever needs standing infrastructure (a results database, a job queue, a web dashboard), that calculus changes and Pulumi becomes the better fit. Revisit if that ever happens; it's genuinely not the case today.

## Which stages actually trigger this — not a blanket "cloud-ify everything" call

| Stage | Backend | Needs cloud burst? |
|---|---|---|
| DFT | Quantum ESPRESSO + Wannier90 (M5, not built) | **Yes** — real ab-initio sweeps across a materials library are the textbook case for this |
| Thermal/Mechanical | FEniCSx + Elmer at production mesh scale (M5, not built) | **Yes** — a real GAA/CFET 3D mesh is thousands to millions of DOF; Kwant's own analog already hit a hard tractability wall (~4,000 sites) on one machine |
| Transport | Kwant (real, verified) | No — proven fine locally at toy scale, seconds per run |
| Transport | DEVSIM (blocked in this sandbox) | No — needs working BLAS/LAPACK, not more compute; a real conda environment fixes this, not a cluster |
| Manufacturability | Monte Carlo yield (real, verified) | No — the Binomial-sampling fix (`manufacturability/monte_carlo.py`, closed this session) made this cheap local math regardless of `n_runs`/`n_dies`, no per-die array |

## Integration point: `orchestration/config.py`'s existing seam

`StageConfig(backend: str, params: dict)` already selects a backend per stage via each layer's `get_backend()` registry (stub vs. `kwant` vs., eventually, `qe_wannier`). A cloud-burst execution mode is an **orthogonal axis** to that — which backend runs vs. where it physically executes are two different questions. The natural extension point, when M5 actually needs it, is a new field:

```python
@dataclass
class StageConfig:
    backend: str
    params: dict[str, Any] = field(default_factory=dict)
    execution: str = "local"  # "local" | "cloud_burst" -- NOT added yet, see below
```

**Deliberately not added in this plan.** There's no cloud-burst-capable backend yet for it to select — adding the field now would be the same premature-schema problem this plan otherwise avoids. Add it at M5 implementation time, alongside the first real backend that actually uses it.

## Storage staging already has a real hook — not a new system

`dft/results.py`'s `TightBindingHandle` and `thermal/results.py`'s `FieldHandle` were both designed from day one with:

```python
format: str            # e.g. "wannier90_hr", "xdmf_hdf5"
path: Path | None
loader: Callable[[], Any]
```

— exactly "this data might not be inline, fetch it lazily" already. An S3-backed cloud-burst result is a direct extension of this existing pattern: `path` becomes an `s3://bucket/jobs/{job_id}/output/...` URI instead of a local filesystem path, and `loader` does the actual fetch (e.g. via `boto3` or an `fsspec`-style client) instead of a local file read. This is not new architecture bolted on top — it's the extension the schema was already shaped for.

Input staging (crystal geometries, mesh parameters, boundary conditions) follows the same shape in reverse: upload before the job starts, referenced by the same kind of path.

## Containerization prerequisite — the actual current gap

QE+Wannier90 and FEniCSx currently install via `environment.yml` (conda-forge), not containers. Elmer has a **scaffolded, unbuilt** `docker/elmer.Dockerfile` — closest to ready, but never built or run against a real solve (`docker/README.md`'s own status note). Real Docker/Apptainer images for QE and FEniCSx don't exist yet, and building them before the real backend code they'd wrap exists would mean containerizing nothing — this is sequencing, not an oversight. The real order is: M5 backend code first, then a real (built, tested) container image, then cloud-burst orchestration around it.

## Safety guardrails — mapped to what's actually relevant here

- **Dead-man's-switch / TTL watchdog:** SkyPilot's native `autostop` (and `autodown`) flag covers this directly — no custom daemon needed.
- **Spot/preemptible + checkpointing:** matters specifically for QE sweeps across a materials library — a real, embarrassingly-parallel-shaped workload where losing one instance mid-sweep shouldn't lose the whole run. Does **not** matter for Monte Carlo yield anymore — the Binomial-sampling fix already made that cheap enough to just rerun locally.
- **Hard budget caps via IAM policies:** a real, provider-agnostic safeguard worth having regardless of SkyPilot vs. Pulumi — independent of this decision, should be in place before any real cloud spend happens at all.

## Explicit trigger

**Build this when M5's real Quantum ESPRESSO + Wannier90 implementation starts — not before, not "just in case."**

## Explicit non-scope for this plan

Not done as part of writing this document, deliberately:
- No new dependency installed (`skypilot`, `boto3`, etc.) — same up-front-flag treatment `jarvis-tools` got before it was installed.
- No containers built for QE or FEniCSx.
- No `StageConfig.execution` field added to the real schema yet.
- No cloud credentials, IAM policies, or budget caps configured — there's nothing to spend on yet.
