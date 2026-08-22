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
    MaterialRecord(
        identity=MaterialIdentity(id="steel-aisi4140", name="AISI 4140 Steel Q&T (stub)", family="Steel"),
        mechanical=MechanicalProperties(
            density_kg_m3=7850.0,
            elastic_modulus_gpa=210.0,
            yield_strength_mpa=655.0,
            ultimate_tensile_strength_mpa=1020.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=510.0,
            fatigue_strength_coefficient_mpa=1500.0,
            basquin_exponent=-0.095,
            fatigue_quality_note="Illustrative placeholder values only.",
        ),
        tags=("high-strength", "quenched-tempered", "machined"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="ti-6al4v", name="Ti-6Al-4V Annealed (stub)", family="Titanium"),
        mechanical=MechanicalProperties(
            density_kg_m3=4430.0,
            elastic_modulus_gpa=114.0,
            yield_strength_mpa=880.0,
            ultimate_tensile_strength_mpa=950.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=None,
            fatigue_strength_coefficient_mpa=1500.0,
            basquin_exponent=-0.095,
            fatigue_quality_note="No true endurance limit; use 10^7 cycle strength ~550 MPa as proxy.",
        ),
        tags=("aerospace", "lightweight", "high-strength"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="ss-aisi304", name="AISI 304 Stainless Annealed (stub)", family="Stainless Steel"),
        mechanical=MechanicalProperties(
            density_kg_m3=7900.0,
            elastic_modulus_gpa=193.0,
            yield_strength_mpa=205.0,
            ultimate_tensile_strength_mpa=515.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=None,
            fatigue_strength_coefficient_mpa=1000.0,
            basquin_exponent=-0.12,
            fatigue_quality_note="Austenitic; no defined endurance limit. 10^8 cycle strength ~200 MPa used as proxy.",
        ),
        tags=("corrosion-resistant", "general-purpose", "weldable"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="al-7075t6", name="Al 7075-T6 (stub)", family="Aluminum"),
        mechanical=MechanicalProperties(
            density_kg_m3=2810.0,
            elastic_modulus_gpa=71.7,
            yield_strength_mpa=503.0,
            ultimate_tensile_strength_mpa=572.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=None,
            fatigue_strength_coefficient_mpa=740.0,
            basquin_exponent=-0.106,
            fatigue_quality_note="No true endurance limit; 10^7 cycle strength ~160 MPa used as proxy.",
        ),
        tags=("aerospace", "lightweight", "high-strength"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="ci-gjl250", name="EN-GJL-250 Gray Cast Iron (stub)", family="Cast Iron"),
        mechanical=MechanicalProperties(
            density_kg_m3=7150.0,
            elastic_modulus_gpa=100.0,
            yield_strength_mpa=165.0,
            ultimate_tensile_strength_mpa=250.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=100.0,
            fatigue_strength_coefficient_mpa=440.0,
            basquin_exponent=-0.12,
            fatigue_quality_note="Brittle; compressive strength ~3x tensile. Endurance limit ~0.4 Sut.",
        ),
        tags=("foundry", "compressive-dominant", "general-purpose"),
    ),
    MaterialRecord(
        identity=MaterialIdentity(id="steel-aisi1020hr", name="AISI 1020 Steel Hot-Rolled (stub)", family="Steel"),
        mechanical=MechanicalProperties(
            density_kg_m3=7870.0,
            elastic_modulus_gpa=200.0,
            yield_strength_mpa=210.0,
            ultimate_tensile_strength_mpa=380.0,
        ),
        fatigue=FatigueProperties(
            endurance_limit_mpa=190.0,
            fatigue_strength_coefficient_mpa=620.0,
            basquin_exponent=-0.081,
            fatigue_quality_note="Mild steel baseline; high ductility, good weldability.",
        ),
        tags=("mild-steel", "weldable", "general-purpose"),
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
