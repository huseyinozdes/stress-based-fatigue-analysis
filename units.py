from __future__ import annotations

from typing import Literal


UnitSystem = Literal["SI", "Imperial"]

MM_PER_IN = 25.4
N_PER_LBF = 4.4482216152605
NMM_PER_NM = 1000.0
MPA_PER_KSI = 6.894757293168361


def mm_to_in(value_mm: float) -> float:
    return value_mm / MM_PER_IN


def in_to_mm(value_in: float) -> float:
    return value_in * MM_PER_IN


def n_to_lbf(value_n: float) -> float:
    return value_n / N_PER_LBF


def lbf_to_n(value_lbf: float) -> float:
    return value_lbf * N_PER_LBF


def nm_to_nmm(value_nm: float) -> float:
    return value_nm * NMM_PER_NM


def nmm_to_nm(value_nmm: float) -> float:
    return value_nmm / NMM_PER_NM


def nm_to_lbfin(value_nm: float) -> float:
    return n_to_lbf(value_nm) * mm_to_in(1000.0)


def lbfin_to_nm(value_lbfin: float) -> float:
    return lbf_to_n(value_lbfin) * in_to_mm(1.0) / 1000.0


def lbfin_to_nmm(value_lbfin: float) -> float:
    return lbf_to_n(value_lbfin) * in_to_mm(1.0)


def mpa_to_ksi(value_mpa: float) -> float:
    return value_mpa / MPA_PER_KSI


def ksi_to_mpa(value_ksi: float) -> float:
    return value_ksi * MPA_PER_KSI


def strain_to_microstrain(value_strain: float) -> float:
    return value_strain * 1_000_000.0


def normalize_geometry_load_inputs(
    unit_system: UnitSystem,
    diameter_value: float,
    axial_mean_value: float,
    axial_alt_value: float,
    moment_mean_value: float,
    moment_alt_value: float,
) -> dict[str, float]:
    if unit_system == "SI":
        return {
            "diameter_mm": diameter_value,
            "axial_force_mean_n": axial_mean_value,
            "axial_force_alt_n": axial_alt_value,
            "bending_moment_mean_nmm": nm_to_nmm(moment_mean_value),
            "bending_moment_alt_nmm": nm_to_nmm(moment_alt_value),
        }

    return {
        "diameter_mm": in_to_mm(diameter_value),
        "axial_force_mean_n": lbf_to_n(axial_mean_value),
        "axial_force_alt_n": lbf_to_n(axial_alt_value),
        "bending_moment_mean_nmm": lbfin_to_nmm(moment_mean_value),
        "bending_moment_alt_nmm": lbfin_to_nmm(moment_alt_value),
    }
