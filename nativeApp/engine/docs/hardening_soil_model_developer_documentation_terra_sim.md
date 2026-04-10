# Hardening Soil (HS) Model – Developer Documentation for TerraSim

> **Target audience:** FEM / geotechnical solver developer  
> **Assumptions:**  
> - User understands **Mohr–Coulomb (MC)** model  
> - Solver is **2D FEM**, Gaussian integration points  
> - **Compression = negative**, **tension = positive** (TerraSim convention)  
> - Primary formulation uses **effective stress**

---

## 1. Why Hardening Soil (HS)?

Mohr–Coulomb is simple but unrealistic:
- Single elastic modulus
- No stress dependency
- No loading/unloading distinction
- Perfect plasticity (no hardening)

**Hardening Soil (HS)** improves realism by introducing:
- Stress-dependent stiffness
- Separate stiffness for loading, unloading, and compression
- Plastic hardening (yield surface evolution)
- Effective-stress-based formulation

HS is a **nonlinear elasto-plastic model with isotropic hardening**.

---

## 2. Fundamental Concept

Total strain decomposition:

\[
\varepsilon = \varepsilon^e + \varepsilon^p
\]

Stress update (incremental):

\[
\Delta \sigma' = \mathbf{D}(\sigma', \kappa) : \Delta \varepsilon^e
\]

Where:
- \(\sigma'\) = effective stress
- \(\kappa\) = hardening variable (plastic strain history)

---

## 3. Stress Measures (Important)

Mean effective stress:

\[
p' = \frac{\sigma'_1 + \sigma'_2 + \sigma'_3}{3}
\]

Deviatoric stress (triaxial sense):

\[
q = \sigma'_1 - \sigma'_3
\]

> All stiffness and yielding depend on **p′**, not total stress.

---

## 4. HS Input Parameters

### 4.1 Strength Parameters (same as MC)

| Parameter | Meaning |
|--------|--------|
| c′ | Effective cohesion |
| φ′ | Effective friction angle |
| ψ | Dilatancy angle |

---

### 4.2 Stiffness Parameters (core of HS)

| Parameter | Usage |
|---------|------|
| **E50_ref** | Secant stiffness for primary loading |
| **Eoed_ref** | Oedometer stiffness (1D compression) |
| **Eur_ref** | Unloading / reloading stiffness |
| ν_ur | Poisson ratio for unloading |

---

### 4.3 Stress Dependency

All stiffness moduli depend on mean effective stress:

\[
E = E^{ref} \left( \frac{p'}{p_{ref}} \right)^m
\]

Where:
- \(p_{ref}\) = reference pressure (typically 100 kPa)
- \(m\) = power exponent (≈ 0.3–1.0)

This applies to:
- \(E_{50}\)
- \(E_{oed}\)
- \(E_{ur}\)

---

### 4.4 Additional Parameters

| Parameter | Meaning |
|---------|--------|
| Rf | Failure ratio (≈ 0.9) |
| K0,NC | At-rest earth pressure (normally consolidated) |
| pref | Reference pressure |

---

## 5. Elastic Behaviour in HS

HS uses **nonlinear elasticity**:
- No single elastic modulus
- Elastic stiffness updated every iteration

Elastic matrix \(D\) is constructed using:
- Current \(E\) (from p′)
- Poisson ratio (ν or ν_ur)

---

## 6. Plasticity & Hardening

HS includes **two hardening mechanisms**:

### 6.1 Shear Hardening
- Controlled by accumulated plastic shear strain
- Yield surface expands with loading

Simplified yield function:

\[
f = q - q_{max}(p', \kappa)
\]

---

### 6.2 Compression Hardening
- Controlled by plastic volumetric strain
- Relevant for oedometer-type loading

---

## 7. Flow Rule

- **Non-associated flow rule**
- Plastic potential uses **ψ (dilatancy)**
- Allows realistic volume change behaviour

---

## 8. Drainage Types in Hardening Soil

> HS is **always an effective stress model**

### 8.1 Available Drainage Types

| Drainage Type | Supported | Notes |
|-------------|----------|------|
| Drained | ✅ | Main HS mode |
| Undrained A | ✅ | Most common |
| Undrained B | ⚠️ Limited | Rarely used |
| Undrained C | ❌ | Not compatible |

---

## 9. Drained HS Formulation

- \(\Delta u = 0\)
- \(\sigma = \sigma'\)
- No excess pore pressure

Solver steps:
1. Compute strain increment
2. Update effective stress via HS
3. Assemble global equilibrium

---

## 10. Undrained A HS (Critical Section)

### 10.1 Physical Meaning

- Soil volume is constrained
- \(\Delta \varepsilon_v = 0\)
- Excess pore pressure generated automatically

---

### 10.2 Numerical Treatment

1. Compute trial strain increment
2. Apply HS constitutive law in **effective stress space**
3. Enforce volumetric strain constraint
4. Compute mean stresses:

\[
\Delta u = \Delta \sigma_m - \Delta \sigma'_m
\]

5. Recover total stress:

\[
\sigma = \sigma' + u
\]

> Excess pore pressure is **post-processed**, not an input.

---

## 11. Excess Pore Water Pressure (PWP)

- Can form **above groundwater table**
- Occurs when:
  - Undrained condition
  - Contractive behaviour

HS naturally captures:
- Positive excess PWP (clay, loose sand)
- Negative excess PWP (dense sand)

---

## 12. FEM Implementation Strategy

### 12.1 Integration Point Algorithm

For each Gauss point:
1. Read previous \(\sigma'\), plastic strains
2. Compute \(p'\)
3. Update stiffness moduli
4. Elastic trial stress
5. Yield check
6. Plastic correction (return mapping)
7. Update hardening variables

---

### 12.2 Newton–Raphson Loop

- Use **consistent tangent stiffness** if possible
- Otherwise start with secant stiffness
- Small load increments recommended

---

## 13. Comparison with Mohr–Coulomb

| Feature | MC | HS |
|------|----|----|
| Stress-dependent stiffness | ❌ | ✅ |
| Hardening | ❌ | ✅ |
| Unloading stiffness | ❌ | ✅ |
| Effective stress based | Optional | Mandatory |

---

## 14. Implementation Priority for TerraSim

### Must Have (Core)
- Stress-dependent stiffness
- Plastic strain history
- Shear hardening
- Undrained A formulation

### Can Be Added Later
- K0,NC auto-initialization
- Undrained B
- HSsmall (small-strain stiffness)

---

## 15. Key Developer Notes

- HS **must not** be treated as total stress model
- Do **not** fake undrained behaviour using ν = 0.49
- Excess PWP must be computed from stress difference
- Always update stiffness using **current p′**

---

## 16. Final Remark

If Hardening Soil is implemented correctly:
- TerraSim will be capable of realistic deformation analysis
- You will be operating at **PLAXIS-developer level**, not user level

---

**End of Document**

