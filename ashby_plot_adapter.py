from __future__ import annotations

from dataclasses import dataclass

from materials_selection_types import AshbyAxis, AshbyChartPayload, AshbyDroppedPoint, AshbyPoint, MaterialRecord


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
        dropped_points: list[AshbyDroppedPoint] = []

        for material in materials:
            x_value = self._value_for_axis(material, x_axis)
            y_value = self._value_for_axis(material, y_axis)
            if x_value is None or y_value is None:
                missing_keys: list[str] = []
                if x_value is None:
                    missing_keys.append(x_axis.property_key)
                if y_value is None:
                    missing_keys.append(y_axis.property_key)
                dropped_points.append(
                    AshbyDroppedPoint(
                        material_id=material.identity.id,
                        material_name=material.identity.name,
                        missing_axis_keys=tuple(missing_keys),
                        reason="missing_axis_value",
                    )
                )
                continue
            points.append(
                AshbyPoint(
                    material_id=material.identity.id,
                    material_name=material.identity.name,
                    x=x_value,
                    y=y_value,
                    is_highlighted=material.identity.id in highlighted,
                    annotations=(
                        f"family={material.identity.family}",
                        f"selection_state={'highlighted' if material.identity.id in highlighted else 'candidate'}",
                    ),
                )
            )

        highlighted_present = sorted([point.material_id for point in points if point.is_highlighted])
        filters = (
            f"axis.x={x_axis.property_key}",
            f"axis.y={y_axis.property_key}",
            f"dropped_points={len(dropped_points)}",
            f"highlighted_points={len(highlighted_present)}",
        )
        notes = (
            "Scaffold payload only; plotting backend and stylistic policy are intentionally deferred.",
            "TODO: add transform hooks for class envelopes and Pareto-front overlays.",
        )
        return AshbyChartPayload(
            x_axis=x_axis,
            y_axis=y_axis,
            points=tuple(points),
            dropped_points=tuple(dropped_points),
            highlighted_material_ids=tuple(highlighted_present),
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
