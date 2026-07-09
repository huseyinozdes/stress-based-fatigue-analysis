from units import (
    ksi_to_mpa,
    lbfin_to_nm,
    mpa_to_ksi,
    mm_to_in,
    n_to_lbf,
    nm_to_lbfin,
    normalize_geometry_load_inputs,
)


def test_basic_si_to_imperial_conversions() -> None:
    assert abs(mm_to_in(25.4) - 1.0) < 1e-12
    assert abs(n_to_lbf(4.4482216152605) - 1.0) < 1e-12
    assert abs(nm_to_lbfin(1.0) - 8.8507457673787) < 1e-6
    assert abs(lbfin_to_nm(8.8507457673787) - 1.0) < 1e-6
    assert abs(mpa_to_ksi(6.894757293168361) - 1.0) < 1e-12
    assert abs(ksi_to_mpa(1.0) - 6.894757293168361) < 1e-12


def test_internal_normalization_matches_expected_si_base() -> None:
    normalized = normalize_geometry_load_inputs(
        "Imperial",
        diameter_value=0.5,
        axial_mean_value=449.618048,
        axial_alt_value=224.809024,
        moment_mean_value=88.507458,
        moment_alt_value=70.805966,
    )
    assert abs(normalized["diameter_mm"] - 12.7) < 1e-6
    assert abs(normalized["axial_force_mean_n"] - 2000.0) < 1e-3
    assert abs(normalized["axial_force_alt_n"] - 1000.0) < 1e-3
    assert abs(normalized["bending_moment_mean_nmm"] - 10_000.0) < 0.5
    assert abs(normalized["bending_moment_alt_nmm"] - 8_000.0) < 0.5


def test_si_normalization_preserves_si_units() -> None:
    normalized = normalize_geometry_load_inputs(
        "SI",
        diameter_value=12.0,
        axial_mean_value=2_000.0,
        axial_alt_value=1_000.0,
        moment_mean_value=10.0,
        moment_alt_value=8.0,
    )
    assert normalized["diameter_mm"] == 12.0
    assert normalized["axial_force_mean_n"] == 2_000.0
    assert normalized["axial_force_alt_n"] == 1_000.0
    assert normalized["bending_moment_mean_nmm"] == 10_000.0
    assert normalized["bending_moment_alt_nmm"] == 8_000.0
