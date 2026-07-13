from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from materials_selection_types import (
    MaterialRecord,
    NumericConstraint,
    SelectionCandidate,
    SelectionResult,
    SelectionRequest,
)


_PROPERTY_ACCESSORS = {
    "mechanical.density_kg_m3": lambda material: material.mechanical.density_kg_m3,
    "mechanical.elastic_modulus_gpa": lambda material: material.mechanical.elastic_modulus_gpa,
    "mechanical.yield_strength_mpa": lambda material: material.mechanical.yield_strength_mpa,
    "mechanical.ultimate_tensile_strength_mpa": lambda material: material.mechanical.ultimate_tensile_strength_mpa,
    "fatigue.endurance_limit_mpa": lambda material: material.fatigue.endurance_limit_mpa,
    "fatigue.fatigue_strength_coefficient_mpa": lambda material: material.fatigue.fatigue_strength_coefficient_mpa,
    "fatigue.basquin_exponent": lambda material: material.fatigue.basquin_exponent,
}


@dataclass
class MaterialsSelectionService:
    """Scaffold-only selector for materials/fatigue screening.

    The current implementation performs basic feasibility filtering and a stub
    ranking pass. The ranking strategy intentionally uses placeholders until
    literature-calibrated criteria and normalization policies are defined.
    """

    def evaluate(
        self,
        materials: tuple[MaterialRecord, ...],
        request: SelectionRequest,
    ) -> SelectionResult:
        feasible = tuple(self._apply_constraints(materials, request))
        ranked = tuple(self._rank_candidates(feasible, request))
        unresolved = (
            "TODO: replace placeholder scoring with literature-calibrated weighting.",
            "TODO: introduce normalized criteria scaling and uncertainty handling.",
            "TODO: validate constraint semantics against target design use-cases.",
        )
        return SelectionResult(
            request=request,
            feasible_materials=feasible,
            ranked_candidates=ranked,
            unresolved_todos=unresolved,
        )

    @staticmethod
    def _numeric_value(material: MaterialRecord, property_key: str) -> float | None:
        accessor = _PROPERTY_ACCESSORS.get(property_key)
        if accessor is None:
            return None
        value = accessor(material)
        if value is None:
            return None
        numeric_value = float(value)
        return numeric_value if isfinite(numeric_value) else None

    def _apply_constraints(
        self,
        materials: tuple[MaterialRecord, ...],
        request: SelectionRequest,
    ) -> list[MaterialRecord]:
        filtered_by_tags = [
            material
            for material in materials
            if all(tag in material.tags for tag in request.required_tags)
        ]
        return [
            material
            for material in filtered_by_tags
            if self._matches_numeric_constraints(material, request.numeric_constraints)
        ]

    def _matches_numeric_constraints(
        self,
        material: MaterialRecord,
        constraints: tuple[NumericConstraint, ...],
    ) -> bool:
        for constraint in constraints:
            value = self._numeric_value(material, constraint.property_key)
            if value is None:
                return False
            if constraint.min_value is not None and value < constraint.min_value:
                return False
            if constraint.max_value is not None and value > constraint.max_value:
                return False
        return True

    def _rank_candidates(
        self,
        feasible_materials: tuple[MaterialRecord, ...],
        request: SelectionRequest,
    ) -> list[SelectionCandidate]:
        if not request.criteria:
            return sorted(
                [
                SelectionCandidate(
                    material=material,
                    score=self._baseline_density_endurance_score(material),
                    rationale=(
                        "Fallback score from endurance-limit to density ratio.",
                        "No explicit criteria provided in request.",
                    ),
                )
                for material in feasible_materials
                ],
                key=lambda candidate: candidate.score if candidate.score is not None else float("-inf"),
                reverse=True,
            )

        criterion_ranges = self._criterion_ranges(feasible_materials, request)
        ranked_candidates: list[SelectionCandidate] = []
        for material in feasible_materials:
            score, rationale = self._score_material(material, request, criterion_ranges)
            ranked_candidates.append(
                SelectionCandidate(
                    material=material,
                    score=score,
                    rationale=rationale,
                )
            )
        return sorted(
            ranked_candidates,
            key=lambda candidate: candidate.score if candidate.score is not None else float("-inf"),
            reverse=True,
        )

    def _criterion_ranges(
        self,
        feasible_materials: tuple[MaterialRecord, ...],
        request: SelectionRequest,
    ) -> dict[str, tuple[float, float]]:
        ranges: dict[str, tuple[float, float]] = {}
        for criterion in request.criteria:
            values = [
                self._numeric_value(material, criterion.property_key)
                for material in feasible_materials
            ]
            numeric_values = [value for value in values if value is not None and isfinite(value)]
            if not numeric_values:
                continue
            ranges[criterion.property_key] = (min(numeric_values), max(numeric_values))
        return ranges

    def _score_material(
        self,
        material: MaterialRecord,
        request: SelectionRequest,
        criterion_ranges: dict[str, tuple[float, float]],
    ) -> tuple[float | None, tuple[str, ...]]:
        weighted_total = 0.0
        weight_sum = 0.0
        rationale: list[str] = []
        penalty = 0.0

        for criterion in request.criteria:
            weight = max(criterion.weight, 0.0)
            if weight == 0.0:
                rationale.append(f"Skipped '{criterion.name}' because weight <= 0.")
                continue

            value = self._numeric_value(material, criterion.property_key)
            value_range = criterion_ranges.get(criterion.property_key)
            weight_sum += weight
            if value is None or value_range is None:
                penalty += 0.05 * weight
                rationale.append(f"Penalty on '{criterion.name}' due to missing value/range.")
                continue

            min_value, max_value = value_range
            if max_value == min_value:
                normalized = 0.5
                rationale.append(f"Neutral score for '{criterion.name}' because min == max.")
            else:
                normalized = (value - min_value) / (max_value - min_value)
                normalized = max(0.0, min(1.0, normalized))

            if criterion.objective == "minimize":
                normalized = 1.0 - normalized

            weighted_total += normalized * weight

        if weight_sum == 0.0:
            return None, tuple(rationale + ["No positive-weight criteria available for scoring."])

        deterministic_score = max(0.0, (weighted_total / weight_sum) - penalty)
        rationale.append(f"Deterministic baseline score={deterministic_score:.4f} (penalty={penalty:.4f}).")
        rationale.append("TODO: calibrate weights and penalty terms with validated literature datasets.")
        return deterministic_score, tuple(rationale)

    @staticmethod
    def _baseline_density_endurance_score(material: MaterialRecord) -> float | None:
        endurance_limit = material.fatigue.endurance_limit_mpa
        density = material.mechanical.density_kg_m3
        if endurance_limit is None:
            return None
        if not isfinite(endurance_limit) or not isfinite(density) or density <= 0:
            return None
        return endurance_limit / density
