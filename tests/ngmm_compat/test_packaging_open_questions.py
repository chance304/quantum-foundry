from quantum_foundry.ngmm_compat.packaging_open_questions import (
    packaging_compatibility_note,
)


def test_status_is_always_unresolved_open_question():
    note = packaging_compatibility_note("MoS2_monolayer", "MoS2")
    assert note["status"] == "unresolved_open_question"
    assert note["verified"] is False


def test_note_mentions_the_material_formula():
    note = packaging_compatibility_note("HfO2", "HfO2")
    assert "HfO2" in note["note"]


def test_bonding_processes_considered_is_a_list():
    note = packaging_compatibility_note("WSe2_monolayer", "WSe2")
    assert isinstance(note["bonding_processes_considered"], list)
    assert len(note["bonding_processes_considered"]) > 0


def test_unknown_material_falls_back_to_generic_note_not_a_crash():
    note = packaging_compatibility_note("Unobtainium_monolayer", "Ux")
    assert note["status"] == "unresolved_open_question"
    assert "Ux" in note["note"]
