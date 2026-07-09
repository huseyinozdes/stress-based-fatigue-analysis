from __future__ import annotations

from math import log

import altair as alt
import streamlit as st

from fatigue_model import (
    LOAD_FACTOR,
    MATERIALS,
    RELIABILITY_FACTOR,
    STRAIN_LIFE_DEFAULTS,
    SURFACE_FINISH_COEFFICIENTS,
    FatigueInput,
    StrainLifeInput,
    WeibullObservation,
    estimate_fatigue_life,
    estimate_strain_life,
    estimate_weibull_life,
    parse_weibull_observations,
    weibull_survival_probability,
)
from units import (
    UnitSystem,
    ksi_to_mpa,
    lbfin_to_nm,
    mpa_to_ksi,
    mm_to_in,
    n_to_lbf,
    nm_to_lbfin,
    normalize_geometry_load_inputs,
    strain_to_microstrain,
)
from project_version import PROJECT_VERSION


def _logspace_10(start_exp: float, end_exp: float, points: int) -> list[float]:
    if points < 2:
        return [10**start_exp]
    step = (end_exp - start_exp) / (points - 1)
    return [10 ** (start_exp + i * step) for i in range(points)]


def _format_conversion_hint(value: float, unit: str) -> str:
    return f"({value:,.3f} {unit})"


def _stress_primary_with_hint(stress_mpa: float, unit_system: UnitSystem) -> tuple[str, str]:
    if unit_system == "SI":
        return f"{stress_mpa:.1f} MPa", _format_conversion_hint(mpa_to_ksi(stress_mpa), "ksi")
    return f"{mpa_to_ksi(stress_mpa):.2f} ksi", _format_conversion_hint(stress_mpa, "MPa")


def _normalize_error_for_units(message: str, unit_system: UnitSystem) -> str:
    if unit_system == "SI":
        return message
    mapped = message.replace("MPa", "ksi (internally converted to MPa)")
    mapped = mapped.replace("mm", "in (internally converted to mm)")
    return mapped


def _sn_curve_data(stress_result: object, unit_system: UnitSystem) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for n in _logspace_10(3.0, 8.0, 80):
        if n <= 1.0e6:
            stress_mpa = stress_result.basquin_a * (n**stress_result.basquin_b)
        else:
            stress_mpa = stress_result.endurance_limit_mpa
        stress_display = stress_mpa if unit_system == "SI" else mpa_to_ksi(stress_mpa)
        data.append({"cycles": n, "stress": stress_display, "series": "S-N model"})
    return data


def _goodman_data(sut_mpa: float, se_mpa: float, unit_system: UnitSystem) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for i in range(120):
        sigma_m = sut_mpa * i / 119.0
        sigma_a = se_mpa * max(1.0 - sigma_m / sut_mpa, 0.0)
        if unit_system == "SI":
            sigma_m_display = sigma_m
            sigma_a_display = sigma_a
        else:
            sigma_m_display = mpa_to_ksi(sigma_m)
            sigma_a_display = mpa_to_ksi(sigma_a)
        data.append({"sigma_m": sigma_m_display, "sigma_a": sigma_a_display, "series": "Goodman boundary"})
    return data


def _epsilon_n_data(strain_inputs: StrainLifeInput, sigma_mean_mpa: float) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for n in _logspace_10(0.0, 8.0, 80):
        reversals = 2.0 * n
        elastic = max(strain_inputs.sigma_f_prime_mpa - sigma_mean_mpa, 0.0) / strain_inputs.elastic_modulus_mpa * (
            reversals**strain_inputs.basquin_b
        )
        plastic = strain_inputs.epsilon_f_prime * (reversals**strain_inputs.coffin_c)
        total = elastic + plastic
        data.append({"cycles": n, "strain": total, "series": "Total strain amplitude"})
    return data


