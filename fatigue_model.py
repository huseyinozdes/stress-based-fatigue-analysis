from __future__ import annotations

from dataclasses import dataclass
from math import log10, pi


@dataclass(frozen=True)
class Material:
    name: str
    sut_mpa: float
    sy_mpa: float


@dataclass(frozen=True)
class FatigueInput:
    material: Material
    diameter_mm: float
    axial_force_mean_n: float
    axial_force_alt_n: float
    bending_moment_mean_nmm: float
    bending_moment_alt_nmm: float
    surface_finish: str
    reliability_percent: int
    load_type: str
    miscellaneous_factor: float = 1.0


@dataclass(frozen=True)
class FatigueResult:
    area_mm2: float
    sigma_mean_mpa: float
    sigma_alt_mpa: float
    sigma_alt_goodman_mpa: float
    endurance_limit_prime_mpa: float
    endurance_limit_mpa: float
    marin_ka: float
    marin_kb: float
    marin_kc: float
    marin_ke: float
    basquin_a: float
    basquin_b: float
    estimated_cycles: float | None
    life_label: str
    notes: list[str]


@dataclass(frozen=True)
class StressState:
    area_mm2: float
    sigma_mean_mpa: float
    sigma_alt_mpa: float
    sigma_max_mpa: float


@dataclass(frozen=True)
class StrainLifeInput:
    stress_input: FatigueInput
    elastic_modulus_mpa: float
    sigma_f_prime_mpa: float
    epsilon_f_prime: float
    basquin_b: float
    coffin_c: float
    total_strain_amplitude: float


@dataclass(frozen=True)
class StrainLifeResult:
    stress_state: StressState
    sigma_alt_goodman_mpa: float
    estimated_cycles: float | None
    life_label: str
    elastic_strain_component: float
    plastic_strain_component: float
    notes: list[str]


SURFACE_FINISH_COEFFICIENTS: dict[str, tuple[float, float]] = {
    "Ground": (1.58, -0.085),
    "Machined/Cold-drawn": (4.51, -0.265),
    "Hot-rolled": (57.7, -0.718),
    "As-forged": (272.0, -0.995),
}

LOAD_FACTOR: dict[str, float] = {
    "Bending": 1.0,
    "Axial": 0.85,
}

RELIABILITY_FACTOR: dict[int, float] = {
    50: 1.000,
    90: 0.897,
    95: 0.868,
    99: 0.814,
    99_9: 0.753,
}

MATERIALS: dict[str, Material] = {
    "AISI 1045 steel (normalized)": Material("AISI 1045 steel (normalized)", sut_mpa=625.0, sy_mpa=530.0),
    "AISI 4140 steel (quenched & tempered)": Material(
        "AISI 4140 steel (quenched & tempered)",
        sut_mpa=1020.0,
        sy_mpa=655.0,
    ),
    "Al 6061-T6": Material("Al 6061-T6", sut_mpa=310.0, sy_mpa=276.0),
}

STRAIN_LIFE_DEFAULTS: dict[str, dict[str, float]] = {
    "AISI 1045 steel (normalized)": {
        "elastic_modulus_mpa": 205_000.0,
        "sigma_f_prime_mpa": 980.0,
        "epsilon_f_prime": 0.47,
        "basquin_b": -0.089,
        "coffin_c": -0.58,
    },
    "AISI 4140 steel (quenched & tempered)": {
        "elastic_modulus_mpa": 210_000.0,
        "sigma_f_prime_mpa": 1500.0,
        "epsilon_f_prime": 0.26,
        "basquin_b": -0.095,
        "coffin_c": -0.59,
    },
    "Al 6061-T6": {
        "elastic_modulus_mpa": 69_000.0,
        "sigma_f_prime_mpa": 450.0,
        "epsilon_f_prime": 0.32,
        "basquin_b": -0.085,
        "coffin_c": -0.62,
    },
}


def _validate_inputs(inputs: FatigueInput) -> None:
    if inputs.diameter_mm <= 0:
        raise ValueError("Diameter must be > 0 mm.")
    if inputs.reliability_percent not in RELIABILITY_FACTOR:
        raise ValueError("Unsupported reliability level.")
    if inputs.surface_finish not in SURFACE_FINISH_COEFFICIENTS:
        raise ValueError("Unsupported surface finish.")
    if inputs.load_type not in LOAD_FACTOR:
        raise ValueError("Unsupported load type.")
    if inputs.miscellaneous_factor <= 0:
        raise ValueError("Miscellaneous Marin factor must be > 0.")


