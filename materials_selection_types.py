from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

ObjectiveDirection = Literal["maximize", "minimize"]
ConstraintMode = Literal["all", "any"]


@dataclass(frozen=True)
class MaterialIdentity:
    id: str
    name: str
    family: str


@dataclass(frozen=True)
class MechanicalProperties:
    density_kg_m3: float
    elastic_modulus_gpa: float
    yield_strength_mpa: float
    ultimate_tensile_strength_mpa: float


@dataclass(frozen=True)
class FatigueProperties:
    endurance_limit_mpa: float | None = None
    fatigue_strength_coefficient_mpa: float | None = None
    basquin_exponent: float | None = None
    fatigue_quality_note: str | None = None


@dataclass(frozen=True)
class MaterialRecord:
    identity: MaterialIdentity
    mechanical: MechanicalProperties
    fatigue: FatigueProperties
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class NumericConstraint:
    property_key: str
    min_value: float | None = None
    max_value: float | None = None
    mode: ConstraintMode = "all"


@dataclass(frozen=True)
class SelectionCriterion:
    name: str
    property_key: str
    objective: ObjectiveDirection
    weight: float = 1.0


@dataclass(frozen=True)
class SelectionRequest:
    name: str
    numeric_constraints: tuple[NumericConstraint, ...] = ()
    required_tags: tuple[str, ...] = ()
    criteria: tuple[SelectionCriterion, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectionCandidate:
    material: MaterialRecord
    score: float | None
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectionResult:
    request: SelectionRequest
    feasible_materials: tuple[MaterialRecord, ...]
    ranked_candidates: tuple[SelectionCandidate, ...]
    unresolved_todos: tuple[str, ...] = ()


@dataclass(frozen=True)
class AshbyAxis:
    property_key: str
    label: str
    scale: Literal["linear", "log"] = "log"


@dataclass(frozen=True)
class AshbyPoint:
    material_id: str
    material_name: str
    x: float
    y: float
    is_highlighted: bool = False
    annotations: tuple[str, ...] = ()


@dataclass(frozen=True)
class AshbyChartPayload:
    x_axis: AshbyAxis
    y_axis: AshbyAxis
    points: tuple[AshbyPoint, ...]
    filters_applied: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class AshbyPlotAdapter(Protocol):
    def build_payload(
        self,
        materials: tuple[MaterialRecord, ...],
        x_axis: AshbyAxis,
        y_axis: AshbyAxis,
        highlighted_material_ids: set[str] | None = None,
    ) -> AshbyChartPayload:
        ...


@dataclass(frozen=True)
class SelectionScaffoldConfig:
    version: str = "0.1-scaffold"
    TODOs: tuple[str, ...] = field(
        default_factory=lambda: (
            "Calibrate fatigue-property distributions from validated literature datasets.",
            "Define domain-approved weighting and multi-objective scoring strategy.",
            "Add uncertainty propagation and confidence bounds into ranking.",
        )
    )
