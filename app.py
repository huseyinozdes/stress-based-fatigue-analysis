from __future__ import annotations

import streamlit as st

from fatigue_model import (
    LOAD_FACTOR,
    MATERIALS,
    RELIABILITY_FACTOR,
    SURFACE_FINISH_COEFFICIENTS,
    FatigueInput,
    estimate_fatigue_life,
)


st.set_page_config(page_title="Fatigue Life Estimator (v1)", layout="wide")
st.title("Fatigue Life Estimator (v1)")
st.caption("Stress-based quick estimator for fatigue-life screening. Results are engineering estimates, not certification values.")

with st.expander("Model summary", expanded=False):
    st.markdown(
        """
        - **Stress model**: nominal axial + bending stress on a solid round section
        - **Mean stress correction**: Goodman relation
        - **High-cycle region**: Basquin line between 1e3 and 1e6 cycles
        - **Endurance limit correction**: Marin factors (surface, size, load, reliability, misc.)
        """
    )

col1, col2 = st.columns(2)
with col1:
    material_name = st.selectbox("Material", list(MATERIALS.keys()), index=0)
    diameter_mm = st.number_input("Section diameter (mm)", min_value=0.1, value=12.0, step=0.1)
    surface_finish = st.selectbox("Surface finish", list(SURFACE_FINISH_COEFFICIENTS.keys()), index=1)
    reliability = st.selectbox("Reliability (%)", list(RELIABILITY_FACTOR.keys()), index=2)
    load_type = st.selectbox("Primary loading type for kc", list(LOAD_FACTOR.keys()), index=0)
    k_misc = st.number_input("Misc. Marin factor (kf, default 1.0)", min_value=0.1, max_value=1.5, value=1.0, step=0.01)

with col2:
    st.subheader("Loading inputs")
    st.caption("Enter force in N and moment in N·mm. Compression can be entered as 0 in this v1 estimator.")
    axial_mean = st.number_input("Mean axial force, Fm (N)", min_value=0.0, value=2_000.0, step=100.0)
    axial_alt = st.number_input("Alternating axial force amplitude, Fa (N)", min_value=0.0, value=1_000.0, step=100.0)
    moment_mean = st.number_input("Mean bending moment, Mm (N·mm)", min_value=0.0, value=10_000.0, step=500.0)
    moment_alt = st.number_input("Alternating bending moment amplitude, Ma (N·mm)", min_value=0.0, value=8_000.0, step=500.0)

if st.button("Estimate fatigue life", type="primary"):
    try:
        result = estimate_fatigue_life(
            FatigueInput(
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
        )
        st.success("Fatigue-life estimate generated.")
        out1, out2, out3 = st.columns(3)
        with out1:
            if result.estimated_cycles is None:
                st.metric("Estimated life", ">= 1e6 cycles")
            else:
                st.metric("Estimated life", f"{result.estimated_cycles:,.0f} cycles")
            st.caption(result.life_label)
        with out2:
            st.metric("Corrected endurance limit, Se", f"{result.endurance_limit_mpa:.1f} MPa")
            st.metric("Goodman-adjusted alternating stress", f"{result.sigma_alt_goodman_mpa:.1f} MPa")
        with out3:
            st.metric("Mean stress, σm", f"{result.sigma_mean_mpa:.1f} MPa")
            st.metric("Alternating stress, σa", f"{result.sigma_alt_mpa:.1f} MPa")

        st.subheader("Intermediate values")
        st.write(
            {
                "Area (mm^2)": round(result.area_mm2, 3),
                "Se' (MPa)": round(result.endurance_limit_prime_mpa, 3),
                "ka": round(result.marin_ka, 4),
                "kb": round(result.marin_kb, 4),
                "kc": round(result.marin_kc, 4),
                "ke": round(result.marin_ke, 4),
                "Basquin a": round(result.basquin_a, 6),
                "Basquin b": round(result.basquin_b, 6),
            }
        )

        st.warning(
            "Estimate only: confirm with detailed geometry, notch effects, load spectra, and material test data before design release."
        )
        st.subheader("Assumptions / cautions")
        for note in result.notes:
            st.write(f"- {note}")
    except ValueError as exc:
        st.error(str(exc))

st.divider()
st.markdown(
    """
    **Future extension hook (part-based defaults)**  
    Add a part catalog (e.g., McMaster or internal part IDs) mapped to default material, diameter, and surface finish, then let users override.
    """
)