def _weibull_probability_data(
    observations: list[WeibullObservation],
    beta_shape: float,
    eta_scale_cycles: float,
) -> tuple[list[dict[str, float | str]], list[dict[str, float | str]], list[dict[str, float | str]]]:
    model_line: list[dict[str, float | str]] = []
    for n in _logspace_10(3.0, 8.0, 100):
        failure_probability = 1.0 - weibull_survival_probability(n, beta_shape, eta_scale_cycles)
        y_weibull = log(-log(1.0 - min(max(failure_probability, 1e-6), 1.0 - 1e-6)))
        model_line.append({"ln_cycles": log(n), "weibull_y": y_weibull, "series": "Fitted Weibull"})

    failures = sorted(obs.cycles for obs in observations if obs.failed)
    failure_points: list[dict[str, float | str]] = []
    runout_points: list[dict[str, float | str]] = []

    for idx, cycles in enumerate(failures, start=1):
        plotting_f = (idx - 0.3) / (len(failures) + 0.4)
        y_weibull = log(-log(1.0 - min(max(plotting_f, 1e-6), 1.0 - 1e-6)))
        failure_points.append({"ln_cycles": log(cycles), "weibull_y": y_weibull, "series": "Failed data"})

    y_runout = min((row["weibull_y"] for row in model_line), default=-4.0) - 0.4
    for obs in observations:
        if not obs.failed:
            runout_points.append({"ln_cycles": log(obs.cycles), "weibull_y": y_runout, "series": "Run-out (censored)"})

    return model_line, failure_points, runout_points


def _weibull_survival_curve_data(beta_shape: float, eta_scale_cycles: float) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for n in _logspace_10(3.0, 8.0, 100):
        data.append(
            {
                "cycles": n,
                "survival": weibull_survival_probability(n, beta_shape, eta_scale_cycles),
                "series": "Reliability curve",
            }
        )
    return data


def _nomenclature_rows() -> list[tuple[str, str, str]]:
    return [
        (r"$d$", "Section diameter", "mm or in"),
        (r"$A$", "Section area", r"mm$^2$"),
        (r"$F_m,\ F_a$", "Mean and alternating axial force", "N or lbf"),
        (r"$M_m,\ M_a$", "Mean and alternating bending moment", "N*m or lbf*in"),
        (r"$\sigma_m,\ \sigma_a$", "Mean and alternating nominal stress", "MPa or ksi"),
        (r"$\sigma_{a,eq}$", "Goodman-equivalent alternating stress", "MPa or ksi"),
        (r"$S_{ut}$", "Ultimate tensile strength", "MPa or ksi"),
        (r"$S_e',\ S_e$", "Uncorrected and corrected endurance limit", "MPa or ksi"),
        (r"$N_f$", "Cycles to failure", "cycles"),
        (r"$\varepsilon_a$", "Total strain amplitude", "mm/mm"),
        (r"$\sigma_f',\ \varepsilon_f',\ b,\ c,\ E$", "Strain-life material constants", "-, MPa or ksi"),
        (r"$\beta,\ \eta$", "Weibull shape and scale parameters", "-, cycles"),
        (r"$R(N)$", "Survival probability at cycle count $N$", "0 to 1"),
        (r"$B_{10},\ B_{50}$", "10% and 50% failure-life quantiles", "cycles"),
    ]


def _render_nomenclature() -> None:
    rows = _nomenclature_rows()
    header = "| Symbol | Meaning | Units |\n|---|---|---|\n"
    body = "\n".join(f"| {symbol} | {meaning} | {units} |" for symbol, meaning, units in rows)
    st.markdown(header + body)


st.set_page_config(page_title=f"Fatigue Life Estimator (v{PROJECT_VERSION})", layout="wide")
st.title(f"Fatigue Life Estimator (v{PROJECT_VERSION})")
st.caption("Quick engineering fatigue estimator for screening decisions. Results are estimates, not design certification.")

unit_mode_label = st.radio("Primary input units", ["SI primary", "Imperial primary"], horizontal=True)
unit_system: UnitSystem = "SI" if unit_mode_label == "SI primary" else "Imperial"

