from dataclasses import replace
from pathlib import Path

from ashby_plot_adapter import ScaffoldAshbyPlotAdapter, get_payload_dropped_points
from materials_selection_service import MaterialsSelectionService
from materials_selection_types import SelectionCriterion, SelectionRequest
from materials_selection_stubs import (
    EXAMPLE_MATERIALS,
    EXAMPLE_SELECTION_REQUEST,
    EXAMPLE_X_AXIS,
    EXAMPLE_Y_AXIS,
)


def test_selection_service_filters_and_ranks_stub_materials() -> None:
    service = MaterialsSelectionService()
    result = service.evaluate(EXAMPLE_MATERIALS, EXAMPLE_SELECTION_REQUEST)

    assert result.request.name == "Scaffold demo request"
    assert len(result.feasible_materials) >= 1
    assert len(result.ranked_candidates) == len(result.feasible_materials)
    assert result.ranked_candidates[0].score is not None
    assert result.ranked_candidates[0].score >= result.ranked_candidates[-1].score
    assert result.unresolved_todos


def test_selection_service_applies_penalty_for_missing_criterion_values() -> None:
    service = MaterialsSelectionService()
    low_data_material = replace(
        EXAMPLE_MATERIALS[0],
        fatigue=replace(EXAMPLE_MATERIALS[0].fatigue, endurance_limit_mpa=None),
    )
    request = SelectionRequest(
        name="Penalty check",
        criteria=(
            SelectionCriterion(
                name="Maximize endurance limit",
                property_key="fatigue.endurance_limit_mpa",
                objective="maximize",
                weight=1.0,
            ),
        ),
    )
    result = service.evaluate((low_data_material, EXAMPLE_MATERIALS[1]), request)
    assert result.ranked_candidates[0].score is not None
    assert result.ranked_candidates[1].score is not None
    assert result.ranked_candidates[0].score > result.ranked_candidates[1].score


def test_selection_service_uses_neutral_score_when_range_collapses() -> None:
    service = MaterialsSelectionService()
    m1 = replace(EXAMPLE_MATERIALS[0], mechanical=replace(EXAMPLE_MATERIALS[0].mechanical, density_kg_m3=7000.0))
    m2 = replace(EXAMPLE_MATERIALS[1], mechanical=replace(EXAMPLE_MATERIALS[1].mechanical, density_kg_m3=7000.0))
    request = SelectionRequest(
        name="Collapsed range check",
        criteria=(
            SelectionCriterion(
                name="Minimize density",
                property_key="mechanical.density_kg_m3",
                objective="minimize",
                weight=1.0,
            ),
        ),
    )
    result = service.evaluate((m1, m2), request)
    assert result.ranked_candidates[0].score == 0.5
    assert result.ranked_candidates[1].score == 0.5


def test_ashby_adapter_payload_contains_axis_and_points() -> None:
    adapter = ScaffoldAshbyPlotAdapter()
    payload = adapter.build_payload(
        materials=EXAMPLE_MATERIALS,
        x_axis=EXAMPLE_X_AXIS,
        y_axis=EXAMPLE_Y_AXIS,
        highlighted_material_ids={"steel-aisi1045"},
    )

    assert payload.x_axis.label.startswith("Density")
    assert payload.y_axis.label.startswith("Endurance")
    assert len(payload.points) == len(EXAMPLE_MATERIALS)
    assert any(point.is_highlighted for point in payload.points)
    assert payload.highlighted_material_ids == ("steel-aisi1045",)
    assert "dropped_points=0" in payload.filters_applied


def test_ashby_adapter_marks_dropped_points_with_structured_metadata() -> None:
    adapter = ScaffoldAshbyPlotAdapter()
    missing_x = replace(
        EXAMPLE_MATERIALS[0],
        mechanical=replace(EXAMPLE_MATERIALS[0].mechanical, density_kg_m3=0.0),
    )
    # Force missing axis value through unsupported key.
    from materials_selection_types import AshbyAxis

    bad_axis = AshbyAxis(property_key="fatigue.not_available", label="Unavailable")
    payload = adapter.build_payload(
        materials=(missing_x,),
        x_axis=bad_axis,
        y_axis=EXAMPLE_Y_AXIS,
        highlighted_material_ids={"steel-aisi1045"},
    )
    assert len(payload.points) == 0
    assert len(payload.dropped_points) == 1
    dropped = payload.dropped_points[0]
    assert dropped.material_id == "steel-aisi1045"
    assert "missing_axis_value" == dropped.reason
    assert "fatigue.not_available" in dropped.missing_axis_keys


def test_dropped_points_accessor_handles_legacy_payload_shape() -> None:
    class LegacyPayload:
        dropped_materials = [{"material_name": "Legacy"}]

    class UnknownPayload:
        pass

    assert len(get_payload_dropped_points(LegacyPayload())) == 1
    assert get_payload_dropped_points(UnknownPayload()) == ()


def test_project_text_has_updated_ashby_labels() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    app_text = (repo_root / "app.py").read_text(encoding="utf-8")
    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "Materials selection scaffold (Ashby)" in app_text
    assert "Materials-selection scaffold (Ashby, new)" in readme_text
