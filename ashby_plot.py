from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from math import isfinite, log10
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


_DEFAULT_FAMILY_STYLES: dict[str, dict[str, object]] = {
    "Steel": {"color": "#1f77b4", "marker": "o"},
    "Aluminum": {"color": "#ff7f0e", "marker": "s"},
    "Titanium": {"color": "#2ca02c", "marker": "^"},
    "Composite": {"color": "#9467bd", "marker": "D"},
    "Ceramic": {"color": "#8c564b", "marker": "P"},
}

_TOOLTIP_CSS = """
table {
  border-collapse: collapse;
  font-family: Arial, sans-serif;
  font-size: 12px;
}
th {
  text-align: left;
  padding-right: 8px;
  vertical-align: top;
}
td {
  vertical-align: top;
}
"""


@dataclass(frozen=True)
class AshbyPoint:
    name: str
    x_value: float
    y_value: float
    family: str
    review_note: str = ""
    confidence: str = ""
    source: str = ""
    key_values: Mapping[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class PerformanceIndexGuide:
    label: str
    constant: float
    y_exponent: float = 1.0
    x_exponent: float = 1.0
    color: str = "#6b7280"
    linestyle: str = "--"
    linewidth: float = 1.1


@dataclass
class AshbyPlotResult:
    figure: Figure
    axes: Axes
    tooltip_series: list[tuple[PathCollection, list[str]]]


def _logspace_10(start_exp: float, end_exp: float, points: int) -> list[float]:
    if points < 2:
        return [10**start_exp]
    step = (end_exp - start_exp) / (points - 1)
    return [10 ** (start_exp + i * step) for i in range(points)]


def _format_tooltip_value(value: float | int | str) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _validate_points(points: Sequence[AshbyPoint]) -> None:
    if not points:
        raise ValueError("At least one Ashby point is required.")
    for point in points:
        if (
            not isfinite(point.x_value)
            or not isfinite(point.y_value)
            or point.x_value <= 0
            or point.y_value <= 0
        ):
            raise ValueError("Ashby plot values must be finite and positive for log-log axes.")


def build_tooltip_html(
    point: AshbyPoint,
    *,
    x_label: str,
    y_label: str,
    x_unit: str = "",
    y_unit: str = "",
) -> str:
    rows = [
        ("Material", point.name),
        (x_label, f"{_format_tooltip_value(point.x_value)} {x_unit}".strip()),
        (y_label, f"{_format_tooltip_value(point.y_value)} {y_unit}".strip()),
    ]
    for key, value in point.key_values.items():
        rows.append((key, _format_tooltip_value(value)))
    if point.review_note:
        rows.append(("Review note", point.review_note))
    if point.confidence:
        rows.append(("Confidence", point.confidence))
    if point.source:
        rows.append(("Source", point.source))

    row_html = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in rows
    )
    return f"<table>{row_html}</table>"


def add_performance_index_guideline(
    ax: Axes,
    guide: PerformanceIndexGuide,
    *,
    x_min: float,
    x_max: float,
    points: int = 80,
) -> Line2D:
    if guide.constant <= 0:
        raise ValueError("Performance index constant must be positive.")
    if guide.y_exponent <= 0:
        raise ValueError("Performance index y exponent must be positive.")
    if x_min <= 0 or x_max <= 0 or x_min >= x_max:
        raise ValueError("x_min and x_max must be positive and ordered for log scaling.")

    x_values = _logspace_10(log10(x_min), log10(x_max), points)
    y_values = [
        (guide.constant * (x_value**guide.x_exponent)) ** (1.0 / guide.y_exponent)
        for x_value in x_values
    ]
    line = ax.plot(
        x_values,
        y_values,
        color=guide.color,
        linestyle=guide.linestyle,
        linewidth=guide.linewidth,
        label=guide.label,
    )[0]
    ax.text(
        x_values[-1],
        y_values[-1],
        f" {guide.label}",
        color=guide.color,
        fontsize=9,
        va="bottom",
        ha="left",
    )
    return line


def create_ashby_plot(
    points: Sequence[AshbyPoint],
    *,
    x_label: str,
    y_label: str,
    title: str = "",
    x_unit: str = "",
    y_unit: str = "",
    performance_indices: Sequence[PerformanceIndexGuide] = (),
    family_styles: Mapping[str, Mapping[str, object]] | None = None,
    ax: Axes | None = None,
) -> AshbyPlotResult:
    _validate_points(points)
    if ax is None:
        figure, axes = plt.subplots(figsize=(9, 6))
    else:
        axes = ax
        figure = ax.figure

    styles: dict[str, Mapping[str, object]] = dict(_DEFAULT_FAMILY_STYLES)
    if family_styles:
        styles.update(family_styles)

    grouped_points: dict[str, list[AshbyPoint]] = {}
    for point in points:
        grouped_points.setdefault(point.family, []).append(point)

    tooltip_series: list[tuple[PathCollection, list[str]]] = []
    for family, family_points in grouped_points.items():
        style = styles.get(family, {"color": "#4b5563", "marker": "o"})
        scatter = axes.scatter(
            [point.x_value for point in family_points],
            [point.y_value for point in family_points],
            color=style.get("color", "#4b5563"),
            marker=style.get("marker", "o"),
            s=75,
            alpha=0.9,
            edgecolors="black",
            linewidths=0.4,
            label=family,
        )
        labels = [
            build_tooltip_html(point, x_label=x_label, y_label=y_label, x_unit=x_unit, y_unit=y_unit)
            for point in family_points
        ]
        tooltip_series.append((scatter, labels))

    x_values = [point.x_value for point in points]
    x_min = min(x_values) * 0.85
    x_max = max(x_values) * 1.15
    for guide in performance_indices:
        add_performance_index_guideline(axes, guide, x_min=x_min, x_max=x_max)

    axes.set_xscale("log")
    axes.set_yscale("log")
    axes.set_xlabel(f"{x_label} ({x_unit})".strip().replace(" ()", ""))
    axes.set_ylabel(f"{y_label} ({y_unit})".strip().replace(" ()", ""))
    if title:
        axes.set_title(title)
    axes.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)
    if len(grouped_points) > 1 or performance_indices:
        axes.legend()

    return AshbyPlotResult(figure=figure, axes=axes, tooltip_series=tooltip_series)


def export_interactive_ashby_html(
    plot_result: AshbyPlotResult,
    output_path: str | Path | None = None,
) -> str:
    try:
        import mpld3
        from mpld3 import plugins
    except ImportError as exc:
        raise RuntimeError("mpld3 is required for interactive Ashby HTML export.") from exc

    for artist, labels in plot_result.tooltip_series:
        plugins.connect(
            plot_result.figure,
            plugins.PointHTMLTooltip(artist, labels=labels, voffset=10, hoffset=10, css=_TOOLTIP_CSS),
        )

    html = mpld3.fig_to_html(plot_result.figure)
    if output_path is not None:
        Path(output_path).write_text(html, encoding="utf-8")
    return html


__all__ = [
    "AshbyPoint",
    "AshbyPlotResult",
    "PerformanceIndexGuide",
    "add_performance_index_guideline",
    "build_tooltip_html",
    "create_ashby_plot",
    "export_interactive_ashby_html",
]
