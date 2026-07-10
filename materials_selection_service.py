from __future__ import annotations

from dataclasses import dataclass

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
            accessor = _PROPERTY_ACCESSORS.get(constraint.property_key)
            if accessor is None:
                return False
            value = accessor(material)
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
        ranked_candidates: list[SelectionCandidate] = []
        for material in feasible_materials:
            # TODO: Replace this scaffold score with calibrated multi-criteria weighting.
            placeholder_score = self._placeholder_score(material)
            ranked_candidates.append(
                SelectionCandidate(
                    material=material,
                    score=placeholder_score,
                    rationale=(
                        "Placeholder score from fatigue-endurance and density ratio.",
                        f"Criteria declared: {len(request.criteria)} (not yet applied).",
                    ),
                )
            )
        return sorted(
            ranked_candidates,
            key=lambda candidate: candidate.score if candidate.score is not None else float("-inf"),
            reverse=True,
        )

    @staticmethod
    def _placeholder_score(material: MaterialRecord) -> float | None:
        if material.fatigue.endurance_limit_mpa is None:
            return None
        if material.mechanical.density_kg_m3 <= 0:
            return None
        return material.fatigue.endurance_limit_mpa / material.mechanical.density_kg_m3
