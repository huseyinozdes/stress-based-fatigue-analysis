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
