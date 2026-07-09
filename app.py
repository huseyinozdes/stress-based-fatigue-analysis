from __future__ import annotations

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
    estimate_fatigue_life,
    estimate_strain_life,
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


st.set_page_config(page_title="Fatigue Life Estimator (v2)", layout="wide")
st.title("Fatigue Life Estimator (v2)")
st.caption("Quick engineering fatigue estimator for screening decisions. Results are estimates, not design certification.")

with st.expander("Model options", expanded=False):
    st.markdown(
        """
        - **Stress-life (S-N):** Basquin + Marin factors + Goodman correction
        - **Strain-life (epsilon-N):** Manson-Coffin-Basquin with Morrow mean-stress correction
        """
    )

model_mode = st.radio(
    "Select estimation model",
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

        st.subheader("Verdict")
        if model_mode == "Stress-life (S-N)":
            if stress_result.estimated_cycles is None:
                headline = "Estimated life: >= 1e6 cycles"
            else:
                headline = f"Estimated life: {stress_result.estimated_cycles:,.0f} cycles"
            st.success(headline)
            st.caption(stress_result.life_label)
        else:
            if strain_result.estimated_cycles is None:
                headline = "Estimated life: beyond epsilon-N solver upper range"
            else:
                headline = f"Estimated life: {strain_result.estimated_cycles:,.0f} cycles"
            st.success(headline)
            st.caption(strain_result.life_label)

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
            sn_point_cycles = stress_result.estimated_cycles if stress_result.estimated_cycles is not None else 1.0e6
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

        if model_mode == "Strain-life (epsilon-N)" and strain_inputs is not None:
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

        st.subheader("Assumptions and cautions")
        st.warning("Use this output for screening and part-selection guidance, then validate with detailed fatigue data.")
        for note in assumptions:
            st.write(f"- {note}")
    except ValueError as exc:
        st.error(str(exc))
