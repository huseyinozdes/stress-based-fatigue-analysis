from ashby_plot_adapter import ScaffoldAshbyPlotAdapter
from materials_selection_service import MaterialsSelectionService
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
    assert result.unresolved_todos


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
