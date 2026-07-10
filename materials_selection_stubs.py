"""
Synthetic stub datasets for the materials-selection scaffold.

STATUS: placeholder – values are plausible order-of-magnitude estimates only.
        Replace with literature-validated data (e.g. CES Edupack, ASM Handbooks,
        Shigley Appendix) before using for engineering decisions.

Reference targets for calibration:
  - Ashby, M.F. (2011). Materials Selection in Mechanical Design, 4th ed.
  - Norton, R.L. (2013). Machine Design, 5th ed.
  - Shigley, J.E. et al. (2014). Mechanical Engineering Design, 10th ed.
"""
from __future__ import annotations

from materials_selection_types import MaterialProperties

# ---------------------------------------------------------------------------
# Steel family
# ---------------------------------------------------------------------------

AISI_1020_HR = MaterialProperties(
    name="AISI 1020 HR",
    youngs_modulus_mpa=200_000.0,
    yield_strength_mpa=210.0,
    ultimate_strength_mpa=380.0,
    density_kg_m3=7_850.0,
    endurance_limit_mpa=190.0,   # TODO: verify against standardised R=-1 data
    basquin_exponent=-0.085,      # TODO: calibrate from test data
    fracture_toughness_mpa_sqrtm=50.0,
    material_class="steel",
    notes=["Stub – placeholder values; calibration required."],
)

AISI_4340 = MaterialProperties(
    name="AISI 4340",
    youngs_modulus_mpa=200_000.0,
    yield_strength_mpa=1_170.0,
    ultimate_strength_mpa=1_280.0,
    density_kg_m3=7_850.0,
    endurance_limit_mpa=590.0,   # TODO: verify
    basquin_exponent=-0.076,      # TODO: calibrate
    fracture_toughness_mpa_sqrtm=59.0,
    material_class="steel",
    notes=["Stub – placeholder values; calibration required."],
)

AISI_316L_SS = MaterialProperties(
    name="AISI 316L SS",
    youngs_modulus_mpa=193_000.0,
    yield_strength_mpa=170.0,
    ultimate_strength_mpa=485.0,
    density_kg_m3=7_990.0,
    endurance_limit_mpa=210.0,   # TODO: verify
    basquin_exponent=-0.094,      # TODO: calibrate
    fracture_toughness_mpa_sqrtm=200.0,
    material_class="steel",
    notes=["Stub – placeholder values; calibration required."],
)

# ---------------------------------------------------------------------------
# Aluminium family
# ---------------------------------------------------------------------------

AL_6061_T6 = MaterialProperties(
    name="Al 6061-T6",
    youngs_modulus_mpa=68_900.0,
    yield_strength_mpa=276.0,
    ultimate_strength_mpa=310.0,
    density_kg_m3=2_700.0,
    endurance_limit_mpa=97.0,    # TODO: verify; Al alloys have no true endurance limit
    basquin_exponent=-0.095,      # TODO: calibrate
    fracture_toughness_mpa_sqrtm=29.0,
    material_class="aluminium",
    notes=[
        "Stub – placeholder values; calibration required.",
        "Aluminium alloys lack a true endurance limit; value is at 10^7 cycles.",
    ],
)

AL_7075_T6 = MaterialProperties(
    name="Al 7075-T6",
    youngs_modulus_mpa=71_700.0,
    yield_strength_mpa=503.0,
    ultimate_strength_mpa=572.0,
    density_kg_m3=2_810.0,
    endurance_limit_mpa=159.0,   # TODO: verify at 10^7 cycles
    basquin_exponent=-0.088,      # TODO: calibrate
    fracture_toughness_mpa_sqrtm=24.0,
    material_class="aluminium",
    notes=[
        "Stub – placeholder values; calibration required.",
        "Aluminium alloys lack a true endurance limit; value is at 10^7 cycles.",
    ],
)

# ---------------------------------------------------------------------------
# Titanium family
# ---------------------------------------------------------------------------

TI_6AL_4V = MaterialProperties(
    name="Ti-6Al-4V",
    youngs_modulus_mpa=113_800.0,
    yield_strength_mpa=880.0,
    ultimate_strength_mpa=950.0,
    density_kg_m3=4_430.0,
    endurance_limit_mpa=510.0,   # TODO: verify at R=-1, 10^7 cycles
    basquin_exponent=-0.095,      # TODO: calibrate
    fracture_toughness_mpa_sqrtm=75.0,
    material_class="titanium",
    notes=["Stub – placeholder values; calibration required."],
)

# ---------------------------------------------------------------------------
# Polymer family (illustrative Ashby region coverage)
# ---------------------------------------------------------------------------

NYLON_PA6 = MaterialProperties(
    name="Nylon PA-6",
    youngs_modulus_mpa=2_800.0,
    yield_strength_mpa=65.0,
    ultimate_strength_mpa=75.0,
    density_kg_m3=1_130.0,
    endurance_limit_mpa=25.0,    # TODO: very approximate; polymers are environment-sensitive
    material_class="polymer",
    notes=["Stub – highly approximate; polymer fatigue is highly environment-sensitive."],
)

# ---------------------------------------------------------------------------
# Convenience collection
# ---------------------------------------------------------------------------

STUB_MATERIALS: list[MaterialProperties] = [
    AISI_1020_HR,
    AISI_4340,
    AISI_316L_SS,
    AL_6061_T6,
    AL_7075_T6,
    TI_6AL_4V,
    NYLON_PA6,
]
