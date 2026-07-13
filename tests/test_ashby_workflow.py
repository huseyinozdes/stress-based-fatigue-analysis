from dataclasses import replace

import pytest

from ashby_workflow import (
    build_screening_data,
    filter_materials,
    material_review_rows,
    property_by_key,
)
from materials_selection_stubs import EXAMPLE_MATERIALS


def test_filter_materials_supports_family_and_material_filters() -> None:
    aluminum = filter_materials(EXAMPLE_MATERIALS, families=("Aluminum",))
    assert [material.identity.id for material in aluminum] == ["al-6061t6"]

    steel = filter_materials(
        EXAMPLE_MATERIALS,
        families=("Steel", "Aluminum"),
        material_ids=("steel-aisi1045",),
    )
    assert [material.identity.id for material in steel] == ["steel-aisi1045"]


def test_build_screening_data_creates_reviewable_plot_points() -> None:
    data = build_screening_data(
        EXAMPLE_MATERIALS,
        x_property_key="mechanical.density_kg_m3",
        y_property_key="fatigue.endurance_limit_mpa",
    )

    assert len(data.points) == len(EXAMPLE_MATERIALS)
    assert data.dropped_materials == ()
    assert {point.family for point in data.points} == {"Steel", "Aluminum"}
    assert all(point.confidence == "Illustrative stub data" for point in data.points)
    assert all(point.review_note for point in data.points)


@pytest.mark.parametrize("invalid_value", [0.0, -1.0, float("nan"), float("inf")])
def test_build_screening_data_reports_invalid_log_values(invalid_value: float) -> None:
    invalid_material = replace(
        EXAMPLE_MATERIALS[0],
        mechanical=replace(EXAMPLE_MATERIALS[0].mechanical, density_kg_m3=invalid_value),
    )

    data = build_screening_data(
        (invalid_material,),
        x_property_key="mechanical.density_kg_m3",
        y_property_key="fatigue.endurance_limit_mpa",
    )

    assert data.points == ()
    assert len(data.dropped_materials) == 1
    assert "log axis" in data.dropped_materials[0].reason or "non-finite" in data.dropped_materials[0].reason


def test_build_screening_data_rejects_duplicate_or_unknown_axes() -> None:
    with pytest.raises(ValueError, match="different properties"):
        build_screening_data(
            EXAMPLE_MATERIALS,
            x_property_key="mechanical.density_kg_m3",
            y_property_key="mechanical.density_kg_m3",
        )

    with pytest.raises(ValueError, match="Unsupported Ashby property"):
        property_by_key("unsupported.property")


def test_material_review_rows_identify_sample_values() -> None:
    rows = material_review_rows(EXAMPLE_MATERIALS[0])
    values = {row["Property"]: row["Value"] for row in rows}

    assert values["Family"] == "Steel"
    assert values["Density"].endswith("kg/m³")
    assert values["Endurance limit"].endswith("MPa")
    assert values["Basquin exponent"] == "-0.089"
