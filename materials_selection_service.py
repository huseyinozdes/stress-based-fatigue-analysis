"""
Materials-selection service shell (Ashby-inspired scaffold).

STATUS: scaffold / placeholder – scoring policy not yet calibrated.

The service exposes two entry points:
  - evaluate_candidates()  – filters by hard constraints, computes fatigue
                             metrics, and applies a placeholder ranking.
  - build_ashby_payload()  – constructs an AshbyChartPayload from a list of
                             MaterialProperties for any two chosen axes.
"""
from __future__ import annotations

import math
from typing import Sequence

from materials_selection_types import (
    AshbyChartPayload,
    AshbyChartPoint,
    FatigueMetrics,
    MaterialCandidate,
    MaterialProperties,
    SelectionConstraint,
    SelectionCriteria,
    SelectionResult,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_property(props: MaterialProperties, name: str) -> float | None:
    """Return a named scalar attribute from MaterialProperties (or None)."""
    value = getattr(props, name, None)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _compute_fatigue_metrics(props: MaterialProperties) -> FatigueMetrics:
    """Derive FatigueMetrics from MaterialProperties.

    TODO: Replace heuristic endurance ratio with literature-calibrated
    material-class-specific distributions.
    """
    notes: list[str] = []

    if props.endurance_limit_mpa is not None:
        se = props.endurance_limit_mpa
    else:
        # Heuristic placeholder: Se ≈ 0.5 · Sut for ferrous, 0.4 · Sut otherwise
        # TODO: calibrate per material class and surface/size/reliability factors
        ratio = 0.5 if props.material_class in {"steel", "iron"} else 0.4
        se = ratio * props.ultimate_strength_mpa
        notes.append(
            f"Endurance limit estimated as {ratio:.1f}·Sut (placeholder – "
            "not calibrated for this material class)."
        )

    endurance_ratio = se / props.ultimate_strength_mpa if props.ultimate_strength_mpa else 0.0
    specific_endurance = se / props.density_kg_m3 if props.density_kg_m3 else 0.0

    return FatigueMetrics(
        material_name=props.name,
        endurance_ratio=endurance_ratio,
        specific_endurance=specific_endurance,
        notes=notes,
    )


def _check_constraints(
    props: MaterialProperties,
    metrics: FatigueMetrics,
    constraints: Sequence[SelectionConstraint],
) -> list[str]:
    """Return a list of violated constraint descriptions (empty = feasible)."""
    violations: list[str] = []
    for c in constraints:
        # Try MaterialProperties first, then FatigueMetrics
        value: float | None = _get_property(props, c.property_name)
        if value is None:
            value = getattr(metrics, c.property_name, None)
        if value is None:
            violations.append(
                f"Property '{c.property_name}' not available for '{props.name}'."
            )
            continue
        if c.min_value is not None and value < c.min_value:
            violations.append(
                f"'{props.name}': {c.property_name}={value:.2f} < min {c.min_value:.2f}."
            )
        if c.max_value is not None and value > c.max_value:
            violations.append(
                f"'{props.name}': {c.property_name}={value:.2f} > max {c.max_value:.2f}."
            )
    return violations


def _rank_candidates(
    candidates: list[MaterialCandidate],
    criteria: Sequence[SelectionCriteria],
) -> list[MaterialCandidate]:
    """Return feasible candidates sorted by a weighted-sum rank score.

    TODO: Replace min-max normalisation + uniform weighting with a
    calibrated multi-objective policy (e.g. TOPSIS or weighted-Ashby index).
    """
    feasible = [c for c in candidates if c.feasible]
    if not feasible or not criteria:
        return feasible

    # Collect raw values per criterion
    raw: dict[str, list[float | None]] = {}
    for crit in criteria:
        raw[crit.property_name] = []
        for cand in feasible:
            val: float | None = _get_property(cand.properties, crit.property_name)
            if val is None and cand.fatigue_metrics is not None:
                val = getattr(cand.fatigue_metrics, crit.property_name, None)
            raw[crit.property_name].append(val)

    # Min-max normalise per criterion (placeholder – not validated)
    scores: dict[int, float] = {i: 0.0 for i in range(len(feasible))}
    for crit in criteria:
        vals = [v for v in raw[crit.property_name] if v is not None]
        if not vals:
            continue
        v_min, v_max = min(vals), max(vals)
        span = (v_max - v_min) or 1.0
        for i, cand in enumerate(feasible):
            v = raw[crit.property_name][i]
            if v is None:
                continue
            normalised = (v - v_min) / span
            if not crit.maximize:
                normalised = 1.0 - normalised
            scores[i] += crit.weight * normalised

    score_map = {id(c): scores[i] for i, c in enumerate(feasible)}
    return sorted(feasible, key=lambda c: score_map[id(c)], reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_candidates(
    materials: Sequence[MaterialProperties],
    constraints: Sequence[SelectionConstraint] = (),
    criteria: Sequence[SelectionCriteria] = (),
) -> SelectionResult:
    """Evaluate and rank a list of materials against constraints and criteria.

    Parameters
    ----------
    materials:    Iterable of MaterialProperties to evaluate.
    constraints:  Hard feasibility constraints; infeasible materials are
                  excluded from ranking but still returned in `candidates`.
    criteria:     Soft optimisation objectives used for ranking.

    Returns
    -------
    SelectionResult with all candidates (feasibility flagged) and a ranked
    list of feasible candidates.
    """
    notes: list[str] = [
        "Ranking uses a placeholder min-max weighted-sum policy (TODO: calibrate).",
        "Endurance limits estimated where not explicitly provided.",
    ]

    candidates: list[MaterialCandidate] = []
    for props in materials:
        metrics = _compute_fatigue_metrics(props)
        violations = _check_constraints(props, metrics, constraints)
        candidates.append(
            MaterialCandidate(
                properties=props,
                fatigue_metrics=metrics,
                feasible=(len(violations) == 0),
                constraint_violations=violations,
            )
        )

    ranked = _rank_candidates(candidates, criteria)
    return SelectionResult(candidates=candidates, ranked=ranked, notes=notes)


def build_ashby_payload(
    materials: Sequence[MaterialProperties],
    x_property: str,
    y_property: str,
    x_label: str = "",
    y_label: str = "",
    selected_names: Sequence[str] = (),
) -> AshbyChartPayload:
    """Build an AshbyChartPayload for two chosen property axes.

    Missing or zero values are silently skipped (incomplete point filtering).

    Parameters
    ----------
    materials:       Candidate materials to plot.
    x_property:      Attribute name on MaterialProperties (or FatigueMetrics)
                     for the x-axis.
    y_property:      Attribute name for the y-axis.
    x_label:         Human-readable axis label (defaults to property name).
    y_label:         Human-readable axis label (defaults to property name).
    selected_names:  Names of materials to highlight as selected.
    """
    notes: list[str] = [
        "TODO: add class-envelope overlays and Pareto-front lines once "
        "literature-calibrated datasets are available.",
    ]
    points: list[AshbyChartPoint] = []
    selected_set = set(selected_names)

    for props in materials:
        metrics = _compute_fatigue_metrics(props)
        x = _get_property(props, x_property)
        if x is None:
            x = getattr(metrics, x_property, None)
        y = _get_property(props, y_property)
        if y is None:
            y = getattr(metrics, y_property, None)

        if x is None or y is None or x == 0.0 or y == 0.0:
            notes.append(
                f"'{props.name}' skipped: missing value for '{x_property}' "
                f"or '{y_property}'."
            )
            continue

        points.append(
            AshbyChartPoint(
                name=props.name,
                x=x,
                y=y,
                material_class=props.material_class,
                selected=props.name in selected_set,
            )
        )

    return AshbyChartPayload(
        x_property=x_property,
        y_property=y_property,
        x_label=x_label or x_property,
        y_label=y_label or y_property,
        points=points,
        notes=notes,
    )
