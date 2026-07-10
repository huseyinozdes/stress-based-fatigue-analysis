"""
Minimal fatigue life prediction engine based on Hüseyin Özdeş's thesis:
'The Relationship Between High-Cycle Fatigue and Tensile Properties in Cast Aluminum Alloys'

This module provides:
- Structural quality index calculations
- Mean stress correction models (Soderberg, SWT, Walker)
- Basquin S-N modeling
- Weibull probability helpers
- Rotating beam to axial fatigue conversion (Esin, Manson-style helpers)
- A minimalist prediction workflow for cast aluminum alloys

The implementation is intentionally lightweight and transparent so it can be
extended as more thesis datasets and calibrated coefficients are added.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, gamma, log
from typing import Optional, Tuple


@dataclass
class TensileProperties:
    """Minimal tensile property container.

    Attributes
    ----------
    uts : float
        Ultimate tensile strength.
    ys : Optional[float]
        Yield strength.
    elongation_percent : float
        Elongation at fracture in percent.
    quality_index : Optional[float]
        Optional precomputed structural quality index.
    """

    uts: float
    ys: Optional[float] = None
    elongation_percent: float = 0.0
    quality_index: Optional[float] = None


@dataclass
class BasquinParameters:
    """Basquin parameters for S-N modeling: sigma_a = A * N^b."""

    A: float
    b: float


@dataclass
class WalkerModel:
    """Walker mean stress correction parameters."""

    exponent: float


@dataclass
class WeibullParameters:
    """Weibull distribution parameters."""

    shape_m: float
    scale_sigma0: float
    threshold_sigma_t: float = 0.0
    volume: float = 1.0


class FatigueCalculationError(ValueError):
    """Raised when an invalid fatigue calculation is requested."""


class FatigueEngine:
    """Minimalist fatigue life prediction engine.

    Notes
    -----
    This engine uses transparent empirical defaults intended for cast aluminum
    alloys. Several coefficients are placeholders that should be calibrated with
    thesis-derived datasets when available in the repository.
    """

    def __init__(
        self,
        walker_qt_intercept: float = 0.30,
        walker_qt_slope: float = 0.015,
        basquin_b_intercept: float = -0.16,
        basquin_b_slope: float = 0.0025,
        basquin_a_factor: float = 0.95,
    ) -> None:
        self.walker_qt_intercept = walker_qt_intercept
        self.walker_qt_slope = walker_qt_slope
        self.basquin_b_intercept = basquin_b_intercept
        self.basquin_b_slope = basquin_b_slope
        self.basquin_a_factor = basquin_a_factor

    @staticmethod
    def calculate_quality_index(uts: float, elongation_percent: float, ys: Optional[float] = None) -> float:
        """Estimate a structural quality index.

        A normalized minimalist form is used when full alloy-specific quality
        index equations are unavailable.

        Parameters
        ----------
        uts : float
            Ultimate tensile strength.
        elongation_percent : float
            Elongation at fracture in percent.
        ys : Optional[float]
            Yield strength, if available.

        Returns
        -------
        float
            Estimated quality index.
        """
        if uts <= 0:
            raise FatigueCalculationError("UTS must be positive.")
        if elongation_percent < 0:
            raise FatigueCalculationError("Elongation percent cannot be negative.")

        elongation_fraction = elongation_percent / 100.0
        strength_ratio = 1.0 if ys is None or ys <= 0 else ys / uts
        return uts * strength_ratio * log(1.0 + elongation_fraction)

    def infer_walker_exponent(self, qt: float) -> float:
        """Infer Walker exponent from structural quality index.

        This is a thesis-derived linear empirical mapping placeholder.
        """
        exponent = self.walker_qt_intercept + self.walker_qt_slope * qt
        return max(0.05, min(exponent, 0.95))

    @staticmethod
    def mean_stress_correction_soderberg(stress_amplitude: float, mean_stress: float, ys: float) -> float:
        """Soderberg equivalent fully-reversed stress amplitude."""
        if ys <= 0:
            raise FatigueCalculationError("Yield strength must be positive for Soderberg correction.")
        factor = 1.0 - (mean_stress / ys)
        if factor <= 0:
            raise FatigueCalculationError("Mean stress is too high for Soderberg correction.")
        return stress_amplitude / factor

    @staticmethod
    def mean_stress_correction_swt(stress_amplitude: float, max_stress: float) -> float:
        """Smith-Watson-Topper equivalent amplitude using sqrt(sigma_max * sigma_a)."""
        if stress_amplitude < 0 or max_stress < 0:
            raise FatigueCalculationError("Stress amplitude and max stress must be non-negative for SWT.")
        return (stress_amplitude * max_stress) ** 0.5

    @staticmethod
    def mean_stress_correction_walker(stress_amplitude: float, stress_ratio_r: float, exponent: float) -> float:
        """Walker corrected equivalent amplitude.

        sigma_eq = sigma_a * (1 - R)^exponent
        """
        if exponent < 0:
            raise FatigueCalculationError("Walker exponent must be non-negative.")
        base = 1.0 - stress_ratio_r
        if base <= 0:
            raise FatigueCalculationError("Stress ratio R must be less than 1 for Walker correction.")
        return stress_amplitude * (base ** exponent)

    def estimate_basquin_parameters(self, tensile: TensileProperties) -> BasquinParameters:
        """Estimate Basquin parameters from tensile data.

        Uses a QT-driven exponent and a tensile-strength-scaled coefficient.
        """
        qt = tensile.quality_index
        if qt is None:
            qt = self.calculate_quality_index(tensile.uts, tensile.elongation_percent, tensile.ys)

        b = self.basquin_b_intercept + self.basquin_b_slope * qt
        b = min(-0.02, max(-0.25, b))
        A = max(1e-9, self.basquin_a_factor * tensile.uts)
        return BasquinParameters(A=A, b=b)

    @staticmethod
    def predict_cycles(stress_amplitude: float, basquin: BasquinParameters) -> float:
        """Predict fatigue life in cycles from Basquin parameters.

        Rearranged from sigma_a = A * N^b.
        """
        if stress_amplitude <= 0:
            raise FatigueCalculationError("Stress amplitude must be positive.")
        if basquin.A <= 0:
            raise FatigueCalculationError("Basquin parameter A must be positive.")
        if basquin.b == 0:
            raise FatigueCalculationError("Basquin exponent b cannot be zero.")

        return (stress_amplitude / basquin.A) ** (1.0 / basquin.b)

    @staticmethod
    def predict_stress(cycles: float, basquin: BasquinParameters) -> float:
        """Predict stress amplitude at a given fatigue life."""
        if cycles <= 0:
            raise FatigueCalculationError("Cycles must be positive.")
        return basquin.A * (cycles ** basquin.b)

    @staticmethod
    def weibull_failure_probability(value: float, params: WeibullParameters) -> float:
        """Compute cumulative Weibull probability of failure."""
        if value <= params.threshold_sigma_t:
            return 0.0
        scaled = (value - params.threshold_sigma_t) / (params.scale_sigma0 / params.volume)
        return 1.0 - exp(-(scaled ** params.shape_m))

    @staticmethod
    def weibull_mean(params: WeibullParameters) -> float:
        """Compute mean of Weibull distribution."""
        return params.threshold_sigma_t + (params.scale_sigma0 / params.volume) * gamma(1.0 + 1.0 / params.shape_m)

    @staticmethod
    def esin_axial_stress(rotating_beam_stress: float, k: float) -> float:
        """Convert rotating beam stress amplitude to axial equivalent using Esin's method."""
        if not 0 <= k < 1:
            raise FatigueCalculationError("k must satisfy 0 <= k < 1.")
        numerator = 2.0 * rotating_beam_stress * (1.0 - k**3)
        denominator = 3.0 * (1.0 - k**2)
        return numerator / denominator

    @staticmethod
    def esin_life_factor(specimen_diameter: float, elastic_core_diameter: float) -> float:
        """Life correction factor F = D^2 / (D^2 - d^2)."""
        D = specimen_diameter
        d = elastic_core_diameter
        if D <= 0:
            raise FatigueCalculationError("Specimen diameter must be positive.")
        if d < 0 or d >= D:
            raise FatigueCalculationError("Elastic core diameter must satisfy 0 <= d < D.")
        return D**2 / (D**2 - d**2)

    def rotating_beam_to_axial(self, rotating_beam_stress: float, rotating_beam_cycles: float, specimen_diameter: float, elastic_core_diameter: float) -> Tuple[float, float]:
        """Convert rotating beam fatigue result to axial equivalent using Esin's method."""
        k = elastic_core_diameter / specimen_diameter
        axial_stress = self.esin_axial_stress(rotating_beam_stress, k)
        factor = self.esin_life_factor(specimen_diameter, elastic_core_diameter)
        axial_cycles = rotating_beam_cycles / factor
        return axial_stress, axial_cycles

    def predict_from_tensile(
        self,
        tensile: TensileProperties,
        stress_amplitude: float,
        mean_stress: float = 0.0,
        stress_ratio_r: Optional[float] = None,
        correction: str = "walker",
    ) -> dict:
        """End-to-end fatigue prediction from tensile properties.

        Returns a dictionary with quality index, model parameters, corrected
        stress amplitude, and predicted cycles.
        """
        qt = tensile.quality_index
        if qt is None:
            qt = self.calculate_quality_index(tensile.uts, tensile.elongation_percent, tensile.ys)

        basquin = self.estimate_basquin_parameters(
            TensileProperties(
                uts=tensile.uts,
                ys=tensile.ys,
                elongation_percent=tensile.elongation_percent,
                quality_index=qt,
            )
        )

        if correction.lower() == "walker":
            if stress_ratio_r is None:
                max_stress = mean_stress + stress_amplitude
                min_stress = mean_stress - stress_amplitude
                if max_stress == 0:
                    raise FatigueCalculationError("Cannot infer stress ratio when max stress is zero.")
                stress_ratio_r = min_stress / max_stress
            walker_exponent = self.infer_walker_exponent(qt)
            corrected = self.mean_stress_correction_walker(stress_amplitude, stress_ratio_r, walker_exponent)
            correction_parameter = walker_exponent
        elif correction.lower() == "soderberg":
            if tensile.ys is None:
                raise FatigueCalculationError("Yield strength is required for Soderberg correction.")
            corrected = self.mean_stress_correction_soderberg(stress_amplitude, mean_stress, tensile.ys)
            correction_parameter = tensile.ys
        elif correction.lower() == "swt":
            max_stress = mean_stress + stress_amplitude
            corrected = self.mean_stress_correction_swt(stress_amplitude, max_stress)
            correction_parameter = max_stress
        else:
            raise FatigueCalculationError(f"Unsupported correction model: {correction}")

        cycles = self.predict_cycles(corrected, basquin)
        return {
            "quality_index": qt,
            "basquin_A": basquin.A,
            "basquin_b": basquin.b,
            "correction_model": correction.lower(),
            "correction_parameter": correction_parameter,
            "corrected_stress_amplitude": corrected,
            "predicted_cycles": cycles,
        }


__all__ = [
    "BasquinParameters",
    "FatigueCalculationError",
    "FatigueEngine",
    "TensileProperties",
    "WalkerModel",
    "WeibullParameters",
]
