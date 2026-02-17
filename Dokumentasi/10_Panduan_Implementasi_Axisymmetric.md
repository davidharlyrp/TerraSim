# 10. Panduan Implementasi Analisis Axisymmetric

Dokumen ini menjelaskan teori, rincian rumus, dan langkah-langkah implementasi untuk menambahkan sistem analisis **Axisymmetric** ke dalam solver TerraSim.

## 1. Pendahuluan
Analisis Axisymmetric digunakan untuk memodelkan struktur 3D yang memiliki simetri putar terhadap sebuah poros (axis), seperti pondasi lingkaran, tangki silinder, atau galian sumuran. Dengan metode ini, masalah 3D dapat diselesaikan sebagai masalah 2D pada bidang radial ($r$-$z$).

### Asumsi Koordinat
*   **Sumbu Putar**: Berada pada sisi kiri domain ($x_{min}$).
*   **Koordinat Radial ($r$)**: Jarak horizontal dari sumbu putar ($r = x - x_{min}$).
*   **Koordinat Aksial ($z$)**: Koordinat vertikal ($z = y$).
*   **Derajat Kebebasan**: $u_r$ (radial) dan $u_z$ (aksial).

---

## 2. Penjabaran Rumus (Matematis)

### 2.1 Hubungan Regangan-Perpindahan (Strain-Displacement)
Dalam analisis 2D standar (Plane Strain), terdapat 3 komponen regangan. Dalam Axisymmetric, terdapat komponen ke-4 yaitu **Regangan Hoop ($\epsilon_\theta$)** akibat ekspansi/kontraksi radial.

Vektor regangan $\boldsymbol{\epsilon}$ didefinisikan sebagai:
$$ \boldsymbol{\epsilon} = \begin{bmatrix} \epsilon_r \\ \epsilon_z \\ \gamma_{rz} \\ \epsilon_\theta \end{bmatrix} = \begin{bmatrix} \frac{\partial u_r}{\partial r} \\ \frac{\partial u_z}{\partial z} \\ \frac{\partial u_r}{\partial z} + \frac{\partial u_z}{\partial r} \\ \frac{u_r}{r} \end{bmatrix} $$

### 2.2 Matriks B (Strain-Displacement Matrix)
Matriks $B$ untuk setiap node $i$ pada elemen T6 berubah menjadi ukuran $4 \times 2$:

$$ B_i = \begin{bmatrix}
\frac{\partial N_i}{\partial r} & 0 \\
0 & \frac{\partial N_i}{\partial z} \\
\frac{\partial N_i}{\partial z} & \frac{\partial N_i}{\partial r} \\
\frac{N_i}{r} & 0
\end{bmatrix} $$

Matriks $B$ total untuk satu elemen T6 (6 node) akan berukuran **$4 \times 12$**.

### 2.3 Matriks Konstitutif D (Isotropic Elastic)
Hubungan tegangan-regangan ($\boldsymbol{\sigma} = \mathbf{D} \boldsymbol{\epsilon}$) menjadi $4 \times 4$:

$$ D = \begin{bmatrix}
\lambda + 2\mu & \lambda & 0 & \lambda \\
\lambda & \lambda + 2\mu & 0 & \lambda \\
0 & 0 & \mu & 0 \\
\lambda & \lambda & 0 & \lambda + 2\mu
\end{bmatrix} $$

Di mana $\lambda$ dan $\mu$ (G) adalah parameter Lamé:
*   $\mu = G = \frac{E}{2(1+\nu)}$
*   $\lambda = \frac{E\nu}{(1+\nu)(1-2\nu)}$

Vektor tegangan hasil: $\boldsymbol{\sigma} = [\sigma_r, \sigma_z, \tau_{rz}, \sigma_\theta]^T$.

### 2.4 Matriks B pada Node $i$
Untuk elemen T6, setiap Gauss point memiliki posisi $(r, z)$. Komponen $B_i$ ($4 \times 2$) adalah:
$$ B_i = \begin{bmatrix}
\frac{\partial N_i}{\partial r} & 0 \\
0 & \frac{\partial N_i}{\partial z} \\
\frac{\partial N_i}{\partial z} & \frac{\partial N_i}{\partial r} \\
\frac{N_i}{r} & 0
\end{bmatrix} $$

### 2.5 Integrasi Volume (Stiffness Matrix)
Perbedaan utama pada axisymmetric adalah integral dilakukan terhadap volume silinder ($dV = \int 2\pi r \cdot dA$):

$$ K_{el} = \int_{A} B^T D B \cdot (2\pi r) \, dr dz $$

