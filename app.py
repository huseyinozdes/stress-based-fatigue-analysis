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


def _logspace_10(start_exp: float, end_exp: float, points: int) -> list[float]:
    if points < 2:
        return [10**start_exp]
    step = (end_exp - start_exp) / (points - 1)
    return [10 ** (start_exp + i * step) for i in range(points)]


def _sn_curve_data(stress_result: object) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for n in _logspace_10(3.0, 8.0, 80):
        if n <= 1.0e6:
            stress = stress_result.basquin_a * (n**stress_result.basquin_b)
        else:
            stress = stress_result.endurance_limit_mpa
        data.append({"cycles": n, "stress_mpa": stress, "series": "S-N model"})
    return data


def _goodman_data(sut_mpa: float, se_mpa: float) -> list[dict[str, float | str]]:
    data: list[dict[str, float | str]] = []
    for i in range(120):
        sigma_m = sut_mpa * i / 119.0
        sigma_a = se_mpa * max(1.0 - sigma_m / sut_mpa, 0.0)
        data.append({"sigma_m_mpa": sigma_m, "sigma_a_mpa": sigma_a, "series": "Goodman boundary"})
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


st.set_page_config(page_title="Fatigue Life Estimator (v2)", layout="wide")
st.title("Fatigue Life Estimator (v2)")
st.caption("Quick engineering fatigue estimator for screening decisions. Results are estimates, not design certification.")

with st.expander("Model options", expanded=False):
    st.markdown(
        """
        - **Stress-life (S-N):** Basquin + Marin factors + Goodman correction
        - **Strain-life (epsilon-N):** Manson-Coffin-Basquin with Morrow mean-stress correction
        - **Reliability statistics:** two-parameter Weibull with right-censored run-out handling
        """
    )

model_mode = st.radio(
    "Select deterministic model",
    ["Stress-life (S-N)", "Strain-life (epsilon-N)"],
    horizontal=True,
)

col1, col2 = st.columns(2)
with col1:
    material_name = st.selectbox("Material", list(MATERIALS.keys()), index=0)
    diameter_mm = st.number_input("Section diameter d (mm)", min_value=0.1, value=12.0, step=0.1)
    surface_finish = st.selectbox("Surface finish", list(SURFACE_FINISH_COEFFICIENTS.keys()), index=1)
    reliability = st.selectbox("Reliability (%)", list(RELIABILITY_FACTOR.keys()), index=2)
    load_type = st.selectbox("Primary loading type for kc", list(LOAD_FACTOR.keys()), index=0)
    k_misc = st.number_input("Miscellaneous Marin factor kf", min_value=0.1, max_value=1.5, value=1.0, step=0.01)

with col2:
    st.subheader("Loading inputs")
    st.caption("Units: force in N, moment in N*mm.")
    axial_mean = st.number_input("Mean axial force Fm (N)", min_value=0.0, value=2_000.0, step=100.0)
    axial_alt = st.number_input("Alternating axial force amplitude Fa (N)", min_value=0.0, value=1_000.0, step=100.0)
    moment_mean = st.number_input("Mean bending moment Mm (N*mm)", min_value=0.0, value=10_000.0, step=500.0)
    moment_alt = st.number_input("Alternating bending moment amplitude Ma (N*mm)", min_value=0.0, value=8_000.0, step=500.0)

