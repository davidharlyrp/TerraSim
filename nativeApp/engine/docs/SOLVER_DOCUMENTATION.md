# 🗺️ DaharTerraSim: Specialized FEA Solver Deep-Dive

This document provides a **"Super Complete"** technical and scientific reference for the **DaharTerraSim** 2D Finite Element Analysis (FEA) engine. It details the journey from mesh coordinates to factor of safety results, including all governing equations and logic.

---

## 1. Geometric Core: Constant Strain Triangle (CST) 📐

The solver uses 3-node linear triangular elements. These are the fundamental units for discretization.

### 1.1 Shape Functions ($N_i$)
The CST interpolation is linear. For any point $(x,y)$ inside an element with area $A$:
$$N_i(x,y) = \frac{1}{2A}(a_i + b_i x + c_i y)$$
Where geometric constants are:
*   $a_1 = x_2 y_3 - x_3 y_2, \quad b_1 = y_2 - y_3, \quad c_1 = x_3 - x_2$
*   $a_2 = x_3 y_1 - x_1 y_3, \quad b_2 = y_3 - y_1, \quad c_2 = x_1 - x_3$
*   $a_3 = x_1 y_2 - x_2 y_1, \quad b_3 = y_1 - y_2, \quad c_3 = x_2 - x_1$

**Area Matrix Det**:
$$2A = |x_1(y_2-y_3) + x_2(y_3-y_1) + x_3(y_1-y_2)|$$

### 1.2 Displacement & Strain Kinematics
Displacement within the element:
$$u = N_1 u_1 + N_2 u_2 + N_3 u_3$$
$$v = N_1 v_1 + N_2 v_2 + N_3 v_3$$

Strain components (Plane Strain):
$$\boldsymbol{\epsilon} = \begin{bmatrix} \epsilon_{xx} \\ \epsilon_{yy} \\ \gamma_{xy} \end{bmatrix} = \begin{bmatrix} \frac{\partial u}{\partial x} \\ \frac{\partial v}{\partial y} \\ \frac{\partial u}{\partial y} + \frac{\partial v}{\partial x} \end{bmatrix}$$

This Leads to the **Strain-Displacement Matrix ($B$):**
$$
[B] = \frac{1}{2A} \begin{bmatrix} 
b_1 & 0 & b_2 & 0 & b_3 & 0 \\
0 & c_1 & 0 & c_2 & 0 & c_3 \\
c_1 & b_1 & c_2 & b_2 & c_3 & b_3
\end{bmatrix}
$$

---

## 2. Constitutive Laws & Materials 🧱

### 2.1 Elastic Stiffness ($D$)
For Plane Strain ($\epsilon_{zz} = 0$), the relation $\boldsymbol{\sigma} = [D] \boldsymbol{\epsilon}$ uses:
$$
[D] = \frac{E}{(1+\nu)(1-2\nu)} \begin{bmatrix} 1-\nu & \nu & 0 \\ \nu & 1-\nu & 0 \\ 0 & 0 & \frac{1-2\nu}{2} \end{bmatrix}
$$
*   **Drained Soils**: Use $E'$ (Effective Modulus).
*   **Total Stress (Undrained B/C)**: Use $E_{total}$.

### 2.2 Drainage & Pore Water Pressure (PWP)
Soil is a multi-phase medium (Skeleton + Water).

#### Steady State PWP
Calculated based on the groundwater line interpolation:
$$P_{steady} = \min(0, -\gamma_w \cdot (Y_{water} - Y_{centroid}))$$
*(Note: Tension is positive, so pressure is negative).*

#### Undrained A (Skeletal Stiffness + Excess PWP)
In Undrained A, the volumetric stiffness of water is added:
$$[D_{undrained}] = [D_{skeleton}] + [D_{water}]$$
Where $[D_{water}]$ is a penalty matrix:
$$
[D_{water}] = \frac{K_w}{n} \begin{bmatrix} 1 & 1 & 0 \\ 1 & 1 & 0 \\ 0 & 0 & 0 \end{bmatrix}
$$
The generator of **Excess PWP ($\Delta p_{exc}$)**:
$$\Delta p_{exc} = -\frac{K_w}{n} \Delta \epsilon_v$$

---

## 3. Initial Stress Generation (K0 Procedure) ⛰️

Before applying loads, we must establish gravity equilibrium.

### 3.1 Vertical Stress Integration
For each element, we trace a vertical ray to the surface:
$$\sigma_v = \sum (\gamma_i \cdot \Delta y_i)$$
*   $\gamma_{unsat}$ is used above the water table.
*   $\gamma_{sat}$ is used below the water table.

