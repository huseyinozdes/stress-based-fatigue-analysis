from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log, log10, pi
import re


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


@dataclass(frozen=True)
class WeibullObservation:
    cycles: float
    failed: bool


@dataclass(frozen=True)
class WeibullResult:
    beta_shape: float
    eta_scale_cycles: float
    b10_cycles: float
    b50_cycles: float
    survival_at_target: float
    target_cycles: float
    sample_count: int
    failure_count: int
    censored_count: int
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
    "Ti-6Al-4V (annealed)": Material("Ti-6Al-4V (annealed)", sut_mpa=950.0, sy_mpa=880.0),
    "AISI 304 stainless (annealed)": Material("AISI 304 stainless (annealed)", sut_mpa=515.0, sy_mpa=205.0),
    "Al 7075-T6": Material("Al 7075-T6", sut_mpa=572.0, sy_mpa=503.0),
    "EN-GJL-250 gray cast iron": Material("EN-GJL-250 gray cast iron", sut_mpa=250.0, sy_mpa=165.0),
    "AISI 1020 steel (hot-rolled)": Material("AISI 1020 steel (hot-rolled)", sut_mpa=380.0, sy_mpa=210.0),
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
    "Ti-6Al-4V (annealed)": {
        "elastic_modulus_mpa": 114_000.0,
        "sigma_f_prime_mpa": 1500.0,
        "epsilon_f_prime": 0.80,
        "basquin_b": -0.095,
        "coffin_c": -0.69,
    },
    "AISI 304 stainless (annealed)": {
        "elastic_modulus_mpa": 193_000.0,
        "sigma_f_prime_mpa": 1000.0,
        "epsilon_f_prime": 0.17,
        "basquin_b": -0.12,
        "coffin_c": -0.45,
    },
    "Al 7075-T6": {
        "elastic_modulus_mpa": 71_700.0,
        "sigma_f_prime_mpa": 740.0,
        "epsilon_f_prime": 0.19,
        "basquin_b": -0.106,
        "coffin_c": -0.60,
    },
    "EN-GJL-250 gray cast iron": {
        "elastic_modulus_mpa": 100_000.0,
        "sigma_f_prime_mpa": 440.0,
        "epsilon_f_prime": 0.01,
        "basquin_b": -0.12,
        "coffin_c": -0.60,
    },
    "AISI 1020 steel (hot-rolled)": {
        "elastic_modulus_mpa": 200_000.0,
        "sigma_f_prime_mpa": 620.0,
        "epsilon_f_prime": 0.59,
        "basquin_b": -0.081,
        "coffin_c": -0.56,
    },
}

