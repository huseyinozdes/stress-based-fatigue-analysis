from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import textwrap

from ashby_plot_adapter import ScaffoldAshbyPlotAdapter, get_payload_dropped_points
from materials_selection_service import MaterialsSelectionService
from materials_selection_types import NumericConstraint, SelectionCriterion, SelectionRequest
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


def test_selection_service_rejects_non_finite_constraint_values() -> None:
    service = MaterialsSelectionService()
    invalid_material = replace(
        EXAMPLE_MATERIALS[0],
        mechanical=replace(EXAMPLE_MATERIALS[0].mechanical, yield_strength_mpa=float("nan")),
    )
    request = SelectionRequest(
        name="Finite values only",
        numeric_constraints=(
            NumericConstraint(property_key="mechanical.yield_strength_mpa", min_value=250.0),
        ),
    )

    result = service.evaluate((invalid_material,), request)

    assert result.feasible_materials == ()
    assert result.ranked_candidates == ()


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


def test_ashby_adapter_drops_invalid_log_axis_values() -> None:
    adapter = ScaffoldAshbyPlotAdapter()
    invalid_values = (0.0, -1.0, float("nan"), float("inf"))

    for value in invalid_values:
        material = replace(
            EXAMPLE_MATERIALS[0],
            mechanical=replace(EXAMPLE_MATERIALS[0].mechanical, density_kg_m3=value),
        )
        payload = adapter.build_payload(
            materials=(material,),
            x_axis=EXAMPLE_X_AXIS,
            y_axis=EXAMPLE_Y_AXIS,
        )
        assert payload.points == ()
        assert len(payload.dropped_points) == 1


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
    assert "Ashby material screening" in app_text
    assert "Ashby material screening workflow" in readme_text
    assert "st.pyplot(ashby_plot.figure, width=\"stretch\")" in app_text


def test_app_has_no_deprecated_use_container_width() -> None:
    """Guard against re-introducing use_container_width (removed in Streamlit >=2)."""
    repo_root = Path(__file__).resolve().parent.parent
    app_text = (repo_root / "app.py").read_text(encoding="utf-8")
    assert "use_container_width" not in app_text, (
        "use_container_width is deprecated and removed; use width='stretch' or width='content' instead."
    )


def test_streamlit_requirement_supports_responsive_width_api() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    requirements_text = (repo_root / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit>=1.59,<2" in requirements_text


def test_app_startup_import_handles_adapter_without_helper_symbol(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    shadow_adapter = tmp_path / "ashby_plot_adapter.py"
    shadow_adapter.write_text(
        textwrap.dedent(
            """
            class _Payload:
                def __init__(self, x_axis, y_axis):
                    self.x_axis = x_axis
                    self.y_axis = y_axis
                    self.points = ()
                    self.filters_applied = ()
                    self.notes = ()

            class ScaffoldAshbyPlotAdapter:
                def build_payload(self, materials, x_axis, y_axis, highlighted_material_ids=None):
                    return _Payload(x_axis, y_axis)
            """
        ),
        encoding="utf-8",
    )
    script = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(tmp_path)!r})
        sys.path.insert(1, {str(repo_root)!r})
        import app  # noqa: F401
        print("APP_IMPORT_OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\\n{result.stdout}\\nstderr:\\n{result.stderr}"
    assert "APP_IMPORT_OK" in result.stdout
