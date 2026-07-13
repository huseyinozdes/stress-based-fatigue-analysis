import matplotlib
import pytest

matplotlib.use("Agg")

from matplotlib import pyplot as plt

from ashby_plot import (
    AshbyPoint,
    PerformanceIndexGuide,
    add_performance_index_guideline,
    create_ashby_plot,
    export_interactive_ashby_html,
)


def _sample_points() -> list[AshbyPoint]:
    return [
        AshbyPoint(
            name="AISI 1045 steel (normalized)",
            family="Steel",
            x_value=7.85,
            y_value=290.0,
            key_values={"Sut (MPa)": 625.0},
            review_note="Baseline shaft material.",
            confidence="Medium",
            source="Repository material library",
        ),
        AshbyPoint(
            name="Al 6061-T6",
            family="Aluminum",
            x_value=2.70,
            y_value=96.0,
            key_values={"Sut (MPa)": 310.0},
            review_note="Lightweight option with finite-life follow-up required.",
            confidence="Medium",
            source="Repository material library",
        ),
    ]


def test_create_ashby_plot_sets_log_axes_and_family_groups() -> None:
    plot = create_ashby_plot(
        _sample_points(),
        x_label="Density",
        x_unit="g/cm^3",
        y_label="Fatigue screening strength",
        y_unit="MPa",
    )
    assert plot.axes.get_xscale() == "log"
    assert plot.axes.get_yscale() == "log"
    assert len(plot.tooltip_series) == 2
    legend_labels = [text.get_text() for text in plot.axes.get_legend().texts]
    assert "Steel" in legend_labels
    assert "Aluminum" in legend_labels
    plt.close(plot.figure)


def test_performance_index_guideline_follows_expected_power_law() -> None:
    figure, axes = plt.subplots()
    axes.set_xscale("log")
    axes.set_yscale("log")
    line = add_performance_index_guideline(
        axes,
        PerformanceIndexGuide(label="Specific fatigue strength", constant=10.0),
        x_min=1.0,
        x_max=10.0,
        points=5,
    )
    for x_value, y_value in zip(line.get_xdata(), line.get_ydata()):
        assert abs((y_value / x_value) - 10.0) < 1e-9
    plt.close(figure)


def test_interactive_html_contains_review_fields() -> None:
    plot = create_ashby_plot(
        _sample_points(),
        x_label="Density",
        x_unit="g/cm^3",
        y_label="Fatigue screening strength",
        y_unit="MPa",
        performance_indices=[PerformanceIndexGuide(label="Specific fatigue strength", constant=10.0)],
    )
    html = export_interactive_ashby_html(plot)
    assert "mpld3" in html.lower()
    assert "AISI 1045 steel (normalized)" in html
    assert "Review note" in html
    assert "Confidence" in html
    assert "Source" in html
    assert ".mpld3-tooltip table" in html
    plt.close(plot.figure)


@pytest.mark.parametrize("invalid_value", [0.0, -1.0, float("nan"), float("inf")])
def test_create_ashby_plot_rejects_invalid_log_values(invalid_value: float) -> None:
    point = AshbyPoint(
        name="Invalid",
        family="Test",
        x_value=invalid_value,
        y_value=1.0,
    )

    with pytest.raises(ValueError, match="finite and positive"):
        create_ashby_plot([point], x_label="X", y_label="Y")