MATERIAL_USE_CASES: dict[str, tuple[str, ...]] = {
    "AISI 1045 steel (normalized)": (
        "Shafts, axles, and crankshafts in automotive drivetrains",
        "Structural bolts and high-cycle rotating machine components",
        "Agricultural and construction equipment gears",
    ),
    "AISI 4140 steel (quenched & tempered)": (
        "Aircraft landing gear, oil-country drill collars, and tooling spindles",
        "High-load automotive and motorsport connecting rods",
        "Hydraulic cylinder rods and precision shafts under combined loading",
    ),
    "Al 6061-T6": (
        "Aerospace frames, bicycle frames, and marine structural extrusions",
        "Automotive suspension components where weight reduction is critical",
        "Electronic enclosures and machined fixtures requiring good corrosion resistance",
    ),
    "Ti-6Al-4V (annealed)": (
        "Jet engine compressor blades and aerospace primary structures",
        "Orthopedic implants and surgical instrumentation (biocompatible)",
        "High-performance motorsport and offshore structural fasteners",
    ),
    "AISI 304 stainless (annealed)": (
        "Chemical process piping, pressure vessels, and food-grade equipment",
        "Marine hardware and coastal architectural structures",
        "Pharmaceutical and biomedical devices where sterilisability is required",
    ),
    "Al 7075-T6": (
        "Wing spars, bulkheads, and aircraft structural skins",
        "High-performance bicycle and motorsport chassis components",
        "Precision mold tooling and jigs where strength-to-weight is paramount",
    ),
    "EN-GJL-250 gray cast iron": (
        "Lathe beds, milling machine columns, and large press frames requiring vibration damping",
        "Engine blocks, cylinder heads, and exhaust manifolds in heavy machinery",
        "Hydraulic valve bodies and pump housings in industrial fluid systems",
    ),
    "AISI 1020 steel (hot-rolled)": (
        "Welded structural frames, brackets, and general fabrications",
        "Low-stress shafts, pins, and keystock in light-duty machinery",
        "Automotive body stampings and domestic appliance structural panels",
    ),
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


_FAIL_TOKENS = {"f", "fail", "failed", "failure", "1"}
_RUNOUT_TOKENS = {"r", "runout", "run-out", "c", "censored", "survived", "s", "0"}


def parse_weibull_observations(text: str) -> list[WeibullObservation]:
    observations: list[WeibullObservation] = []
    lines = text.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = [t for t in re.split(r"[,;\t ]+", line) if t]
        if len(tokens) < 2:
            raise ValueError(f"Line {idx}: expected '<cycles> <status>'.")
        try:
            cycles = float(tokens[0])
        except ValueError as exc:
            raise ValueError(f"Line {idx}: invalid cycle count '{tokens[0]}'.") from exc
        if cycles <= 0:
            raise ValueError(f"Line {idx}: cycles must be > 0.")

        status = tokens[1].lower()
        if status in _FAIL_TOKENS:
            failed = True
        elif status in _RUNOUT_TOKENS:
            failed = False
        else:
            raise ValueError(
                f"Line {idx}: status '{tokens[1]}' must be fail/failed/f or runout/censored/r."
            )
        observations.append(WeibullObservation(cycles=cycles, failed=failed))

    if not observations:
        raise ValueError("No Weibull observations provided.")
    return observations


def _validate_weibull_observations(observations: list[WeibullObservation]) -> None:
    if len(observations) < 3:
        raise ValueError("At least 3 observations are required for Weibull fitting.")
    failures = [obs for obs in observations if obs.failed]
    if len(failures) < 2:
        raise ValueError("At least 2 failed observations are required for two-parameter Weibull fitting.")
    if any(obs.cycles <= 0 for obs in observations):
        raise ValueError("All Weibull cycles must be > 0.")


def _safe_log_sum_exp(beta: float, cycles_values: list[float]) -> float:
    ln_cycles = [log(c) for c in cycles_values]
    max_ln = max(ln_cycles)
    scaled_sum = sum(exp(beta * (ln_c - max_ln)) for ln_c in ln_cycles)
    return beta * max_ln + log(scaled_sum)


def _weibull_profile_log_likelihood(beta: float, failures: list[float], all_cycles: list[float]) -> float:
    if beta <= 0 or not isfinite(beta):
        return float("-inf")
    r = len(failures)
    sum_fail_ln = sum(log(x) for x in failures)
    ln_a = _safe_log_sum_exp(beta, all_cycles)
    ln_r = log(r)
    # Profile log-likelihood after substituting eta^beta = A/r where A = sum(t_i^beta) over all (failed + censored).
    return r * log(beta) - r * (ln_a - ln_r) + (beta - 1.0) * sum_fail_ln - r


def _estimate_weibull_beta(failures: list[float], all_cycles: list[float]) -> float:
    lo = 0.2
    hi = 20.0
    gr = (5**0.5 - 1.0) / 2.0

    c = hi - gr * (hi - lo)
    d = lo + gr * (hi - lo)
    fc = _weibull_profile_log_likelihood(c, failures, all_cycles)
    fd = _weibull_profile_log_likelihood(d, failures, all_cycles)

    for _ in range(120):
        if fc > fd:
            hi = d
            d = c
            fd = fc
            c = hi - gr * (hi - lo)
            fc = _weibull_profile_log_likelihood(c, failures, all_cycles)
        else:
            lo = c
            c = d
            fc = fd
            d = lo + gr * (hi - lo)
            fd = _weibull_profile_log_likelihood(d, failures, all_cycles)

    beta = (lo + hi) / 2.0
    if beta <= 0 or not isfinite(beta):
        raise ValueError("Weibull MLE did not converge to a valid beta.")
    if beta < 0.201 or beta > 19.99:
        raise ValueError("Weibull MLE reached parameter bounds; data may be insufficient or ill-conditioned.")
    return beta


def _weibull_eta(beta: float, failures: list[float], all_cycles: list[float]) -> float:
    r = len(failures)
    ln_a = _safe_log_sum_exp(beta, all_cycles)
    ln_eta = (ln_a - log(r)) / beta
    eta = exp(ln_eta)
    if eta <= 0 or not isfinite(eta):
        raise ValueError("Weibull MLE did not converge to a valid eta.")
    return eta


def weibull_survival_probability(cycles: float, beta_shape: float, eta_scale_cycles: float) -> float:
    if cycles < 0:
        raise ValueError("Cycles must be >= 0.")
    if beta_shape <= 0 or eta_scale_cycles <= 0:
        raise ValueError("Invalid Weibull parameters.")
    if cycles == 0:
        return 1.0
    exponent = (cycles / eta_scale_cycles) ** beta_shape
    return exp(-exponent)


def weibull_quantile_cycles(unreliability: float, beta_shape: float, eta_scale_cycles: float) -> float:
    if not (0 < unreliability < 1):
        raise ValueError("Unreliability must be between 0 and 1.")
    if beta_shape <= 0 or eta_scale_cycles <= 0:
        raise ValueError("Invalid Weibull parameters.")
    return eta_scale_cycles * ((-log(1.0 - unreliability)) ** (1.0 / beta_shape))


def estimate_weibull_life(
    observations: list[WeibullObservation],
    target_cycles: float,
) -> WeibullResult:
    _validate_weibull_observations(observations)
    if target_cycles <= 0:
        raise ValueError("Target cycles must be > 0.")

    failures = [obs.cycles for obs in observations if obs.failed]
    all_cycles = [obs.cycles for obs in observations]
    beta = _estimate_weibull_beta(failures, all_cycles)
    eta = _weibull_eta(beta, failures, all_cycles)

    b10 = weibull_quantile_cycles(0.10, beta, eta)
    b50 = weibull_quantile_cycles(0.50, beta, eta)
    survival = weibull_survival_probability(target_cycles, beta, eta)

    notes: list[str] = []
    if len(observations) < 8 or len(failures) < 3:
        notes.append("Small sample caution: Weibull parameters may carry high statistical uncertainty.")
    if len(failures) <= len(observations) // 2:
        notes.append("High run-out fraction: fit is sensitive to censoring assumptions and test truncation levels.")
    notes.append("Model uses two-parameter Weibull minimum with right-censored MLE (no location/threshold parameter).")

    return WeibullResult(
        beta_shape=beta,
        eta_scale_cycles=eta,
        b10_cycles=b10,
        b50_cycles=b50,
        survival_at_target=survival,
        target_cycles=target_cycles,
        sample_count=len(observations),
        failure_count=len(failures),
        censored_count=len(observations) - len(failures),
        notes=notes,
    )
