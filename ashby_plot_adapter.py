from __future__ import annotations

from dataclasses import dataclass

from materials_selection_types import AshbyAxis, AshbyChartPayload, AshbyPoint, MaterialRecord


_PLOT_PROPERTY_ACCESSORS = {
    "mechanical.density_kg_m3": lambda material: material.mechanical.density_kg_m3,
    "mechanical.elastic_modulus_gpa": lambda material: material.mechanical.elastic_modulus_gpa,
    "mechanical.yield_strength_mpa": lambda material: material.mechanical.yield_strength_mpa,
    "mechanical.ultimate_tensile_strength_mpa": lambda material: material.mechanical.ultimate_tensile_strength_mpa,
    "fatigue.endurance_limit_mpa": lambda material: material.fatigue.endurance_limit_mpa,
    "fatigue.fatigue_strength_coefficient_mpa": lambda material: material.fatigue.fatigue_strength_coefficient_mpa,
    "fatigue.basquin_exponent": lambda material: material.fatigue.basquin_exponent,
}


@dataclass
class ScaffoldAshbyPlotAdapter:
    """Builds chart-ready payloads for Ashby-style plotting scaffolds."""

    def build_payload(
        self,
        materials: tuple[MaterialRecord, ...],
        x_axis: AshbyAxis,
        y_axis: AshbyAxis,
        highlighted_material_ids: set[str] | None = None,
    ) -> AshbyChartPayload:
        highlighted = highlighted_material_ids or set()
        points: list[AshbyPoint] = []
        dropped_materials: list[str] = []

        for material in materials:
            x_value = self._value_for_axis(material, x_axis)
            y_value = self._value_for_axis(material, y_axis)
            if x_value is None or y_value is None:
                dropped_materials.append(material.identity.name)
                continue
            points.append(
                AshbyPoint(
                    material_id=material.identity.id,
                    material_name=material.identity.name,
                    x=x_value,
                    y=y_value,
                    is_highlighted=material.identity.id in highlighted,
                    annotations=(material.identity.family,),
                )
            )

        filters = tuple(
            [f"Omitted records with missing axis values: {', '.join(dropped_materials)}"]
            if dropped_materials
            else []
        )
        notes = (
            "Scaffold payload only; plotting backend and stylistic policy are intentionally deferred.",
            "TODO: add transform hooks for class envelopes and Pareto-front overlays.",
        )
        return AshbyChartPayload(
            x_axis=x_axis,
            y_axis=y_axis,
            points=tuple(points),
            filters_applied=filters,
            notes=notes,
        )

    @staticmethod
    def _value_for_axis(material: MaterialRecord, axis: AshbyAxis) -> float | None:
        accessor = _PLOT_PROPERTY_ACCESSORS.get(axis.property_key)
        if accessor is None:
            return None
        value = accessor(material)
        return float(value) if value is not None else None
