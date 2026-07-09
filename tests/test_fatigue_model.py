from fatigue_model import MATERIALS, FatigueInput, estimate_fatigue_life


def _base_input() -> FatigueInput:
    return FatigueInput(
        material=MATERIALS["AISI 1045 steel (normalized)"],
        diameter_mm=12.0,
        axial_force_mean_n=2_000.0,
        axial_force_alt_n=1_000.0,
        bending_moment_mean_nmm=10_000.0,
        bending_moment_alt_nmm=8_000.0,
        surface_finish="Machined/Cold-drawn",
        reliability_percent=95,
        load_type="Bending",
        miscellaneous_factor=1.0,
    )


def test_estimate_returns_finite_or_infinite_life() -> None:
    result = estimate_fatigue_life(_base_input())
    assert result.sigma_alt_goodman_mpa > 0
    assert result.endurance_limit_mpa > 0
    assert result.life_label


def test_higher_alternating_load_reduces_life() -> None:
    base = _base_input()
    baseline = estimate_fatigue_life(base)
    worse = estimate_fatigue_life(
        FatigueInput(
            **{
                **base.__dict__,
                "axial_force_alt_n": base.axial_force_alt_n * 1.8,
                "bending_moment_alt_nmm": base.bending_moment_alt_nmm * 1.8,
            }
        )
    )

    if baseline.estimated_cycles is None:
        assert worse.estimated_cycles is not None or worse.sigma_alt_goodman_mpa > baseline.sigma_alt_goodman_mpa
    elif worse.estimated_cycles is not None:
        assert worse.estimated_cycles < baseline.estimated_cycles


def test_invalid_diameter_raises() -> None:
    bad = FatigueInput(
        **{
            **_base_input().__dict__,
            "diameter_mm": 0.0,
        }
    )
    try:
        estimate_fatigue_life(bad)
    except ValueError as exc:
        assert "Diameter" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid diameter")
