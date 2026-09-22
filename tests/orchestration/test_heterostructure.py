from quantum_foundry.orchestration.heterostructure import (
    _CHANNEL_CANDIDATE_MATERIAL_IDS,
    search,
)

# 2026-07-28: WSe2 gained a real, cited electron mass (Kormanyos et al.
# 2015, cross-checked against Shi et al. 2013) after its previous JVASP-652
# value (105.23 m0) was confirmed anomalous, and MoTe2/WTe2 gained full
# real C2DB-sourced data (previously all-null placeholders, confirmed
# absent from JARVIS-DFT). All three moved from "incomplete"/"p-role only"
# into "complete both roles" -- see docs/DECISIONS.md. black_phosphorus and
# graphene remain genuinely incomplete (anisotropic/gapless, don't reduce
# to this schema's scalar effective-mass fields).
_COMPLETE_BOTH_ROLES = {
    "MoS2_monolayer",
    "WS2_monolayer",
    "WSe2_monolayer",
    "MoTe2_monolayer",
    "WTe2_monolayer",
}
_INCOMPLETE_BOTH_ROLES = set(_CHANNEL_CANDIDATE_MATERIAL_IDS) - _COMPLETE_BOTH_ROLES


def test_search_runs_without_error():
    result = search()
    assert len(result.n_candidates) == len(_CHANNEL_CANDIDATE_MATERIAL_IDS)
    assert len(result.p_candidates) == len(_CHANNEL_CANDIDATE_MATERIAL_IDS)


def test_materials_with_complete_data_succeed_in_both_roles():
    result = search()
    for candidates in (result.n_candidates, result.p_candidates):
        by_id = {c.material_id: c for c in candidates}
        for material_id in _COMPLETE_BOTH_ROLES:
            assert by_id[material_id].excluded_reason is None
            assert by_id[material_id].pipeline_result is not None


def test_materials_with_incomplete_data_are_excluded_with_a_real_reason():
    # Never silently dropped -- every incomplete-data candidate must still
    # appear in the candidate list, just with excluded_reason set.
    result = search()
    for candidates in (result.n_candidates, result.p_candidates):
        by_id = {c.material_id: c for c in candidates}
        for material_id in _INCOMPLETE_BOTH_ROLES:
            assert material_id in by_id
            assert by_id[material_id].pipeline_result is None
            assert by_id[material_id].excluded_reason
            assert len(by_id[material_id].excluded_reason) > 0


def test_pareto_fronts_are_nonempty_and_contain_only_successful_candidates():
    result = search()
    for front, candidates in (
        (result.n_pareto_front, result.n_candidates),
        (result.p_pareto_front, result.p_candidates),
    ):
        assert len(front) > 0
        successes = {id(c.pipeline_result) for c in candidates if c.pipeline_result is not None}
        assert all(id(r) in successes for r in front)


def test_recommendation_is_none_or_a_material_on_the_front():
    result = search()
    for recommended, front in (
        (result.recommended_n_material_id, result.n_pareto_front),
        (result.recommended_p_material_id, result.p_pareto_front),
    ):
        if recommended is not None:
            assert recommended in {r.material.material_id for r in front}
            assert len(front) == 1
        else:
            assert len(front) != 1
