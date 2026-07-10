# Stress-Based Fatigue Analysis — Web Estimator v2

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

## Graphs and what they communicate

- **Wohler S-N curve (log-log):** compares the operating stress point to the stress-life model line.
- **Goodman diagram:** checks whether the current $(\sigma_m,\ \sigma_a)$ point is inside the high-cycle fatigue boundary.
- **Strain-life $\varepsilon$-N curve (log-log):** shows the predicted life from total strain amplitude $\varepsilon_a$ when the strain-life model is selected.
- **Weibull probability plot:** visual fit check for the Weibull trend, with run-out samples shown as censored markers.
- **Weibull survival curve:** reliability $R(N)$ vs cycles, including the selected target-cycle point.

## Weibull data input format

In the app's reliability section, enter one sample per line:

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
