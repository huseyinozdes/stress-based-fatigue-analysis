# Stress-Based Fatigue Analysis — Web Estimator v2.1.0

This repository now includes a lightweight web app for quick-reference fatigue-life estimation.

**Live App:** [https://stressbasedfatigue.streamlit.app](https://stressbasedfatigue.streamlit.app)

## What this v2 tool does

- Collects core engineering inputs: **material**, **section diameter** $d$, **axial force** $(F_m,\ F_a)$, **bending moment** $(M_m,\ M_a)$, and fatigue modifiers.
- Supports two model paths:
  - **Stress-life (S-N)** for high-cycle screening,
  - **Strain-life ($\varepsilon$-N)** using Manson-Coffin-Basquin style estimation.
- Adds optional **statistical reliability** from fatigue test data using two-parameter Weibull MLE with right-censored run-outs.
- Includes a **unit-system toggle** (SI primary or Imperial primary) with inline passive conversions next to inputs.
- Uses rendered GitHub math and the same scientist-friendly symbols used in the app's **Nomenclature & Symbols** panel.
- Reports estimated life $N_f$, key intermediate values, engineering graphs, and caution notes.

## Models and equations

The estimator follows a compact stress-life, strain-life, and Weibull workflow aligned with practical machine-design methods.

### Section stress from area and bending

For a solid round section:

$$
A = \frac{\pi d^2}{4}
$$

$$
\sigma = \frac{F}{A}, \qquad \sigma_b = \frac{32M}{\pi d^3}
$$

With mean and alternating loading, the app combines axial and bending terms as:

$$
\sigma_m = \frac{F_m}{A} + \frac{32 M_m}{\pi d^3}, \qquad
\sigma_a = \frac{F_a}{A} + \frac{32 M_a}{\pi d^3}
$$

### Endurance limit

The rotating-beam baseline and Marin correction path are:

$$
S_e' = 0.5 S_{ut}
$$

$$
S_e = k_a k_b k_c k_d k_e k_f S_e'
$$

### Goodman correction

$$
\sigma_{a,eq} = \frac{\sigma_a}{1 - \sigma_m/S_{ut}}
$$

### Basquin stress-life relation

The stress-life branch fits a Basquin line between $N = 10^3$ at $S_f = 0.9 S_{ut}$ and $N = 10^6$ at $S_f = S_e$, then solves:

$$
S_f(N_f) = a N_f^b, \qquad \sigma_{a,eq} = S_f(N_f)
$$

### Manson-Coffin-Basquin strain-life relation

The strain-life branch uses Morrow mean-stress correction in the elastic term:

$$
\varepsilon_a = \left( \frac{\sigma_f' - \sigma_m}{E} \right) (2N_f)^b + \varepsilon_f' (2N_f)^c
$$

### Weibull reliability

For two-parameter Weibull reliability:

$$
F(N) = 1 - \exp \left( - \left( \frac{N}{\eta} \right)^{\beta} \right), \qquad
R(N) = \exp \left( - \left( \frac{N}{\eta} \right)^{\beta} \right)
$$

$$
B_{10} = \eta \left[ -\ln(0.9) \right]^{1/\beta}, \qquad
B_{50} = \eta \left( \ln 2 \right)^{1/\beta}
$$

## Fatigue — engineering background

Fatigue is the progressive, localised, and permanent structural change that occurs in a material subjected to repeated or fluctuating stresses. Unlike static failure, fatigue fracture can occur at stresses well below the material's ultimate tensile strength $S_{ut}$ and, for many steels, below the endurance limit $S_e$.

### Why fatigue matters

The majority of mechanical failures in service are fatigue-driven. Cracks typically initiate at stress concentrations — notches, surface defects, inclusions, or geometric discontinuities — then propagate under cyclic loading until the remaining cross-section can no longer carry the peak load, causing sudden fracture. Three stages govern the process:

1. **Crack initiation** — dislocation pile-ups or inclusion debonding create a micro-crack nucleus, typically at the surface where cyclic plastic strains are highest.
2. **Crack propagation** — the crack advances by a small increment $\Delta a$ per cycle following Paris' law: $\dfrac{da}{dN} = C (\Delta K)^m$, where $\Delta K = Y \Delta\sigma \sqrt{\pi a}$ is the stress-intensity-factor range.
3. **Final fracture** — when crack length $a$ reaches the critical value $a_c = \dfrac{1}{\pi}\left(\dfrac{K_{Ic}}{\sigma_{max} Y}\right)^2$, unstable fracture occurs.

### Stress-life (S-N) regime — high-cycle fatigue (HCF)

The S-N (Wöhler) approach is valid for **high-cycle fatigue (HCF)**, typically $N_f > 10^4$ cycles, where plastic strains per cycle are negligible. The Basquin power-law relates the fully-reversed stress amplitude $\sigma_a$ to life $N_f$:

$$\sigma_a = \sigma_f' (2N_f)^b$$

For steels with $S_{ut} \leq 1400\ \mathrm{MPa}$, a finite-life line is fitted between two anchor points:

$$\left(N = 10^3,\ S_f = 0.9\,S_{ut}\right) \quad \text{and} \quad \left(N = 10^6,\ S_f = S_e\right)$$

giving Basquin slope $b = \dfrac{1}{3}\log_{10}\!\left(\dfrac{0.9\,S_{ut}}{S_e}\right)$.

### Strain-life ($\varepsilon$-N) regime — low-cycle fatigue (LCF)

When local plastic strains are significant ($N_f < 10^4$ cycles), the **Manson-Coffin-Basquin** model separates elastic and plastic strain contributions:

$$\varepsilon_a = \underbrace{\frac{\sigma_f'}{E}(2N_f)^b}_{\text{elastic}} + \underbrace{\varepsilon_f'(2N_f)^c}_{\text{plastic}}$$

where $\sigma_f'$ is the fatigue strength coefficient, $\varepsilon_f'$ is the fatigue ductility coefficient, $b$ is the Basquin (elastic) exponent, and $c$ is the Coffin-Manson (plastic) exponent. The **transition life** $2N_t$ where elastic and plastic contributions are equal is:

$$2N_t = \left(\frac{\varepsilon_f' E}{\sigma_f'}\right)^{1/(b-c)}$$

### Mean stress correction

Non-zero mean stress $\sigma_m$ reduces (tensile) or increases (compressive) fatigue resistance. This estimator uses the **Goodman criterion**:

$$\frac{\sigma_a}{S_e} + \frac{\sigma_m}{S_{ut}} = 1 \implies \sigma_{a,eq} = \frac{\sigma_a}{1 - \sigma_m / S_{ut}}$$

For the strain-life path, the **Morrow correction** modifies the elastic term:

$$\varepsilon_a = \frac{\sigma_f' - \sigma_m}{E}(2N_f)^b + \varepsilon_f'(2N_f)^c$$

### Endurance limit and Marin factors

For wrought steels ($S_{ut} \leq 1400\ \mathrm{MPa}$), the rotating-beam endurance limit is estimated as $S_e' \approx 0.5\,S_{ut}$. The in-service endurance limit $S_e$ is then corrected by five Marin modification factors:

$$S_e = k_a\,k_b\,k_c\,k_d\,k_e\,S_e'$$

| Factor | Symbol | Accounts for |
|---|---|---|
| Surface condition | $k_a = a\,S_{ut}^b$ | Ground, machined, hot-rolled, as-forged |
| Size effect | $k_b$ | Larger sections have higher probability of a critical defect |
| Load type | $k_c$ | Bending (1.0), axial (0.85), torsion (0.59) |
| Temperature | $k_d$ | Derating above ~450 °C (not modelled here) |
| Reliability | $k_e$ | Statistical scatter in $S_e$ data ($k_e = 0.814$ at 99%) |

**Note:** aluminium alloys, titanium alloys, and austenitic stainless steels do **not** exhibit a true endurance limit; fatigue strength is quoted at $10^7$–$10^8$ cycles.

## Material library

The estimator ships with **8 engineering materials** spanning four families. All constants are literature-sourced screening values; they are not substitutes for material-certificate data or coupon testing.

### Stress-life and strain-life constants

| Material | Family | $S_{ut}$ (MPa) | $S_y$ (MPa) | $E$ (GPa) | $\sigma_f'$ (MPa) | $\varepsilon_f'$ | $b$ | $c$ |
|---|---|---|---|---|---|---|---|---|
| AISI 1045 (normalized) | Carbon steel | 625 | 530 | 205 | 980 | 0.47 | −0.089 | −0.58 |
| AISI 4140 (Q&T) | Alloy steel | 1 020 | 655 | 210 | 1 500 | 0.26 | −0.095 | −0.59 |
| AISI 1020 (hot-rolled) | Carbon steel | 380 | 210 | 200 | 620 | 0.59 | −0.081 | −0.56 |
| AISI 304 SS (annealed) | Stainless steel | 515 | 205 | 193 | 1 000 | 0.17 | −0.120 | −0.45 |
| Al 6061-T6 | Aluminium | 310 | 276 | 69 | 450 | 0.32 | −0.085 | −0.62 |
| Al 7075-T6 | Aluminium | 572 | 503 | 71.7 | 740 | 0.19 | −0.106 | −0.60 |
| Ti-6Al-4V (annealed) | Titanium | 950 | 880 | 114 | 1 500 | 0.80 | −0.095 | −0.69 |
| EN-GJL-250 gray cast iron | Cast iron | 250 | 165† | 100 | 440 | 0.01 | −0.120 | −0.60 |

† Gray cast iron does not exhibit a well-defined tensile yield point; 165 MPa is a conservative compressive proxy used for yield-exceedance checks only. Cast iron is compressive-dominant: compressive strength is typically 3–4× tensile strength.

**Endurance limit note:** steels with $S_{ut} \leq 1400\ \mathrm{MPa}$ use $S_e' = 0.5\,S_{ut}$. Aluminium alloys, titanium, and stainless steel have no true endurance limit; use results at $10^7$ cycles as a screening proxy.

### Typical applications

Each material entry in the app includes an **ⓘ** tooltip showing 2–3 representative engineering applications. These are displayed in the material selector and are intended to help engineers quickly identify whether a given material is appropriate for their application domain.

## Graphs and what they communicate

- **Wohler S-N curve (log-log):** compares the operating stress point to the stress-life model line.
- **Goodman diagram:** checks whether the current $(\sigma_m,\ \sigma_a)$ point is inside the high-cycle fatigue boundary.
- **Strain-life $\varepsilon$-N curve (log-log):** shows the predicted life from total strain amplitude $\varepsilon_a$ when the strain-life model is selected.
- **Weibull probability plot:** visual fit check for the Weibull trend, with run-out samples shown as censored markers.
- **Weibull survival curve:** reliability $R(N)$ vs cycles, including the selected target-cycle point.
- **Ashby-style material map (log-log):** available through the new `ashby_plot.py` helper for density/property screening, material-family differentiation, and optional performance-index guide lines.

## Project versioning

- The repository now uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
- The single source of truth is the top-level `VERSION` file.
- Runtime code reads that value through `project_version.py`, so the Streamlit title and demo scripts stay synchronized automatically.
- For a release bump:
  1. update `VERSION`,
  2. refresh any README examples that mention the version explicitly,
  3. rerun `python3 -m pytest -q`,
  4. and publish/tag with the same SemVer value.

## Ashby-style interactive plots

Use the new Matplotlib utility module when you want an Ashby-style material-property view alongside the repository's fatigue calculations.

### Features

- log-log axes for wide property ranges,
- material-family coloring/markers,
- optional Ashby performance-index guide lines,
- and **browser-safe HTML tooltips** via `mpld3` (DOM hover tooltips, not alert/confirm/prompt dialogs).

### Example usage

```bash
python3 -m pip install -r requirements.txt
python3 examples/ashby_fatigue_demo.py
```

That example writes:

- `ashby_fatigue_demo.html` for interactive browser review,
- `ashby_fatigue_demo.png` for static sharing.

The HTML tooltips include concise review fields such as material name, key properties, review note, confidence, and source. Common browsers treat them as normal in-page HTML elements, so they are not subject to pop-up blocking rules.

### Reusing the helper in scripts or notebooks

```python
from ashby_plot import AshbyPoint, PerformanceIndexGuide, create_ashby_plot, export_interactive_ashby_html

points = [
    AshbyPoint(
        name="Al 6061-T6",
        family="Aluminum",
        x_value=2.70,
        y_value=96.0,
        key_values={"Sut (MPa)": 310.0},
        review_note="Finite-life follow-up recommended.",
        confidence="Medium",
        source="Repository material library",
    )
]

plot = create_ashby_plot(
    points,
    x_label="Density",
    x_unit="g/cm^3",
    y_label="Fatigue screening strength",
    y_unit="MPa",
    performance_indices=[PerformanceIndexGuide(label="Specific fatigue strength", constant=60.0)],
)
export_interactive_ashby_html(plot, "ashby_plot.html")
```

### Caveats

- Ashby helpers expect strictly positive property values because both axes use logarithmic scaling.
- Tooltip interactivity depends on `mpld3`; if you only need a static figure, save the Matplotlib figure directly instead of exporting HTML.
- Example fatigue-screening values beyond the repository's built-in material library are intentionally lightweight screening references, not certification data.

## Weibull data input format

In the app's reliability section, Weibull estimation is **opt-in** by default.  
Use real fatigue test data for decision support; the app also provides an optional demo dataset loader for quick UI checks.

When enabled, enter one sample per line:

- `25000, fail`
- `80000, runout`

Accepted status tokens:
- failure: `fail`, `failed`, `f`
- right-censored run-out: `runout`, `censored`, `r`

All cycles must be positive.

## Unit handling

- Inputs can be entered in **SI primary** or **Imperial primary** mode.
- The app shows counterpart-unit hints inline (for example mm <-> in, N <-> lbf, N*m <-> lbf*in, MPa <-> ksi).
- Internal fatigue calculations are normalized to a consistent SI base:
  - geometry in mm,
  - force in N,
  - moment in N*mm,
  - stress/strength in MPa.

## Nomenclature and symbols

The app includes a top-level **Nomenclature & Symbols** expander. The README mirrors that notation here for quick reference.

| Symbol | Meaning | Units |
|---|---|---|
| $d$ | Section diameter | mm or in |
| $A$ | Section area | mm$^2$ |
| $F_m,\ F_a$ | Mean and alternating axial force | N or lbf |
| $M_m,\ M_a$ | Mean and alternating bending moment | N*m or lbf*in |
| $\sigma_m,\ \sigma_a$ | Mean and alternating nominal stress | MPa or ksi |
| $\sigma_{a,eq}$ | Goodman-equivalent alternating stress | MPa or ksi |
| $S_{ut}$ | Ultimate tensile strength | MPa or ksi |
| $S_e',\ S_e$ | Uncorrected and corrected endurance limit | MPa or ksi |
| $N_f$ | Cycles to failure | cycles |
| $\varepsilon_a$ | Total strain amplitude | mm/mm |
| $\sigma_f',\ \varepsilon_f',\ b,\ c,\ E$ | Strain-life material constants | -, MPa or ksi |
| $\beta,\ \eta$ | Weibull shape and scale parameters | -, cycles |
| $R(N)$ | Survival probability at cycle count $N$ | 0 to 1 |
| $B_{10},\ B_{50}$ | 10% and 50% failure-life quantiles | cycles |

## Local run

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Then open the local URL shown by Streamlit.

## Tests

```bash
python3 -m pytest -q
```

## Easiest deployment path (immediate publishing)

**Streamlit Community Cloud** is the fastest option for this stack:

1. Push this branch/repo to GitHub.
2. In Streamlit Community Cloud, create a new app from the repo.
3. Set:
   - entrypoint: `app.py`
   - Python dependencies: `requirements.txt`
4. Deploy.

For production hardening later, Render/Fly/other container-hosted options are straightforward from the same app.

## Assumptions and current limits

- Uniaxial nominal stress approach on a solid round section.
- Strain-life path assumes stabilized constant-amplitude cycling and Morrow mean-stress correction in the elastic term.
- Weibull path assumes a two-parameter Weibull distribution and non-informative right-censoring.
- No notch sensitivity, residual stress, corrosion, temperature derating, multiaxial effects, or variable-amplitude rainflow analysis.
- Best used for **screening and comparison**, not final design sign-off.

## Extension path (part-based defaults)

The current code is structured to allow a part catalog layer next:

- map part IDs to default geometry/material/surface settings,
- prefill those defaults in UI,
- keep values user-overridable for what-if exploration.

## Materials-selection scaffold (Ashby, new)

This repository now includes a **first-phase scaffold** for engineering materials selection with fatigue-aware properties:

- `materials_selection_types.py`: typed domain records for material identity, mechanical properties, fatigue descriptors, constraints, criteria, and Ashby payload shapes.
- `materials_selection_service.py`: selection/constraint engine shell with explicit TODO placeholders for calibrated weighting, normalization, and uncertainty-aware ranking.
- `ashby_plot_adapter.py`: plotting adapter shell that maps selected material properties to Ashby-like x/y payload points and highlight flags.
- `materials_selection_stubs.py`: tiny synthetic input stubs demonstrating expected request/material schema.
- `app.py`: a discoverability section in Streamlit ("Materials selection scaffold (Ashby)") showing scaffold inputs, deterministic baseline ranking output, and payload preview.

### What is intentionally not finalized yet

- No literature-grounded calibration of fatigue-property distributions.
- No validated multi-objective optimization/weighting policy.
- No final plotting style/class envelopes/Pareto overlays.
- No claim that scaffold outputs are design-certification quality.

### How to extend in the next phase

1. Replace synthetic stubs with curated literature/experiment-backed datasets.
2. Implement and validate domain-approved weighting and constraint semantics.
3. Plug Ashby payload output into finalized plotting routines and design-space overlays.
4. Add uncertainty handling and regression tests against benchmark case studies.