with st.expander("Model options", expanded=False):
    st.markdown(
        """
        - **Stress-life (S-N):** Basquin + Marin factors + Goodman correction using $\\sigma_a,\\sigma_m,S_e,S_{ut},N_f$
        - **Strain-life (epsilon-N):** Manson-Coffin-Basquin with Morrow correction using $\\varepsilon_a,\\sigma_f',\\varepsilon_f',b,c,E$
        - **Reliability statistics:** two-parameter Weibull with right-censored run-out handling
        """
    )

with st.expander("Nomenclature & Symbols", expanded=False):
    st.caption("Thesis nomenclature source was not found in this repository, so this panel uses the app's model-based baseline nomenclature.")
    _render_nomenclature()

model_mode = st.radio(
    "Select deterministic model",
    ["Stress-life (S-N)", "Strain-life (epsilon-N)"],
    horizontal=True,
)

if unit_system == "SI":
    diameter_default = 12.0
    force_mean_default = 2_000.0
    force_alt_default = 1_000.0
    moment_mean_default = 10.0
    moment_alt_default = 8.0
    diameter_unit = "mm"
    force_unit = "N"
    moment_unit = "N*m"
else:
    diameter_default = mm_to_in(12.0)
    force_mean_default = n_to_lbf(2_000.0)
    force_alt_default = n_to_lbf(1_000.0)
    moment_mean_default = nm_to_lbfin(10.0)
    moment_alt_default = nm_to_lbfin(8.0)
    diameter_unit = "in"
    force_unit = "lbf"
    moment_unit = "lbf*in"

col1, col2 = st.columns(2)
with col1:
    material_name = st.selectbox("Material", list(MATERIALS.keys()), index=0)
    diameter_value = st.number_input(
        f"Section diameter, d ({diameter_unit})",
        min_value=0.001,
        value=float(diameter_default),
        step=0.1 if unit_system == "SI" else 0.01,
        help="Nominal round-section diameter used for area and bending stress calculations.",
    )
    if unit_system == "SI":
        st.caption(_format_conversion_hint(mm_to_in(diameter_value), "in"))
    else:
        st.caption(_format_conversion_hint(diameter_value * 25.4, "mm"))
    st.markdown(r"Small-note symbol: $d$; area relation $A=\pi d^2/4$")

    surface_finish = st.selectbox("Surface finish", list(SURFACE_FINISH_COEFFICIENTS.keys()), index=1)
    reliability = st.selectbox("Reliability (%)", list(RELIABILITY_FACTOR.keys()), index=2)
    load_type = st.selectbox("Primary loading type for kc", list(LOAD_FACTOR.keys()), index=0)
    k_misc = st.number_input(
        "Miscellaneous Marin factor, kf",
        min_value=0.1,
        max_value=1.5,
        value=1.0,
        step=0.01,
        help="Dimensionless correction factor for effects not explicitly modeled.",
    )

