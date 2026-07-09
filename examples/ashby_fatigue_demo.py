from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ashby_plot import (
    AshbyPoint,
    PerformanceIndexGuide,
    create_ashby_plot,
    export_interactive_ashby_html,
)
from project_version import PROJECT_VERSION


def fatigue_screening_points() -> list[AshbyPoint]:
    return [
        AshbyPoint(
            name="AISI 1045 steel (normalized)",
            family="Steel",
            x_value=7.85,
            y_value=290.0,
            key_values={"Sut (MPa)": 625.0, "Yield (MPa)": 530.0},
            review_note="Balanced baseline for machined shafts; review corrosion and notch effects separately.",
            confidence="Medium",
            source="Repository fatigue material library + handbook density",
        ),
        AshbyPoint(
            name="AISI 4140 steel (Q&T)",
            family="Steel",
            x_value=7.83,
            y_value=470.0,
            key_values={"Sut (MPa)": 1020.0, "Yield (MPa)": 655.0},
            review_note="Strong fatigue-screening candidate when heat treatment and section size are controlled.",
            confidence="Medium",
            source="Repository fatigue material library + handbook density",
        ),
        AshbyPoint(
            name="Al 6061-T6",
            family="Aluminum",
            x_value=2.70,
            y_value=96.0,
            key_values={"Sut (MPa)": 310.0, "Yield (MPa)": 276.0},
            review_note="Lightweight option; finite-life behavior should be checked because aluminum has no true endurance plateau.",
            confidence="Medium",
            source="Repository fatigue material library + handbook density",
        ),
        AshbyPoint(
            name="Ti-6Al-4V",
            family="Titanium",
            x_value=4.43,
            y_value=510.0,
            key_values={"Sut (MPa)": 950.0, "Fatigue strength (MPa)": 510.0},
            review_note="High specific fatigue strength, but cost and procurement traceability usually drive the review.",
            confidence="Low",
            source="Representative handbook screening value",
        ),
        AshbyPoint(
            name="Quasi-isotropic CFRP laminate",
            family="Composite",
            x_value=1.58,
            y_value=240.0,
            key_values={"Tension strength (MPa)": 600.0, "Fatigue screening (MPa)": 240.0},
            review_note="Excellent mass efficiency, but laminate orientation and environmental knockdowns need follow-up review.",
            confidence="Low",
            source="Representative laminate screening value",
        ),
    ]


def main() -> None:
    output_path = Path("ashby_fatigue_demo.html")
    plot = create_ashby_plot(
        fatigue_screening_points(),
        x_label="Density",
        x_unit="g/cm^3",
        y_label="Fatigue screening strength",
        y_unit="MPa",
        title=f"Fatigue screening Ashby map ({PROJECT_VERSION})",
        performance_indices=[
            PerformanceIndexGuide(
                label="Specific fatigue strength",
                constant=60.0,
                y_exponent=1.0,
                x_exponent=1.0,
            )
        ],
    )
    export_interactive_ashby_html(plot, output_path)
    plot.figure.savefig("ashby_fatigue_demo.png", dpi=150, bbox_inches="tight")
    print(f"Wrote interactive HTML to {output_path.resolve()}")


if __name__ == "__main__":
    main()