Secara numerik (Gauss Quadrature):
$$ K_{el} \approx \sum_{g=1}^{3} (B_g^T D B_g) \cdot (2\pi r_g) \cdot \det(J)_g \cdot w_g $$
Di mana $r_g = \sum N_i(g) \cdot r_i$ (koordinat radial di titik Gauss tersebut).

### 2.6 Penanganan Tegangan Utama dalam Axisymmetric
Dalam kondisi axisymmetric, terdapat 3 tegangan utama ($\sigma_1, \sigma_2, \sigma_3$):
1.  **$\sigma_{rz\_max}, \sigma_{rz\_min}$**: Dihitung dari komponen bidang $r$-$z$ ($\sigma_r, \sigma_z, \tau_{rz}$).
2.  **$\sigma_\theta$**: Merupakan salah satu tegangan utama karena tidak ada tegangan geser pada bidang transversal.

Maka, $\sigma_1 = \max(\sigma_{rz\_max}, \sigma_\theta)$ dan $\sigma_3 = \min(\sigma_{rz\_min}, \sigma_\theta)$.
Kriteria Mohr-Coulomb kemudian diterapkan pada $\sigma_1$ dan $\sigma_3$ tersebut.

---

## 3. Detail Implementasi Backend

### 3.1 Perubahan pada `element_t6.py`
Fungsi `compute_b_matrix` perlu mendeteksi mode axisymmetric:

```python
# Pseudo-code update compute_b_matrix
def compute_b_matrix_axisymmetric(node_coords, xi, eta, x_min):
    # ... hitung dN_physical, det_J, dan N (shape functions) ...
    N = shape_functions_t6(xi, eta)
    gp_coords = N @ node_coords
    r = gp_coords[0] - x_min
    
    if r < 1e-6: r = 1e-6 # Hindari pembagian nol di poros simetri
    
    B = np.zeros((4, 12))
    for i in range(6):
        B[0, 2*i] = dN_physical[0, i]   # dNi/dr
        B[1, 2*i+1] = dN_physical[1, i] # dNi/dz
        B[2, 2*i] = dN_physical[1, i]   # dNi/dz
        B[2, 2*i+1] = dN_physical[0, i] # dNi/dr
        B[3, 2*i] = N[i] / r            # Ni/r (Hoop component)
    return B, det_J, r
```

### 3.2 Update Perhitungan Gaya Gravitasi
Beban gravitasi juga harus dikalikan dengan faktor volume $2\pi r$:
$$ \mathbf{F}_{grav} = \sum_{g=1}^{3} \mathbf{N}_g^T \begin{bmatrix} 0 \\ -\rho \end{bmatrix} \cdot (2\pi r_g) \cdot \det(J)_g \cdot w_g $$

### 3.3 Penyesuaian `phase_solver.py`
Pada bagian `compute_elements_stresses_numba`, perhitungan tegangan harus menangani 4 komponen ($\sigma_r, \sigma_z, \tau_{rz}, \sigma_\theta$):
1.  **Regangan Inkremental**: $\Delta \epsilon = B \cdot \Delta u$ (hasilnya 4 baris).
2.  **Tegangan Utama**: Mencari $\sigma_1, \sigma_2, \sigma_3$ dari 4 komponen tersebut.
    *   $\sigma_{1,3}$ dari lingkaran Mohr bidang $r$-$z$.
    *   $\sigma_\theta$ adalah salah satu tegangan utama (karena geseran $\tau_{r\theta}$ dan $\tau_{z\theta}$ adalah nol).
3.  **Return Mapping**: MC harus mempertimbangkan ketiga tegangan utama ($\sigma_1, \sigma_2, \sigma_3$). Jika menggunakan pendekatan Lingkaran Mohr Plane-RZ, pastikan $\sigma_\theta$ tetap dikoreksi atau dicheck terhadap yield.

---

## 4. Checklist Modifikasi
- [ ] **Models**: Tambahkan flag `is_axisymmetric` pada `GeneralSettings` atau `PhaseRequest`.
- [ ] **Element Formulation**: Modifikasi `compute_element_matrices_t6` untuk menyertakan faktor $2\pi r$ dan matriks $B$ $4 \times 12$.
- [ ] **Solver Loop**: Update loop Numba agar mendukung array tegangan/regangan dengan 4 komponen.
- [ ] **PWP Penalty**: $\Delta \epsilon_{vol} = \epsilon_r + \epsilon_z + \epsilon_\theta$.
- [ ] **Output**: Pastikan hasil $\sigma_\theta$ dikirim ke frontend untuk visualisasi.

> [!IMPORTANT]
> Titik putar di kiri ($x_{min}$) berarti nilai $r$ selalu positif. Jika ada elemen yang berada tepat di sumbu ($r=0$), gunakan limitasi nilai $r$ kecil untuk mencegah singularitas pada $B[3, \dots] = N/r$.
