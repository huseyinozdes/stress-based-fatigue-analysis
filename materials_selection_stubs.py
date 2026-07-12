from __future__ import annotations

from materials_selection_types import (
    AshbyAxis,
    FatigueProperties,
    MaterialIdentity,
    MaterialRecord,
    MechanicalProperties,
    NumericConstraint,
    SelectionCriterion,
    SelectionRequest,
)

EXAMPLE_MATERIALS: tuple[MaterialRecord, ...] = (
    MaterialRecord(
        identity=MaterialIdentity(id="steel-aisi1045", name="AISI 1045 Steel (stub)", family="Steel"),
        mechanical=MechanicalProperties(
            density_kg_m3=7850.0,
            elastic_modulus_gpa=205.0,
            yield_strength_mpa=530.0,
            ultimate_tensile_strength_mpa=625.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=310.0,
            fatigue_strength_coefficient_mpa=980.0,
            basquin_exponent=-0.089,
            fatigue_quality_note="Illustrative placeholder values only.",
        ),
        tags=("general-purpose", "machined"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="al-6061t6", name="Al 6061-T6 (stub)", family="Aluminum"),
        mechanical=MechanicalProperties(
            density_kg_m3=2700.0,
            elastic_modulus_gpa=69.0,
            yield_strength_mpa=276.0,
            ultimate_tensile_strength_mpa=310.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=96.0,
            fatigue_strength_coefficient_mpa=450.0,
            basquin_exponent=-0.085,
            fatigue_quality_note="Illustrative placeholder values only.",
        ),
        tags=("lightweight", "general-purpose"),
    ),
)

EXAMPLE_SELECTION_REQUEST = SelectionRequest(
    name="Scaffold demo request",
    numeric_constraints=(
        NumericConstraint(property_key="mechanical.yield_strength_mpa", min_value=250.0),
        NumericConstraint(property_key="fatigue.endurance_limit_mpa", min_value=90.0),
    ),
    required_tags=("general-purpose",),
    criteria=(
        SelectionCriterion(
            name="Maximize endurance limit",
            property_key="fatigue.endurance_limit_mpa",
            objective="maximize",
            weight=0.6,
        ),
        SelectionCriterion(
            name="Minimize density",
            property_key="mechanical.density_kg_m3",
            objective="minimize",
            weight=0.4,
        ),
    ),
    notes=("Scaffold-only criteria; weights are not calibrated.",),
)

EXAMPLE_X_AXIS = AshbyAxis(
    property_key="mechanical.density_kg_m3",
    label="Density (kg/m^3)",
    scale="log",
)
EXAMPLE_Y_AXIS = AshbyAxis(
    property_key="fatigue.endurance_limit_mpa",
    label="Endurance limit (MPa)",
    scale="log",
)
