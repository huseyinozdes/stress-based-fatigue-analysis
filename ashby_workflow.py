from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from ashby_plot import AshbyPoint
from materials_selection_types import MaterialRecord


@dataclass(frozen=True)
class MaterialProperty:
    key: str
    label: str
    unit: str
    accessor: Callable[[MaterialRecord], float | None]


@dataclass(frozen=True)
class DroppedMaterial:
    material_id: str
    material_name: str
    reason: str


@dataclass(frozen=True)
class ScreeningData:
    points: tuple[AshbyPoint, ...]
    materials: tuple[MaterialRecord, ...]
    dropped_materials: tuple[DroppedMaterial, ...]


ASHBY_PROPERTIES: tuple[MaterialProperty, ...] = (
    MaterialProperty(
        "mechanical.density_kg_m3",
        "Density",
        "kg/m³",
        lambda material: material.mechanical.density_kg_m3,
    ),
    MaterialProperty(
        "mechanical.elastic_modulus_gpa",
        "Elastic modulus",
        "GPa",
        lambda material: material.mechanical.elastic_modulus_gpa,
    ),
    MaterialProperty(
        "mechanical.yield_strength_mpa",
        "Yield strength",
        "MPa",
        lambda material: material.mechanical.yield_strength_mpa,
    ),
    MaterialProperty(
        "mechanical.ultimate_tensile_strength_mpa",
        "Ultimate tensile strength",
        "MPa",
        lambda material: material.mechanical.ultimate_tensile_strength_mpa,
    ),
    MaterialProperty(
        "fatigue.endurance_limit_mpa",
        "Endurance limit",
        "MPa",
        lambda material: material.fatigue.endurance_limit_mpa,
    ),
    MaterialProperty(
        "fatigue.fatigue_strength_coefficient_mpa",
        "Fatigue strength coefficient",
        "MPa",
        lambda material: material.fatigue.fatigue_strength_coefficient_mpa,
    ),
)


def property_by_key(property_key: str) -> MaterialProperty:
    for material_property in ASHBY_PROPERTIES:
        if material_property.key == property_key:
            return material_property
    raise ValueError(f"Unsupported Ashby property: {property_key}")


def filter_materials(
    materials: tuple[MaterialRecord, ...],
    *,
    families: tuple[str, ...] | None = None,
    material_ids: tuple[str, ...] | None = None,
) -> tuple[MaterialRecord, ...]:
    family_filter = set(families) if families is not None else None
    material_filter = set(material_ids) if material_ids is not None else None
    return tuple(
        material
        for material in materials
        if (family_filter is None or material.identity.family in family_filter)
        and (material_filter is None or material.identity.id in material_filter)
    )


def build_screening_data(
    materials: tuple[MaterialRecord, ...],
    *,
    x_property_key: str,
    y_property_key: str,
) -> ScreeningData:
    if x_property_key == y_property_key:
        raise ValueError("Choose different properties for the x and y axes.")

    x_property = property_by_key(x_property_key)
    y_property = property_by_key(y_property_key)
    points: list[AshbyPoint] = []
    plotted_materials: list[MaterialRecord] = []
    dropped_materials: list[DroppedMaterial] = []

    for material in materials:
        x_value = x_property.accessor(material)
        y_value = y_property.accessor(material)
        if x_value is None or y_value is None:
            dropped_materials.append(
                DroppedMaterial(
                    material.identity.id,
                    material.identity.name,
                    "A selected property is missing.",
                )
            )
            continue

        x_numeric = float(x_value)
        y_numeric = float(y_value)
        if not isfinite(x_numeric) or not isfinite(y_numeric):
            dropped_materials.append(
                DroppedMaterial(
                    material.identity.id,
                    material.identity.name,
                    "A selected property is non-finite.",
                )
            )
            continue
        if x_numeric <= 0 or y_numeric <= 0:
            dropped_materials.append(
                DroppedMaterial(
                    material.identity.id,
                    material.identity.name,
                    "A selected property is not positive and cannot be shown on a log axis.",
                )
            )
            continue

        fatigue_note = material.fatigue.fatigue_quality_note or "No fatigue review note is available."
        points.append(
            AshbyPoint(
                name=material.identity.name,
                family=material.identity.family,
                x_value=x_numeric,
                y_value=y_numeric,
                key_values={
                    "Family": material.identity.family,
                    "Yield strength (MPa)": material.mechanical.yield_strength_mpa,
                    "UTS (MPa)": material.mechanical.ultimate_tensile_strength_mpa,
                    "Endurance limit (MPa)": material.fatigue.endurance_limit_mpa or "not available",
                },
                review_note=fatigue_note,
                confidence="Illustrative stub data",
                source="Repository materials-selection sample data",
            )
        )
        plotted_materials.append(material)

    return ScreeningData(
        points=tuple(points),
        materials=tuple(plotted_materials),
        dropped_materials=tuple(dropped_materials),
    )


def material_review_rows(material: MaterialRecord) -> list[dict[str, str]]:
    fatigue = material.fatigue
    mechanical = material.mechanical
    return [
        {"Property": "Family", "Value": material.identity.family},
        {"Property": "Density", "Value": f"{mechanical.density_kg_m3:g} kg/m³"},
        {"Property": "Elastic modulus", "Value": f"{mechanical.elastic_modulus_gpa:g} GPa"},
        {"Property": "Yield strength", "Value": f"{mechanical.yield_strength_mpa:g} MPa"},
        {
            "Property": "Ultimate tensile strength",
            "Value": f"{mechanical.ultimate_tensile_strength_mpa:g} MPa",
        },
        {
            "Property": "Endurance limit",
            "Value": "not available" if fatigue.endurance_limit_mpa is None else f"{fatigue.endurance_limit_mpa:g} MPa",
        },
        {
            "Property": "Fatigue strength coefficient",
            "Value": (
                "not available"
                if fatigue.fatigue_strength_coefficient_mpa is None
                else f"{fatigue.fatigue_strength_coefficient_mpa:g} MPa"
            ),
        },
        {
            "Property": "Basquin exponent",
            "Value": "not available" if fatigue.basquin_exponent is None else f"{fatigue.basquin_exponent:g}",
        },
        {"Property": "Tags", "Value": ", ".join(material.tags) or "none"},
    ]


__all__ = [
    "ASHBY_PROPERTIES",
    "DroppedMaterial",
    "MaterialProperty",
    "ScreeningData",
    "build_screening_data",
    "filter_materials",
    "material_review_rows",
    "property_by_key",
]
