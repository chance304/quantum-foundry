from quantum_foundry.thermal.beol_budget import (
    BEOL_MAX_TEMP_C,
    M3D_LAYER_TRANSFER_MAX_TEMP_C,
    check_beol_budget,
    check_m3d_layer_transfer_budget,
)


def test_beol_check_passes_under_limit():
    check = check_beol_budget(350.0)
    assert check.passed is True
    assert check.limit_C == BEOL_MAX_TEMP_C
    assert check.margin_C == BEOL_MAX_TEMP_C - 350.0


def test_beol_check_fails_over_limit():
    check = check_beol_budget(450.0)
    assert check.passed is False
    assert check.margin_C < 0


def test_m3d_check_is_stricter_than_beol():
    # A temperature between the two limits passes BEOL but fails M3D.
    temp = 350.0
    assert check_beol_budget(temp).passed is True
    assert check_m3d_layer_transfer_budget(temp).passed is False
    assert M3D_LAYER_TRANSFER_MAX_TEMP_C < BEOL_MAX_TEMP_C
