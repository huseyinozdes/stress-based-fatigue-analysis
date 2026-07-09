from dataclasses import replace

from fatigue_model import (
    MATERIALS,
    STRAIN_LIFE_DEFAULTS,
    FatigueInput,
    StrainLifeInput,
    estimate_fatigue_life,
    estimate_strain_life,
)


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
        replace(
            base,
            axial_force_alt_n=base.axial_force_alt_n * 1.8,
            bending_moment_alt_nmm=base.bending_moment_alt_nmm * 1.8,
        )
    )

    if baseline.estimated_cycles is None:
        assert worse.estimated_cycles is not None or worse.sigma_alt_goodman_mpa > baseline.sigma_alt_goodman_mpa
    elif worse.estimated_cycles is not None:
        assert worse.estimated_cycles < baseline.estimated_cycles


def test_invalid_diameter_raises() -> None:
    bad = replace(_base_input(), diameter_mm=0.0)
    try:
        estimate_fatigue_life(bad)
    except ValueError as exc:
        assert "Diameter" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid diameter")


def _strain_input() -> StrainLifeInput:
    base = _base_input()
    defaults = STRAIN_LIFE_DEFAULTS[base.material.name]
    return StrainLifeInput(
        stress_input=base,
        elastic_modulus_mpa=defaults["elastic_modulus_mpa"],
        sigma_f_prime_mpa=defaults["sigma_f_prime_mpa"],
        epsilon_f_prime=defaults["epsilon_f_prime"],
        basquin_b=defaults["basquin_b"],
        coffin_c=defaults["coffin_c"],
        total_strain_amplitude=0.003,
    )


def test_strain_life_estimate_returns_positive_cycles_or_upper_regime() -> None:
    result = estimate_strain_life(_strain_input())
    assert result.sigma_alt_goodman_mpa > 0
    assert result.life_label
    if result.estimated_cycles is not None:
        assert result.estimated_cycles > 0


def test_higher_strain_amplitude_reduces_strain_life() -> None:
    base = _strain_input()
    baseline = estimate_strain_life(base)
    worse = estimate_strain_life(replace(base, total_strain_amplitude=base.total_strain_amplitude * 1.4))
    if baseline.estimated_cycles is not None and worse.estimated_cycles is not None:
        assert worse.estimated_cycles < baseline.estimated_cycles


def test_invalid_strain_constants_raise() -> None:
    bad = replace(_strain_input(), basquin_b=0.01)
    try:
        estimate_strain_life(bad)
    except ValueError as exc:
        assert "Basquin exponent b" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid strain-life constants")