strain_inputs: StrainLifeInput | None = None
if model_mode == "Strain-life (epsilon-N)":
    defaults = STRAIN_LIFE_DEFAULTS[material_name]
    st.subheader("Strain-life constants (Manson-Coffin-Basquin)")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        elastic_modulus_mpa = st.number_input(
            "Elastic modulus E (MPa)",
            min_value=1_000.0,
            value=float(defaults["elastic_modulus_mpa"]),
            step=1_000.0,
            help="Typical room-temperature Young's modulus.",
        )
        sigma_f_prime_mpa = st.number_input(
            "Fatigue strength coefficient sigma_f' (MPa)",
            min_value=1.0,
            value=float(defaults["sigma_f_prime_mpa"]),
            step=10.0,
            help="From strain-controlled fatigue data for the selected material.",
        )
    with sc2:
        epsilon_f_prime = st.number_input(
            "Fatigue ductility coefficient epsilon_f' (-)",
            min_value=0.001,
            value=float(defaults["epsilon_f_prime"]),
            step=0.01,
            format="%.4f",
        )
        basquin_b = st.number_input(
            "Basquin exponent b (-)",
            min_value=-1.0,
            max_value=-0.0001,
            value=float(defaults["basquin_b"]),
            step=0.005,
            format="%.4f",
        )
    with sc3:
        coffin_c = st.number_input(
            "Coffin-Manson exponent c (-)",
            min_value=-2.0,
            max_value=-0.0001,
            value=float(defaults["coffin_c"]),
            step=0.01,
            format="%.4f",
        )
        total_strain_amp_percent = st.number_input(
            "Total strain amplitude epsilon_a (%)",
            min_value=0.001,
            max_value=50.0,
            value=0.30,
            step=0.01,
            format="%.4f",
            help="Enter strain amplitude as percent. Example: 0.30 means 0.003 mm/mm.",
        )

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
    fatigue_inputs = FatigueInput(
        material=MATERIALS[material_name],
        diameter_mm=diameter_mm,
        axial_force_mean_n=axial_mean,
        axial_force_alt_n=axial_alt,
        bending_moment_mean_nmm=moment_mean,
        bending_moment_alt_nmm=moment_alt,
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
                    f"Weibull MLE with censoring: survival at {weibull_result.target_cycles:,.0f} cycles = "
                    f"{weibull_result.survival_at_target*100:.1f}%"
                )

        st.subheader("Key metrics")
        km1, km2, km3, km4 = st.columns(4)
        with km1:
            st.metric("Mean stress sigma_m", f"{stress_result.sigma_mean_mpa:.1f} MPa")
        with km2:
            st.metric("Alternating stress sigma_a", f"{stress_result.sigma_alt_mpa:.1f} MPa")
        with km3:
            st.metric("Goodman adjusted sigma_a,eq", f"{stress_result.sigma_alt_goodman_mpa:.1f} MPa")
        with km4:
            st.metric("Corrected endurance limit Se", f"{stress_result.endurance_limit_mpa:.1f} MPa")

        st.subheader("Engineering plots")
        gc1, gc2 = st.columns(2)

        with gc1:
            sn_line = _sn_curve_data(stress_result)
            sn_point_cycles = deterministic_estimate if deterministic_estimate is not None else 1.0e6
            sn_point = [
                {
                    "cycles": max(sn_point_cycles, 1.0e3),
                    "stress_mpa": stress_result.sigma_alt_goodman_mpa,
                    "series": "Operating point",
                }
            ]
            sn_chart = (
                alt.Chart(alt.Data(values=sn_line))
                .mark_line()
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("stress_mpa:Q", scale=alt.Scale(type="log"), title="Stress amplitude, MPa"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                )
                + alt.Chart(alt.Data(values=sn_point))
                .mark_point(size=140, filled=True)
                .encode(
                    x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles to failure, N"),
                    y=alt.Y("stress_mpa:Q", scale=alt.Scale(type="log"), title="Stress amplitude, MPa"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    tooltip=["cycles:Q", "stress_mpa:Q", "series:N"],
                )
            ).properties(title="Wohler S-N curve (log-log)", height=320)
            st.altair_chart(sn_chart, use_container_width=True)
            st.caption("The point above the curve indicates a short-life condition; below it indicates longer life.")

        with gc2:
            goodman_line = _goodman_data(fatigue_inputs.material.sut_mpa, stress_result.endurance_limit_mpa)
            goodman_point = [
                {
                    "sigma_m_mpa": stress_result.sigma_mean_mpa,
                    "sigma_a_mpa": stress_result.sigma_alt_mpa,
                    "series": "Operating point",
                }
            ]
            goodman_chart = (
                alt.Chart(alt.Data(values=goodman_line))
                .mark_line()
                .encode(
                    x=alt.X("sigma_m_mpa:Q", title="Mean stress sigma_m (MPa)"),
                    y=alt.Y("sigma_a_mpa:Q", title="Alternating stress sigma_a (MPa)"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                )
                + alt.Chart(alt.Data(values=goodman_point))
                .mark_point(size=140, filled=True)
                .encode(
                    x=alt.X("sigma_m_mpa:Q", title="Mean stress sigma_m (MPa)"),
                    y=alt.Y("sigma_a_mpa:Q", title="Alternating stress sigma_a (MPa)"),
                    color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    tooltip=["sigma_m_mpa:Q", "sigma_a_mpa:Q", "series:N"],
                )
            ).properties(title="Goodman diagram", height=320)
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
            ).properties(title="Strain-life epsilon-N curve (log-log)", height=320)
            st.altair_chart(epsilon_chart, use_container_width=True)
            st.caption("This curve blends elastic and plastic strain contributions to estimate low-to-high cycle life.")

            st.subheader("Strain-life details")
            sd1, sd2 = st.columns(2)
            with sd1:
                st.metric("Elastic strain component", f"{strain_result.elastic_strain_component:.5f} mm/mm")
                st.metric("Plastic strain component", f"{strain_result.plastic_strain_component:.5f} mm/mm")
            with sd2:
                st.metric("Input total strain amplitude", f"{strain_inputs.total_strain_amplitude:.5f} mm/mm")
                st.metric("Goodman adjusted sigma_a,eq", f"{strain_result.sigma_alt_goodman_mpa:.1f} MPa")
            assumptions = stress_result.notes + strain_result.notes
        else:
            assumptions = stress_result.notes

        if weibull_result is not None:
            st.subheader("Statistical reliability (Weibull with censoring)")
            wr1, wr2, wr3, wr4 = st.columns(4)
            with wr1:
                st.metric("Shape beta", f"{weibull_result.beta_shape:.3f}")
                st.metric("Scale eta", f"{weibull_result.eta_scale_cycles:,.0f} cycles")
            with wr2:
                st.metric("B10 life", f"{weibull_result.b10_cycles:,.0f} cycles")
                st.metric("B50 life", f"{weibull_result.b50_cycles:,.0f} cycles")
            with wr3:
                st.metric(
                    f"Survival at {weibull_result.target_cycles:,.0f}",
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
                ).properties(title="Weibull probability plot", height=320)
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
                        y=alt.Y("survival:Q", title="Survival probability, R(N)"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                    + alt.Chart(alt.Data(values=target_point))
                    .mark_point(size=140, filled=True)
                    .encode(
                        x=alt.X("cycles:Q", scale=alt.Scale(type="log"), title="Cycles, N"),
                        y=alt.Y("survival:Q", title="Survival probability, R(N)"),
                        color=alt.Color("series:N", legend=alt.Legend(title="Legend")),
                    )
                ).properties(title="Weibull survival curve", height=320)
                st.altair_chart(survival_chart, use_container_width=True)
                st.caption("Use this curve to compare reliability targets against required service-life cycles.")

            assumptions = assumptions + weibull_result.notes

        st.subheader("Assumptions and cautions")
        st.warning("Use this output for screening and part-selection guidance, then validate with detailed fatigue data.")
        for note in assumptions:
            st.write(f"- {note}")
    except ValueError as exc:
        st.error(str(exc))
