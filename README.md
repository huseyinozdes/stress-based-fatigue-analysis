# Stress-Based Fatigue Analysis — Web Estimator v2

This repository now includes a lightweight web app for quick-reference fatigue-life estimation.

**Live App:** [https://stressbasedfatigue.streamlit.app](https://stressbasedfatigue.streamlit.app)

## What this v2 tool does

- Collects core engineering inputs: **material**, **section diameter**, **axial force**, **bending moment**, and fatigue modifiers.
- Supports two model paths:
  - **Stress-life (S-N)** for high-cycle screening,
  - **Strain-life (epsilon-N)** using Manson-Coffin-Basquin style estimation.
- Adds optional **statistical reliability** from fatigue test data using two-parameter Weibull MLE with right-censored run-outs.
- Reports:
  - estimated life (cycles),
  - key intermediate values (Marin factors, endurance limits, Goodman-adjusted stress, Basquin coefficients),
  - engineering graphs (S-N, Goodman, epsilon-N, Weibull probability, Weibull survival),
  - assumptions and caution notes.

## Implemented equations/model

The estimator uses standard stress-life and strain-life workflows aligned with practical machine design methods:

1. **Section stress (MPa)**
   - Area: `A = pi*d^2/4`
   - Axial stress: `sigma = F/A`
   - Bending stress: `sigma = 32*M/(pi*d^3)`
   - Mean and alternating nominal stress are summed from axial + bending parts.

2. **Endurance limit**
   - Rotating-beam baseline: `Se' = 0.5*Sut` (capped at 700 MPa for high Sut).
   - Marin corrections: `Se = ka*kb*kc*kd*ke*kf*Se'`
     - `ka`: surface finish (Shigley-style fit)
     - `kb`: size factor from diameter
     - `kc`: load factor (bending/axial)
     - `kd`: temperature (fixed as 1.0 in v1)
     - `ke`: reliability factor
     - `kf`: user-provided miscellaneous factor

3. **Mean stress correction**
   - Goodman: `sigma_a,eq = sigma_a / (1 - sigma_m/Sut)`

4. **Stress-life estimation**
   - Basquin line between:
     - `N=1e3` at `Sf=0.9*Sut`
     - `N=1e6` at `Sf=Se`
   - Solve `Sf(N)=a*N^b` for `N` using `sigma_a,eq`.

5. **Strain-life estimation (Manson-Coffin-Basquin with Morrow correction)**
   - `epsilon_a = ((sigma_f' - sigma_m)/E) * (2N)^b + epsilon_f' * (2N)^c`
   - Solves for `N` from the user-specified total strain amplitude `epsilon_a`.
   - Requires: `E`, `sigma_f'`, `epsilon_f'`, `b`, `c`.

6. **Weibull reliability estimation with censoring**
   - Two-parameter Weibull minimum:
     - Failure CDF: `F(N) = 1 - exp(-(N/eta)^beta)`
     - Survival: `R(N) = exp(-(N/eta)^beta)`
   - Uses maximum likelihood with right-censored run-outs:
     - failures contribute Weibull PDF terms,
     - run-outs contribute survival terms.
   - Reliability metrics:
     - `B10`: life at 10% cumulative failure probability,
     - `B50`: median life,
     - survival at user-selected target cycle count.

## Graphs and what they communicate

- **Wohler S-N curve (log-log):** compares the operating stress point to the stress-life model line.
- **Goodman diagram:** checks whether the current mean/alternating stress point is inside the high-cycle fatigue boundary.
- **Strain-life epsilon-N curve (log-log):** shows the predicted life from total strain amplitude when the strain-life model is selected.
- **Weibull probability plot:** visual fit check for Weibull trend, with run-out samples shown as censored markers.
- **Weibull survival curve:** reliability `R(N)` vs cycles, including the selected target-cycle point.

## Weibull data input format

In the app's reliability section, enter one sample per line:

- `25000, fail`
- `80000, runout`

Accepted status tokens:
- failure: `fail`, `failed`, `f`
- right-censored run-out: `runout`, `censored`, `r`

All cycles must be positive.

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
