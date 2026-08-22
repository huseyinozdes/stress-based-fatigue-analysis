# Publications & References

## Primary Study

### Thesis: The Relationship Between High-Cycle Fatigue and Tensile Properties in Cast Aluminum Alloys

**Author:** Hüseyin Özdeş  
**ORCID ID:** 0000-0003-0283-4626  
**Source:** University of North Florida, Digital Commons  
**URL:** https://digitalcommons.unf.edu/etd/716/  
**Year:** 2014  

#### Abstract
Cast aluminum alloys are common in automotive and aerospace applications due to their high strength-to-density ratio. This thesis analyzes the link between tensile and fatigue performance of commonly used cast aluminum alloys (319, D357, B201, A356-T6), determining whether fatigue performance can be predicted from tensile properties. The study demonstrates that:

- The **Walker mean-stress correction model** with an adjustable exponent provides the best fit across multiple datasets
- A strong correlation exists between **structural quality index (QT)** from tensile data and fatigue performance
- **Basquin parameters** show a distinct relationship with material quality index
- A new empirical method to estimate S-N curves from tensile data is proposed, outperforming six existing methods
- Specimen geometry and structural defects (bifilms, pores) are the dominant factors determining fatigue life

#### Key Findings
1. **Quality Index (QT)** - Estimated from tensile elongation and strength, directly correlates with fatigue life
2. **Walker Parameter** - Shows strong correlation with QT, enabling mean-stress correction
3. **Basquin Exponent** - Related to QT, allowing S-N curve estimation from tensile properties
4. **Rotating Beam Conversion** - Esin's method provides best correlation between rotating bending and axial fatigue
5. **Weibull Statistics** - Fracture properties follow Weibull distribution linked to defect populations

#### Research Questions Addressed
1. Performance of Soderberg, Smith-Watson-Topper, and Walker equations in cast aluminum alloys
2. Correlation between elongation (QT) and fatigue life across aerospace/automotive alloys
3. Development of new method to estimate HCF from tensile data for aluminum castings
4. Rotating beam to axial fatigue conversion methodology

#### Material Systems Studied
- A206 aluminum alloy castings (aerospace)
- 319 aluminum alloy castings (automotive)
- D357 aluminum alloy castings (aerospace)
- B201 aluminum alloy castings (aerospace)
- A356-T6 aluminum alloy castings (automotive/aerospace)

---

## Key Methodologies Implemented

### 1. Structural Quality Index (QT)
$$Q_T = \frac{\sigma_T}{\sigma_U} \times \ln(1 + e_f)$$

where:
- σ_T = tensile strength
- σ_U = ultimate strength
- e_f = elongation at fracture

### 2. Mean Stress Correction: Walker Model
$$\sigma'_a = \sigma_a (1 - R)^{-p}$$

where:
- σ_a = alternating stress amplitude
- R = stress ratio (σ_min / σ_max)
- p = Walker exponent (correlates with QT)

### 3. Basquin S-N Model
$$\sigma_a = A \cdot N_f^b$$

where:
- A, b = Basquin parameters (empirically determined from QT)
- N_f = fatigue life (cycles)

### 4. Weibull Distribution for Fracture Statistics
$$P = 1 - \exp\left[-V\left(\frac{\sigma - \sigma_T}{\sigma_0}\right)^m\right]$$

where:
- P = probability of failure
- m = Weibull modulus (shape parameter)
- σ_0 = scale parameter
- σ_T = threshold stress

### 5. Rotating Beam to Axial Fatigue Conversion (Esin Method)
$$\sigma_{a|ax} = \frac{2\sigma_{a|rb}}{3}\left(\frac{1 - k^3}{1 - k^2}\right)$$

where k = d/D (ratio of elastic core diameter to specimen diameter)

---

## Recommended References for Further Study

The thesis references and analyzes data from studies on:
- Basquin fatigue models and S-N curve behavior
- Mean stress correction methods (Soderberg, Smith-Watson-Topper, Walker)
- Weibull statistics applied to fracture mechanics
- Casting defect effects on fatigue life
- Microstructural effects on fatigue in aluminum alloys
- Rotating bending fatigue test theory and conversion methods

For comprehensive reference list, consult the full thesis at https://digitalcommons.unf.edu/etd/716/

---

## Engineering references for material constants and fatigue methods

The material constants in this estimator are derived from or consistent with the following standard engineering references. These are not exhaustive; engineers should consult primary literature and material certificates for design-critical applications.

### Fatigue theory and S-N / ε-N models

1. **Shigley's Mechanical Engineering Design** — Budynas, R. G. & Nisbett, J. K. (10th ed., McGraw-Hill, 2015).  
   Primary source for Marin modification factors, Goodman criterion, and Basquin S-N fitting procedure used in this estimator.

2. **Metal Fatigue in Engineering** — Stephens, R. I., Fatemi, A., Stephens, R. R., & Fuchs, H. O. (2nd ed., Wiley-Interscience, 2000).  
   Comprehensive treatment of S-N, ε-N, mean-stress corrections, and notch-sensitivity.

3. **Fatigue of Materials** — Suresh, S. (2nd ed., Cambridge University Press, 1998).  
   Detailed coverage of crack initiation, Paris' law crack propagation, and Weibull fracture statistics.

4. **Mechanical Behavior of Materials** — Dowling, N. E. (4th ed., Pearson, 2013).  
   Manson-Coffin-Basquin strain-life model, Morrow correction, and transition life derivations.

### Material property data sources

5. **ASM Handbook, Vol. 19: Fatigue and Fracture** — ASM International (1996).  
   Authoritative fatigue property database for steels, aluminium alloys, and titanium alloys. Source for Basquin and Coffin-Manson constants.

6. **Metallic Materials Properties Development and Standardization (MMPDS)** — Federal Aviation Administration / Battelle (current edition).  
   Statistically qualified $S_{ut}$, $S_y$, and fatigue allowables for aerospace materials including Ti-6Al-4V and Al 7075-T6.

7. **MIL-HDBK-5J: Metallic Materials and Elements for Aerospace Vehicle Structures** — US DoD (2003; superseded by MMPDS).  
   Historical source for Al 6061-T6, Al 7075-T6, and titanium alloy design allowables.

8. **EN 1561:2011 — Founding: Grey Cast Irons** — European Committee for Standardisation (CEN).  
   Specification standard for EN-GJL-250 mechanical property requirements.

### Weibull statistics

9. **Statistical Models in Engineering** — Hald, A. (Wiley, 1952); and  
   **The New Weibull Handbook** — Abernethy, R. B. (5th ed., self-published, 2006).  
   Two-parameter Weibull MLE with right-censored (run-out) data: parameter estimation and $B$-life quantile derivations.

### Walker and quality-index models (fatigue engine)

10. **Özdeş, H.** (2014). *The Relationship Between High-Cycle Fatigue and Tensile Properties in Cast Aluminum Alloys.* University of North Florida. https://digitalcommons.unf.edu/etd/716/  
    Primary thesis: quality-index ($Q_T$), Walker exponent, and S-N estimation from tensile data for cast aluminium alloys. Direct basis for `fatigue_engine.py`.
