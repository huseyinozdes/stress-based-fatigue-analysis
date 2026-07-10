"""
Ashby plot adapter – backend-agnostic rendering hooks (scaffold).

STATUS: scaffold / placeholder – final axis policy and class-envelope
        rendering pending literature calibration.

This module translates an AshbyChartPayload into an Altair chart spec
suitable for embedding in the Streamlit app.  The separation keeps domain
logic (materials_selection_service) independent of the UI layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import altair as alt

from materials_selection_types import AshbyChartPayload


def payload_to_altair(
    payload: AshbyChartPayload,
    log_x: bool = True,
    log_y: bool = True,
    height: int = 380,
) -> "alt.Chart":
    """Convert an AshbyChartPayload to an Altair scatter-chart spec.

    Selected materials (payload.points[i].selected == True) are rendered
    as filled circles with a distinct colour encoding.

    Parameters
    ----------
    payload:  AshbyChartPayload from materials_selection_service.
    log_x:    Use log scale on x-axis (typical for Ashby charts).
    log_y:    Use log scale on y-axis.
    height:   Chart height in pixels.

    TODO
    ----
    - Add material-class envelope overlays (convex-hull or ellipse per class).
    - Add Pareto-front line once multi-objective calibration is complete.
    - Expose colour-scheme and shape options for production use.
    """
    import altair as alt

    if not payload.points:
        # Return an empty chart with a descriptive title rather than failing.
        return (
            alt.Chart(alt.Data(values=[]))
            .mark_point()
            .properties(title="No data to display – check axis selection.", height=height)
        )

    records = [
        {
            "name": p.name,
            "x": p.x,
            "y": p.y,
            "class": p.material_class,
            "status": "selected" if p.selected else "candidate",
        }
        for p in payload.points
    ]

    x_scale = alt.Scale(type="log") if log_x else alt.Scale(type="linear")
    y_scale = alt.Scale(type="log") if log_y else alt.Scale(type="linear")

    base = alt.Chart(alt.Data(values=records))
    scatter = (
        base.mark_point(size=90, filled=True)
        .encode(
            x=alt.X("x:Q", scale=x_scale, title=payload.x_label),
            y=alt.Y("y:Q", scale=y_scale, title=payload.y_label),
            color=alt.Color(
                "status:N",
                scale=alt.Scale(
                    domain=["candidate", "selected"],
                    range=["#7EB8F7", "#E05252"],
                ),
                legend=alt.Legend(title="Material status"),
            ),
            shape=alt.Shape("class:N", legend=alt.Legend(title="Material class")),
            tooltip=[
                alt.Tooltip("name:N", title="Material"),
                alt.Tooltip("x:Q", title=payload.x_label, format=".3g"),
                alt.Tooltip("y:Q", title=payload.y_label, format=".3g"),
                alt.Tooltip("class:N", title="Class"),
            ],
        )
        .properties(
            title=(
                f"Ashby chart: {payload.y_label} vs {payload.x_label} "
                "(scaffold – calibration pending)"
            ),
            height=height,
        )
    )
    return scatter


def ashby_axis_options() -> dict[str, str]:
    """Return a display-name → property-name mapping for axis selection UI.

    Extend this dict as additional calibrated properties become available.

    TODO: add fracture_toughness_mpa_sqrtm, specific_endurance once data
          is validated.
    """
    return {
        "Young's modulus, E (MPa)": "youngs_modulus_mpa",
        "Yield strength, Sy (MPa)": "yield_strength_mpa",
        "Ultimate strength, Sut (MPa)": "ultimate_strength_mpa",
        "Density, ρ (kg/m³)": "density_kg_m3",
        "Endurance limit, Se (MPa)": "endurance_limit_mpa",
        "Specific endurance, Se/ρ": "specific_endurance",
        "Endurance ratio, Se/Sut": "endurance_ratio",
    }
