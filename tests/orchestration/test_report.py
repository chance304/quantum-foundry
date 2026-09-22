from quantum_foundry.orchestration.heterostructure import search
from quantum_foundry.orchestration.report import render_ppa_y_markdown


def test_render_ppa_y_markdown_includes_every_candidate():
    result = search()
    md = render_ppa_y_markdown(result)

    assert "# PPA-Y Pareto-Matrix Report" in md
    assert "## n-type role" in md
    assert "## p-type role" in md
    # Never silently drops a candidate, matching heterostructure.py's own
    # discipline -- every material_id (n and p role) must appear.
    for c in result.n_candidates + result.p_candidates:
        assert c.material_id in md


def test_render_ppa_y_markdown_marks_pareto_front_membership():
    result = search()
    md = render_ppa_y_markdown(result)
    front_material_ids = {r.material.material_id for r in result.n_pareto_front}
    assert front_material_ids, "expected at least one n-role pareto-front member"
    for c in result.n_candidates:
        if c.pipeline_result is not None and c.material_id in front_material_ids:
            row = next(line for line in md.splitlines() if line.startswith(c.material_id))
            assert "| yes |" in row


def test_render_ppa_y_markdown_shows_excluded_reason():
    result = search()
    md = render_ppa_y_markdown(result)
    excluded = [c for c in result.n_candidates if c.pipeline_result is None]
    assert excluded, "expected at least one excluded n-role candidate in the real materials DB"
    for c in excluded:
        assert c.excluded_reason in md