### 3.2 K0 Principle
Total Stress = Effective Stress + PWP
1.  **Effective Vertical**: $\sigma'_v = \sigma_v - P_{steady}$
2.  **Effective Horizontal**: $\sigma'_h = K_0 \cdot \sigma'_v$
    *   **Jaky's Formula**: $K_0 = 1 - \sin(\phi)$
    *   **Elastic**: $K_0 = \frac{\nu}{1-\nu}$
3.  **Total Horizontal**: $\sigma_h = \sigma'_h + P_{steady}$

---

## 4. The Solver Engine: Incremental-Iterative Loop ⚙️

Analysis uses **MStage (Multiplier for Staging)** and **Newton-Raphson**.

### 4.1 Global Equilibrium Equation
$$[K_{global}] \{\Delta u\} = \mathbf{F}_{ext} - \mathbf{F}_{int}$$
Where internal force $\mathbf{F}_{int}$ is the volume integral of stresses:
$$\mathbf{F}_{int} = \sum_{e} \int [B]^T \boldsymbol{\sigma} \, dV = \sum_{e} ([B]^T \boldsymbol{\sigma} \cdot A \cdot t)$$

### 4.2 Loading Stepping (MStage)
We increase the fraction of external force from $M=0$ to $M=1$:
$$ \mathbf{R} = (M_{stage} \cdot \mathbf{F}_{ext}) - \mathbf{F}_{int} $$

### 4.3 Strength Reduction Method (SRM) 🛡️
Used to find the **Factor of Safety (FoS)**.
1.  Keep loads constant.
2.  Incrementally increase $\Sigma M_{sf}$.
3.  Divide strength parameters:
    *   $c' \Rightarrow c' / \Sigma M_{sf}$
    *   $\tan(\phi) \Rightarrow \tan(\phi) / \Sigma M_{sf}$
    *   $S_u \Rightarrow S_u / \Sigma M_{sf}$
4.  If the solver fails to find equilibrium (divergence), the last stable $\Sigma M_{sf}$ is the FoS.

---

## 5. Plasticity & Return Mapping (Mohr-Coulomb) 🏺

### 5.1 Stress State (Mohr Circle)
From global $[\sigma_{xx}, \sigma_{yy}, \tau_{xy}]$, we find Principal Stresses:
$$\sigma_{avg} = \frac{\sigma_{xx} + \sigma_{yy}}{2}$$
$$R = \sqrt{\left(\frac{\sigma_{xx} - \sigma_{yy}}{2}\right)^2 + \tau_{xy}^2}$$
$$\sigma_1 = \sigma_{avg} + R, \quad \sigma_3 = \sigma_{avg} - R$$

### 5.2 Yield Function ($f$)
$$f = (\sigma_1 - \sigma_3) + (\sigma_1 + \sigma_3)\sin\phi - 2c\cos\phi$$
*   $f < 0$: Elastic (Inside Yield Surface).
*   $f \geq 0$: Plastic (Needs Correction).

### 5.3 Radial Return Algorithm
When yielded, we must project the stress back to $f=0$ by scaling the Mohr circle radius $R$:
1.  Target Radius $R_{target} = c\cos\phi - \sigma_{avg}\sin\phi$
2.  Scale Factor $S = R_{target} / R_{trial}$
3.  Correct Stresses:
    $$\sigma_{xx,corr} = \sigma_{avg} + S \cdot \frac{\sigma_{xx}-\sigma_{yy}}{2}$$
    $$\sigma_{yy,corr} = \sigma_{avg} - S \cdot \frac{\sigma_{xx}-\sigma_{yy}}{2}$$
    $$\tau_{xy,corr} = S \cdot \tau_{xy}$$

---

## 6. Numerical Stability Features ⚓

*   **Modified Newton-Raphson**: Uses the Elastic Stiffness Matrix for assembly. This prevents solver "explosion" when elements start yielding heavily, as the tangent matrix doesn't become singular.
*   **Step Size Cutback**: If an increment fails after 60 (or configured) iterations, the solver halves the step size and retries from the last stable state.
*   **Small Step Termination**: In Safety Analysis, if the step size falls below $0.001$ without convergence, we declare **Material Failure** and terminate.

---
**Summary for Learning**:
Geotechnical FEA isn't just about $K \cdot u = F$. It is about balancing the **skeleton stress**, the **water pressure**, and the **failure envelope**. Each increment is a search for a state where internal forces perfectly oppose the external loads without violating the strength of the soil.
