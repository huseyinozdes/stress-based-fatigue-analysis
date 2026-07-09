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


def estimate_fatigue_life(inputs: FatigueInput) -> FatigueResult:
    _validate_inputs(inputs)

    notes: list[str] = []
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
    sigma_max = sigma_mean + sigma_alt
    if sigma_max > sy:
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
        area_mm2=area,
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