with col2:
    st.subheader("Loading inputs")
    st.caption(f"Primary units: force in {force_unit}, moment in {moment_unit}.")
    axial_mean_value = st.number_input(
        f"Mean axial force, Fm ({force_unit})",
        min_value=0.0,
        value=float(force_mean_default),
        step=100.0 if unit_system == "SI" else 10.0,
        help="Mean (steady) axial load component.",
    )
    if unit_system == "SI":
        st.caption(_format_conversion_hint(n_to_lbf(axial_mean_value), "lbf"))
    else:
        st.caption(_format_conversion_hint(axial_mean_value * 4.4482216152605, "N"))
    st.markdown(r"Symbol mapping: $F_m$ is mean load.")

    axial_alt_value = st.number_input(
        f"Alternating axial force amplitude, Fa ({force_unit})",
        min_value=0.0,
        value=float(force_alt_default),
        step=100.0 if unit_system == "SI" else 10.0,
        help="Alternating axial load amplitude. Use positive amplitude magnitude.",
    )
    if unit_system == "SI":
        st.caption(_format_conversion_hint(n_to_lbf(axial_alt_value), "lbf"))
    else:
        st.caption(_format_conversion_hint(axial_alt_value * 4.4482216152605, "N"))
    st.markdown(r"Symbol mapping: $F_a$ is alternating amplitude.")

    moment_mean_value = st.number_input(
        f"Mean bending moment, Mm ({moment_unit})",
        min_value=0.0,
        value=float(moment_mean_default),
        step=0.5 if unit_system == "SI" else 5.0,
        help="Mean bending moment component about the critical section.",
    )
    if unit_system == "SI":
        st.caption(_format_conversion_hint(nm_to_lbfin(moment_mean_value), "lbf*in"))
    else:
        st.caption(_format_conversion_hint(lbfin_to_nm(moment_mean_value), "N*m"))
    st.markdown(r"Symbol mapping: $M_m$ is mean bending moment.")

    moment_alt_value = st.number_input(
        f"Alternating bending moment amplitude, Ma ({moment_unit})",
        min_value=0.0,
        value=float(moment_alt_default),
        step=0.5 if unit_system == "SI" else 5.0,
        help="Alternating bending moment amplitude. Use positive amplitude magnitude.",
    )
    if unit_system == "SI":
        st.caption(_format_conversion_hint(nm_to_lbfin(moment_alt_value), "lbf*in"))
    else:
        st.caption(_format_conversion_hint(lbfin_to_nm(moment_alt_value), "N*m"))
    st.markdown(r"Symbol mapping: $M_a$ is alternating bending moment amplitude.")

st.markdown("##### Input quick guide")
g1, g2 = st.columns(2)
with g1:
    st.info("Geometry: $d$ defines area $A=\\pi d^2/4$.\n\nAxial load: $F_m$ is mean, $F_a$ is alternating amplitude.")
with g2:
    st.info("Bending: $M_m$ is mean, $M_a$ is alternating amplitude.\n\nUse positive amplitudes for alternating terms.")

strain_inputs: StrainLifeInput | None = None
if model_mode == "Strain-life (epsilon-N)":
    defaults = STRAIN_LIFE_DEFAULTS[material_name]
    st.subheader("Strain-life constants (Manson-Coffin-Basquin)")

    if unit_system == "SI":
        e_default = defaults["elastic_modulus_mpa"]
        sigmaf_default = defaults["sigma_f_prime_mpa"]
        stress_constant_unit = "MPa"
    else:
        e_default = mpa_to_ksi(defaults["elastic_modulus_mpa"])
        sigmaf_default = mpa_to_ksi(defaults["sigma_f_prime_mpa"])
        stress_constant_unit = "ksi"

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        elastic_modulus_value = st.number_input(
            f"Elastic modulus, E ({stress_constant_unit})",
            min_value=1.0,
            value=float(e_default),
            step=1000.0 if unit_system == "SI" else 100.0,
            help="Young's modulus used for elastic strain term.",
        )
        if unit_system == "SI":
            st.caption(_format_conversion_hint(mpa_to_ksi(elastic_modulus_value), "ksi"))
        else:
            st.caption(_format_conversion_hint(ksi_to_mpa(elastic_modulus_value), "MPa"))

        sigma_f_prime_value = st.number_input(
            f"Fatigue strength coefficient, sigma_f' ({stress_constant_unit})",
            min_value=0.1,
            value=float(sigmaf_default),
            step=10.0 if unit_system == "SI" else 1.0,
            help="Material fatigue strength coefficient from strain-controlled tests.",
        )
        if unit_system == "SI":
            st.caption(_format_conversion_hint(mpa_to_ksi(sigma_f_prime_value), "ksi"))
        else:
            st.caption(_format_conversion_hint(ksi_to_mpa(sigma_f_prime_value), "MPa"))

    with sc2:
        epsilon_f_prime = st.number_input(
            "Fatigue ductility coefficient, epsilon_f' (-)",
            min_value=0.001,
            value=float(defaults["epsilon_f_prime"]),
            step=0.01,
            format="%.4f",
            help="Fatigue ductility coefficient in Manson-Coffin term.",
        )
        st.caption(_format_conversion_hint(strain_to_microstrain(epsilon_f_prime), "microstrain"))
        basquin_b = st.number_input(
            "Basquin exponent, b (-)",
            min_value=-1.0,
            max_value=-0.0001,
            value=float(defaults["basquin_b"]),
            step=0.005,
            format="%.4f",
            help="Negative exponent for elastic strain-life slope.",
        )

    with sc3:
        coffin_c = st.number_input(
            "Coffin-Manson exponent, c (-)",
            min_value=-2.0,
            max_value=-0.0001,
            value=float(defaults["coffin_c"]),
            step=0.01,
            format="%.4f",
            help="Negative exponent for plastic strain-life slope.",
        )
        total_strain_amp_percent = st.number_input(
            "Total strain amplitude, epsilon_a (%)",
            min_value=0.001,
            max_value=50.0,
            value=0.30,
            step=0.01,
            format="%.4f",
            help="Total imposed strain amplitude. Example: 0.30% equals 3000 microstrain.",
        )
        st.caption(_format_conversion_hint(total_strain_amp_percent * 10_000.0, "microstrain"))
        st.markdown(r"Symbols: $\varepsilon_a,\ \sigma_f',\ \varepsilon_f',\ b,\ c,\ E$")

