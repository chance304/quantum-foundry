"""Search the seeded 2D channel materials for the best n-type and p-type
candidates, and print each role's Pareto front.

    python examples/02_np_channel_search.py

Every candidate runs in *both* roles; nothing is assumed n-only or p-only.
When a front has more than one member there is a genuine trade-off, and no
single "recommended" material is reported.
"""
from quantum_foundry.orchestration.heterostructure import search

result = search()

for role, candidates, front, recommended in (
    ("n-type", result.n_candidates, result.n_pareto_front, result.recommended_n_material_id),
    ("p-type", result.p_candidates, result.p_pareto_front, result.recommended_p_material_id),
):
    print(f"=== {role} ===")
    for c in candidates:
        if c.pipeline_result is None:
            print(f"  {c.material_id:28s} excluded: {c.excluded_reason}")
    print("  Pareto front:", ", ".join(r.material.material_id for r in front) or "(empty)")
    print("  Recommended: ", recommended or "none: real trade-off, see the front above")
    print()