def _validate_strain_inputs(inputs: StrainLifeInput) -> None:
    if inputs.elastic_modulus_mpa <= 0:
        raise ValueError("Elastic modulus E must be > 0 MPa.")
    if inputs.sigma_f_prime_mpa <= 0:
        raise ValueError("Fatigue strength coefficient sigma_f' must be > 0 MPa.")
    if inputs.epsilon_f_prime <= 0:
        raise ValueError("Fatigue ductility coefficient epsilon_f' must be > 0.")
    if inputs.total_strain_amplitude <= 0:
        raise ValueError("Total strain amplitude must be > 0 (strain, mm/mm).")
    if inputs.total_strain_amplitude >= 1.0:
        raise ValueError("Total strain amplitude must be < 1.0 (strain, mm/mm).")
    if inputs.basquin_b >= 0:
        raise ValueError("Basquin exponent b must be negative.")
    if inputs.coffin_c >= 0:
        raise ValueError("Coffin-Manson exponent c must be negative.")


def _endurance_limit_prime(sut_mpa: float) -> float:
    if sut_mpa <= 1400:
        return 0.5 * sut_mpa
    return 700.0


def _surface_factor(sut_mpa: float, finish: str) -> float:
    a, b = SURFACE_FINISH_COEFFICIENTS[finish]
    return a * (sut_mpa**b)


def _size_factor(diameter_mm: float) -> tuple[float, str | None]:
    if 2.79 <= diameter_mm <= 51.0:
        return (diameter_mm / 7.62) ** -0.107, None
    if 51.0 < diameter_mm <= 254.0:
        return 1.51 * (diameter_mm**-0.157), None
    return 1.0, "Diameter outside common Marin size-correlation range (2.79-254 mm); kb set to 1.0."


def _section_area_mm2(diameter_mm: float) -> float:
    return pi * (diameter_mm**2) / 4.0


def _bending_stress_mpa(moment_nmm: float, diameter_mm: float) -> float:
    return (32.0 * moment_nmm) / (pi * (diameter_mm**3))


def _axial_stress_mpa(force_n: float, area_mm2: float) -> float:
    return force_n / area_mm2


def evaluate_stress_state(inputs: FatigueInput) -> StressState:
    _validate_inputs(inputs)
    area = _section_area_mm2(inputs.diameter_mm)
    sigma_mean = _axial_stress_mpa(inputs.axial_force_mean_n, area) + _bending_stress_mpa(
        inputs.bending_moment_mean_nmm,
        inputs.diameter_mm,
    )
    sigma_alt = _axial_stress_mpa(inputs.axial_force_alt_n, area) + _bending_stress_mpa(
        inputs.bending_moment_alt_nmm,
        inputs.diameter_mm,
    )
    sigma_mean = max(sigma_mean, 0.0)
    sigma_alt = max(sigma_alt, 0.0)
    return StressState(
        area_mm2=area,
        sigma_mean_mpa=sigma_mean,
        sigma_alt_mpa=sigma_alt,
        sigma_max_mpa=sigma_mean + sigma_alt,
    )


def estimate_fatigue_life(inputs: FatigueInput) -> FatigueResult:
    notes: list[str] = []
    stress_state = evaluate_stress_state(inputs)
    sigma_mean = stress_state.sigma_mean_mpa
    sigma_alt = stress_state.sigma_alt_mpa

    sut = inputs.material.sut_mpa
    sy = inputs.material.sy_mpa
    if sigma_mean >= sut:
        raise ValueError("Mean stress is >= Sut. Goodman correction is not valid in this region.")

    se_prime = _endurance_limit_prime(sut)
    ka = _surface_factor(sut, inputs.surface_finish)
    kb, size_note = _size_factor(inputs.diameter_mm)
    kc = LOAD_FACTOR[inputs.load_type]
    ke = RELIABILITY_FACTOR[inputs.reliability_percent]
    if size_note:
        notes.append(size_note)
    se = se_prime * ka * kb * kc * ke * inputs.miscellaneous_factor

    sigma_alt_goodman = sigma_alt / (1.0 - sigma_mean / sut)
    if stress_state.sigma_max_mpa > sy:
        notes.append("Peak normal stress exceeds yield strength; estimate may be non-conservative.")

    b = (log10(se) - log10(0.9 * sut)) / 3.0
    a = (0.9 * sut) / ((10.0**3) ** b)

    estimated_cycles: float | None
    life_label: str
    if sigma_alt_goodman <= se:
        estimated_cycles = None
        life_label = "Infinite-life regime (>= 1e6 cycles, stress below corrected endurance limit)."
    elif sigma_alt_goodman >= 0.9 * sut:
        estimated_cycles = 1_000.0
        life_label = "Low-cycle/high-stress regime (<= 1e3 cycles)."
    else:
        estimated_cycles = (sigma_alt_goodman / a) ** (1.0 / b)
        life_label = "Finite-life regime (Basquin estimate)."

    notes.append("Model assumes uniaxial nominal stress on a round section with linear-elastic behavior.")
    notes.append("No notch sensitivity, residual stress, corrosion, or variable-amplitude loading effects are included.")

    return FatigueResult(
        area_mm2=stress_state.area_mm2,
        sigma_mean_mpa=sigma_mean,
        sigma_alt_mpa=sigma_alt,
        sigma_alt_goodman_mpa=sigma_alt_goodman,
        endurance_limit_prime_mpa=se_prime,
        endurance_limit_mpa=se,
        marin_ka=ka,
        marin_kb=kb,
        marin_kc=kc,
        marin_ke=ke,
        basquin_a=a,
        basquin_b=b,
        estimated_cycles=estimated_cycles,
        life_label=life_label,
        notes=notes,
    )


