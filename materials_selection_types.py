"""
Domain types for the Ashby-inspired materials-selection scaffold.

STATUS: scaffold / placeholder – scientific calibration pending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Core material descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaterialProperties:
    """Physical and fatigue properties for one material candidate.

    All stress/modulus values in MPa; density in kg/m³; K_Ic in MPa·√m.
    Fields marked TODO require literature-calibrated values before production use.
    """

    name: str
    # Mechanical
    youngs_modulus_mpa: float          # E
    yield_strength_mpa: float          # Sy
    ultimate_strength_mpa: float       # Sut
    density_kg_m3: float               # ρ
    # Fatigue (Basquin / stress-life defaults)
    endurance_limit_mpa: Optional[float] = None   # Se (fully-reversed, R=-1)
    basquin_exponent: Optional[float] = None       # b  (TODO: calibrate per material class)
    # Fracture
    fracture_toughness_mpa_sqrtm: Optional[float] = None  # K_Ic (TODO)
    # Supplemental
    material_class: str = "unclassified"   # e.g. "steel", "aluminium", "polymer"
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fatigue-specific metric bundle (derived from MaterialProperties + conditions)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FatigueMetrics:
    """Derived fatigue metrics for a given set of loading conditions.

    Populated by the selection service; raw placeholders are NaN where
    calibration data is absent.
    """

    material_name: str
    endurance_ratio: float   # Se / Sut  (TODO: validate against dataset)
    specific_endurance: float  # Se / ρ   (useful for Ashby mass-efficiency axes)
    # TODO: add fatigue-crack-growth threshold, stress-intensity range, etc.
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Selection constraint / criteria descriptors
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SelectionConstraint:
    """A hard minimum/maximum constraint on a single material property.

    Example: SelectionConstraint("yield_strength_mpa", min_value=300)
    """

    property_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass(frozen=True)
class SelectionCriteria:
    """Soft objective for multi-objective ranking (higher weight = more important).

    Example: SelectionCriteria("endurance_limit_mpa", weight=0.6, maximize=True)

    NOTE: Weighting/normalization policy is a TODO – currently uniform weights
    are applied as a placeholder.
    """

    property_name: str
    weight: float = 1.0   # TODO: calibrate relative weights from engineering rationale
    maximize: bool = True


# ---------------------------------------------------------------------------
# Candidate material with pre-computed feasibility flag
# ---------------------------------------------------------------------------

@dataclass
class MaterialCandidate:
    """A material evaluated against a set of constraints."""

    properties: MaterialProperties
    fatigue_metrics: Optional[FatigueMetrics] = None
    feasible: bool = False
    constraint_violations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Selection result
# ---------------------------------------------------------------------------

@dataclass
class SelectionResult:
    """Output of the materials-selection engine for one query."""

    candidates: list[MaterialCandidate]
    ranked: list[MaterialCandidate]    # feasible only, descending rank score
    # TODO: add uncertainty / confidence bands once calibration data is available
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ashby chart payload (axes + point data; independent of plotting backend)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AshbyChartPoint:
    """Single data point for an Ashby-style scatter plot."""

    name: str
    x: float
    y: float
    material_class: str
    selected: bool = False  # highlighted if material was in selection result


@dataclass
class AshbyChartPayload:
    """Backend-agnostic payload passed to the plotting adapter.

    x_property / y_property are keys into MaterialProperties (or computed
    fatigue metrics) that map to the chosen axes.
    """

    x_property: str
    y_property: str
    x_label: str
    y_label: str
    points: list[AshbyChartPoint] = field(default_factory=list)
    # TODO: add Pareto-front / class-envelope data once calibrated
    notes: list[str] = field(default_factory=list)