st.subheader("Reliability statistics (optional)")
enable_weibull = st.checkbox("Enable Weibull reliability estimation (with run-out censoring)", value=True)
weibull_data_text = ""
target_cycles_reliability = 100_000.0
if enable_weibull:
    st.caption("Enter one sample per line: '<cycles>, <status>' where status is fail/failed/f or runout/censored/r.")
    weibull_data_text = st.text_area(
        "Fatigue test data",
        value="25000, fail\n40000, fail\n60000, fail\n85000, runout\n120000, runout",
        height=120,
    )
    target_cycles_reliability = st.number_input(
        "Target cycles for survival probability",
        min_value=1.0,
        value=100_000.0,
        step=10_000.0,
    )

if st.button("Estimate fatigue life", type="primary"):
    normalized = normalize_geometry_load_inputs(
        unit_system,
        diameter_value=diameter_value,
        axial_mean_value=axial_mean_value,
        axial_alt_value=axial_alt_value,
        moment_mean_value=moment_mean_value,
        moment_alt_value=moment_alt_value,
    )

    fatigue_inputs = FatigueInput(
        material=MATERIALS[material_name],
        diameter_mm=normalized["diameter_mm"],
        axial_force_mean_n=normalized["axial_force_mean_n"],
        axial_force_alt_n=normalized["axial_force_alt_n"],
        bending_moment_mean_nmm=normalized["bending_moment_mean_nmm"],
        bending_moment_alt_nmm=normalized["bending_moment_alt_nmm"],
        surface_finish=surface_finish,
        reliability_percent=reliability,
        load_type=load_type,
        miscellaneous_factor=k_misc,
    )

    try:
        stress_result = estimate_fatigue_life(fatigue_inputs)
        deterministic_estimate: float | None = stress_result.estimated_cycles
        deterministic_label = stress_result.life_label
        strain_result = None
        if model_mode == "Strain-life (epsilon-N)":
            if unit_system == "SI":
                elastic_modulus_mpa = elastic_modulus_value
                sigma_f_prime_mpa = sigma_f_prime_value
            else:
                elastic_modulus_mpa = ksi_to_mpa(elastic_modulus_value)
                sigma_f_prime_mpa = ksi_to_mpa(sigma_f_prime_value)

            strain_inputs = StrainLifeInput(
                stress_input=fatigue_inputs,
                elastic_modulus_mpa=elastic_modulus_mpa,
                sigma_f_prime_mpa=sigma_f_prime_mpa,
                epsilon_f_prime=epsilon_f_prime,
                basquin_b=basquin_b,
                coffin_c=coffin_c,
                total_strain_amplitude=total_strain_amp_percent / 100.0,
            )
            strain_result = estimate_strain_life(strain_inputs)
            deterministic_estimate = strain_result.estimated_cycles
            deterministic_label = strain_result.life_label

        weibull_result = None
        weibull_observations: list[WeibullObservation] = []
        if enable_weibull:
            weibull_observations = parse_weibull_observations(weibull_data_text)
            weibull_result = estimate_weibull_life(weibull_observations, target_cycles_reliability)

        st.subheader("Verdict")
        vc1, vc2 = st.columns(2)
        with vc1:
            if deterministic_estimate is None:
                st.success("Deterministic estimate: high/very-high cycle regime")
            else:
                st.success(f"Deterministic estimate: {deterministic_estimate:,.0f} cycles")
            st.caption(f"Deterministic model verdict: {deterministic_label}")
        with vc2:
            if weibull_result is None:
                st.info("Statistical estimate: not enabled")
                st.caption("Enable Weibull section to estimate B-life and reliability from test data.")
            else:
                st.success(f"Statistical estimate: B10 = {weibull_result.b10_cycles:,.0f} cycles")
                st.caption(
                    f"Weibull MLE with censoring: $R(N)$ at {weibull_result.target_cycles:,.0f} cycles = "
                    f"{weibull_result.survival_at_target*100:.1f}%"
                )

        st.subheader("Key metrics")
        km1, km2, km3, km4 = st.columns(4)
        with km1:
            val, hint = _stress_primary_with_hint(stress_result.sigma_mean_mpa, unit_system)
            st.metric("Mean stress, sigma_m", val)
            st.caption(hint)
            st.markdown(r"Symbol: $\sigma_m$")
        with km2:
            val, hint = _stress_primary_with_hint(stress_result.sigma_alt_mpa, unit_system)
            st.metric("Alternating stress, sigma_a", val)
            st.caption(hint)
            st.markdown(r"Symbol: $\sigma_a$")
        with km3:
            val, hint = _stress_primary_with_hint(stress_result.sigma_alt_goodman_mpa, unit_system)
            st.metric("Goodman-adjusted stress, sigma_a,eq", val)
            st.caption(hint)
            st.markdown(r"Symbol: $\sigma_{a,eq}$")
        with km4:
            val, hint = _stress_primary_with_hint(stress_result.endurance_limit_mpa, unit_system)
            st.metric("Corrected endurance limit, Se", val)
            st.caption(hint)
            st.markdown(r"Symbols: $S_e,\ S_e'$")

        st.subheader("Engineering plots")
        stress_axis_unit = "MPa" if unit_system == "SI" else "ksi"
        gc1, gc2 = st.columns(2)

        with gc1:
            sn_line = _sn_curve_data(stress_result, unit_system)
            sn_point_cycles = deterministic_estimate if deterministic_estimate is not None else 1.0e6
            stress_point = (
                stress_result.sigma_alt_goodman_mpa
                if unit_system == "SI"
                else mpa_to_ksi(stress_result.sigma_alt_goodman_mpa)
            )
            sn_point = [
                {
                    "cycles": max(sn_point_cycles, 1.0e3),
                    "stress": stress_point,
                    "series": "Operating point",
                }
            ]
            sn_chart = (
                alt.Chart(alt.Data(values=sn_line))
                .mark_line()
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("stress:Q", scale=alt.Scale(type="log"), title=f"Stress amplitude sigma_a, {stress_axis_unit}"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                )
                + alt.Chart(alt.Data(values=sn_point))
                .mark_point(size=140, filled=True)
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("stress:Q", scale=alt.Scale(type="log"), title=f"Stress amplitude sigma_a, {stress_axis_unit}"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    tooltip=["cycles:Q", "stress:Q", "series:N"],
                )
            ).properties(title="Wohler S-N curve: sigma_a vs N_f (log-log)", height=320)
            st.altair_chart(sn_chart, use_container_width=True)
            st.caption("The point above the curve indicates a short-life condition; below it indicates longer life.")

        with gc2:
            goodman_line = _goodman_data(fatigue_inputs.material.sut_mpa, stress_result.endurance_limit_mpa, unit_system)
            sigma_m_point = stress_result.sigma_mean_mpa if unit_system == "SI" else mpa_to_ksi(stress_result.sigma_mean_mpa)
            sigma_a_point = stress_result.sigma_alt_mpa if unit_system == "SI" else mpa_to_ksi(stress_result.sigma_alt_mpa)
            goodman_point = [{"sigma_m": sigma_m_point, "sigma_a": sigma_a_point, "series": "Operating point"}]
            goodman_chart = (
                alt.Chart(alt.Data(values=goodman_line))
                .mark_line()
                .encode(
                    x=alt.X("sigma_m:Q", title=f"Mean stress sigma_m ({stress_axis_unit})"),
                    y=alt.Y("sigma_a:Q", title=f"Alternating stress sigma_a ({stress_axis_unit})"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                )
                + alt.Chart(alt.Data(values=goodman_point))
                .mark_point(size=140, filled=True)
                .encode(
                    x=alt.X("sigma_m:Q", title=f"Mean stress sigma_m ({stress_axis_unit})"),
                    y=alt.Y("sigma_a:Q", title=f"Alternating stress sigma_a ({stress_axis_unit})"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    tooltip=["sigma_m:Q", "sigma_a:Q", "series:N"],
                )
            ).properties(title="Goodman diagram: sigma_a vs sigma_m", height=320)
            st.altair_chart(goodman_chart, use_container_width=True)
            st.caption("Points above the boundary are outside the allowable high-cycle fatigue envelope.")

        if model_mode == "Strain-life (epsilon-N)" and strain_inputs is not None and strain_result is not None:
            epsilon_line = _epsilon_n_data(strain_inputs, strain_result.stress_state.sigma_mean_mpa)
            epsilon_point_cycles = strain_result.estimated_cycles if strain_result.estimated_cycles is not None else 1.0e8
            epsilon_point = [
                {
                    "cycles": max(epsilon_point_cycles, 1.0),
                    "strain": strain_inputs.total_strain_amplitude,
                    "series": "Operating point",
                }
            ]
            epsilon_chart = (
                alt.Chart(alt.Data(values=epsilon_line))
                .mark_line()
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("strain:Q", scale=alt.Scale(type="log"), title="Strain amplitude epsilon_a (mm/mm)"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                )
                + alt.Chart(alt.Data(values=epsilon_point))
                .mark_point(size=140, filled=True)
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("strain:Q", scale=alt.Scale(type="log"), title="Strain amplitude epsilon_a (mm/mm)"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    tooltip=["cycles:Q", "strain:Q", "series:N"],
                )
            ).properties(title="Strain-life curve: epsilon_a vs N_f (log-log)", height=320)
            st.altair_chart(epsilon_chart, use_container_width=True)
            st.caption("This curve blends elastic and plastic strain contributions to estimate low-to-high cycle life.")

            st.subheader("Strain-life details")
            sd1, sd2 = st.columns(2)
            with sd1:
                st.metric("Elastic strain component", f"{strain_result.elastic_strain_component:.5f} mm/mm")
                st.caption(_format_conversion_hint(strain_to_microstrain(strain_result.elastic_strain_component), "microstrain"))
                st.metric("Plastic strain component", f"{strain_result.plastic_strain_component:.5f} mm/mm")
                st.caption(_format_conversion_hint(strain_to_microstrain(strain_result.plastic_strain_component), "microstrain"))
            with sd2:
                st.metric("Input total strain amplitude", f"{strain_inputs.total_strain_amplitude:.5f} mm/mm")
                st.caption(_format_conversion_hint(strain_to_microstrain(strain_inputs.total_strain_amplitude), "microstrain"))
                val, hint = _stress_primary_with_hint(strain_result.sigma_alt_goodman_mpa, unit_system)
                st.metric("Goodman-adjusted stress, sigma_a,eq", val)
                st.caption(hint)
            assumptions = stress_result.notes + strain_result.notes
        else:
            assumptions = stress_result.notes

        if weibull_result is not None:
            st.subheader("Statistical reliability (Weibull with censoring)")
            wr1, wr2, wr3, wr4 = st.columns(4)
            with wr1:
                st.metric("Shape, beta", f"{weibull_result.beta_shape:.3f}")
                st.metric("Scale life, eta", f"{weibull_result.eta_scale_cycles:,.0f} cycles")
            with wr2:
                st.metric("B10 life, B10", f"{weibull_result.b10_cycles:,.0f} cycles")
                st.metric("B50 life, B50", f"{weibull_result.b50_cycles:,.0f} cycles")
            with wr3:
                st.metric(
                    f"Survival R(N) at {weibull_result.target_cycles:,.0f}",
                    f"{weibull_result.survival_at_target*100:.1f}%",
                )
                st.metric("Failed samples", f"{weibull_result.failure_count}")
            with wr4:
                st.metric("Censored run-outs", f"{weibull_result.censored_count}")
                st.metric("Total samples", f"{weibull_result.sample_count}")

            wp1, wp2 = st.columns(2)
            with wp1:
                model_line, failure_points, runout_points = _weibull_probability_data(
                    weibull_observations,
                    weibull_result.beta_shape,
                    weibull_result.eta_scale_cycles,
                )
                weibull_prob_chart = (
                    alt.Chart(alt.Data(values=model_line))
                    .mark_line()
                    .encode(
                        x=alt.X("ln_cycles:Q", title="ln(cycles), ln(N)"),
                        y=alt.Y("weibull_y:Q", title="ln(-ln(1-F))"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                    + alt.Chart(alt.Data(values=failure_points))
                    .mark_point(size=100, filled=True)
                    .encode(
                        x=alt.X("ln_cycles:Q", title="ln(cycles), ln(N)"),
                        y=alt.Y("weibull_y:Q", title="ln(-ln(1-F))"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                    + alt.Chart(alt.Data(values=runout_points))
                    .mark_point(size=90, shape="triangle")
                    .encode(
                        x=alt.X("ln_cycles:Q", title="ln(cycles), ln(N)"),
                        y=alt.Y("weibull_y:Q", title="ln(-ln(1-F))"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                ).properties(title="Weibull probability plot: ln(-ln(1-F)) vs ln(N)", height=320)
                st.altair_chart(weibull_prob_chart, use_container_width=True)
                st.caption("Linearity on Weibull coordinates indicates fit quality; triangles mark right-censored run-outs.")

            with wp2:
                survival_line = _weibull_survival_curve_data(
                    weibull_result.beta_shape,
                    weibull_result.eta_scale_cycles,
                )
                target_point = [
                    {
                        "cycles": weibull_result.target_cycles,
                        "survival": weibull_result.survival_at_target,
                        "series": "Target point",
                    }
                ]
                survival_chart = (
                    alt.Chart(alt.Data(values=survival_line))
                    .mark_line()
                    .encode(
                        x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles, N"),
                        y=alt.Y("survival:Q", title="Survival probability R(N)"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                    + alt.Chart(alt.Data(values=target_point))
                    .mark_point(size=140, filled=True)
                    .encode(
                        x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles, N"),
                        y=alt.Y("survival:Q", title="Survival probability R(N)"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                ).properties(title="Weibull survival curve: R(N) vs N", height=320)
                st.altair_chart(survival_chart, use_container_width=True)
                st.caption("Use this curve to compare reliability targets against required service-life cycles.")

            assumptions = assumptions + weibull_result.notes

        st.subheader("Assumptions and cautions")
        st.caption(r"Notation context: $\sigma_m,\sigma_a,\sigma_{a,eq},S_e,N_f,\varepsilon_a,\beta,\eta,R(N)$")
        st.warning("Use this output for screening and part-selection guidance, then validate with detailed fatigue data.")
        for note in assumptions:
            st.write(f"- {note}")
    except ValueError as exc:
        st.error(_normalize_error_for_units(str(exc), unit_system))