def _strain_life_value(
    reversals: float,
    sigma_f_prime_mpa: float,
    elastic_modulus_mpa: float,
    epsilon_f_prime: float,
    basquin_b: float,
    coffin_c: float,
    sigma_mean_mpa: float,
) -> tuple[float, float, float]:
    elastic = max(sigma_f_prime_mpa - sigma_mean_mpa, 0.0) / elastic_modulus_mpa * (reversals**basquin_b)
    plastic = epsilon_f_prime * (reversals**coffin_c)
    return elastic + plastic, elastic, plastic


def estimate_strain_life(inputs: StrainLifeInput) -> StrainLifeResult:
    _validate_inputs(inputs.stress_input)
    _validate_strain_inputs(inputs)

    notes: list[str] = []
    stress_state = evaluate_stress_state(inputs.stress_input)
    sigma_mean = stress_state.sigma_mean_mpa
    sigma_alt = stress_state.sigma_alt_mpa
    sut = inputs.stress_input.material.sut_mpa

    if sigma_mean >= sut:
        raise ValueError("Mean stress is >= Sut. Goodman correction is not valid in this region.")
    if sigma_mean >= inputs.sigma_f_prime_mpa:
        raise ValueError("Mean stress must be below sigma_f' for Morrow-corrected strain-life.")

    sigma_alt_goodman = sigma_alt / (1.0 - sigma_mean / sut)
    target = inputs.total_strain_amplitude

    lower_reversals = 1.0
    upper_reversals = 1.0e14
    lower_value, _, _ = _strain_life_value(
        lower_reversals,
        inputs.sigma_f_prime_mpa,
        inputs.elastic_modulus_mpa,
        inputs.epsilon_f_prime,
        inputs.basquin_b,
        inputs.coffin_c,
        sigma_mean,
    )
    upper_value, _, _ = _strain_life_value(
        upper_reversals,
        inputs.sigma_f_prime_mpa,
        inputs.elastic_modulus_mpa,
        inputs.epsilon_f_prime,
        inputs.basquin_b,
        inputs.coffin_c,
        sigma_mean,
    )

    estimated_cycles: float | None
    life_label: str
    if target >= lower_value:
        estimated_cycles = 0.5
        life_label = "Very-low-cycle regime (<= 1 cycle, high imposed strain amplitude)."
        notes.append("Input strain amplitude exceeds the modeled value at 2N=1 reversal.")
        _, elastic_component, plastic_component = _strain_life_value(
            lower_reversals,
            inputs.sigma_f_prime_mpa,
            inputs.elastic_modulus_mpa,
            inputs.epsilon_f_prime,
            inputs.basquin_b,
            inputs.coffin_c,
            sigma_mean,
        )
    elif target <= upper_value:
        estimated_cycles = None
        life_label = "Very-high-cycle regime (beyond solver upper bound, >5e13 cycles)."
        _, elastic_component, plastic_component = _strain_life_value(
            upper_reversals,
            inputs.sigma_f_prime_mpa,
            inputs.elastic_modulus_mpa,
            inputs.epsilon_f_prime,
            inputs.basquin_b,
            inputs.coffin_c,
            sigma_mean,
        )
        notes.append("Predicted life exceeds the configured epsilon-N search range.")
    else:
        lo = lower_reversals
        hi = upper_reversals
        for _ in range(80):
            mid = (lo + hi) / 2.0
            mid_value, _, _ = _strain_life_value(
                mid,
                inputs.sigma_f_prime_mpa,
                inputs.elastic_modulus_mpa,
                inputs.epsilon_f_prime,
                inputs.basquin_b,
                inputs.coffin_c,
                sigma_mean,
            )
            if mid_value > target:
                lo = mid
            else:
                hi = mid

        reversals = (lo + hi) / 2.0
        estimated_cycles = reversals / 2.0
        life_label = "Finite-life regime (Manson-Coffin-Basquin estimate)."
        _, elastic_component, plastic_component = _strain_life_value(
            reversals,
            inputs.sigma_f_prime_mpa,
            inputs.elastic_modulus_mpa,
            inputs.epsilon_f_prime,
            inputs.basquin_b,
            inputs.coffin_c,
            sigma_mean,
        )

    notes.append("Strain-life uses Manson-Coffin-Basquin with Morrow mean-stress correction in elastic term.")
    notes.append("Assumes stabilized strain amplitude and constant-amplitude cycling.")
    notes.append("No notch strain concentration, multiaxiality, or sequence effects are included.")

    return StrainLifeResult(
        stress_state=stress_state,
        sigma_alt_goodman_mpa=sigma_alt_goodman,
        estimated_cycles=estimated_cycles,
        life_label=life_label,
        elastic_strain_component=elastic_component,
        plastic_strain_component=plastic_component,
        notes=notes,
    )
