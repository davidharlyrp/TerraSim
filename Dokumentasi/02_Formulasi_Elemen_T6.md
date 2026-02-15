# 02. Formulasi Elemen T6 (Triangular 6-Node)

Dokumen ini menjelaskan implementasi elemen hingga (Finite Element) yang digunakan dalam solver, yaitu elemen segitiga 6-titik (T6) dengan interpolasi kuadratik.

File terkait: `backend/solver/element_t6.py`

## 1. Karakteristik Elemen T6

Elemen T6 dipilih karena akurasinya yang jauh lebih tinggi dibandingkan elemen segitiga linear (Constant Strain Triangle/CST) dalam menangkap gradien tegangan yang kompleks.
*   **Jumlah Node**: 6 node per elemen.
    *   3 node sudut (vertex).
    *   3 node tengah (midside nodes).
*   **Derajat Kebebasan (DOF)**: 2 per node ($u_x, u_y$). Total 12 DOF per elemen.
*   **Fungsi Bentuk (Shape Functions)**: Kuadratik ($N_i(\xi, \eta)$).
*   **Integrasi Numerik**: Gauss Quadrature 3 titik.

## 2. Fungsi Bentuk (Shape Functions) $N$

Fungsi bentuk didefinisikan dalam koordinat natural $(\xi, \eta)$.
Lihat `element_t6.py`, fungsi `shape_functions_t6` (Baris 24-40).

$$
\begin{aligned}
\zeta &= 1 - \xi - \eta \\
N_1 &= \zeta(2\zeta - 1) \\
N_2 &= \xi(2\xi - 1) \\
N_3 &= \eta(2\eta - 1) \\
N_4 &= 4\zeta\xi \quad (\text{midpoint } 1-2) \\
N_5 &= 4\xi\eta \quad (\text{midpoint } 2-3) \\
N_6 &= 4\eta\zeta \quad (\text{midpoint } 3-1)
\end{aligned}
$$

## 3. Matriks Strain-Displacement ($B$)

Matriks $B$ menghubungkan vektor perpindahan nodal ($u$) dengan vektor regangan ($\epsilon$).
$$ \epsilon = B \cdot u $$
Dimana:
$$ \epsilon = \begin{bmatrix} \epsilon_{xx} \\ \epsilon_{yy} \\ \gamma_{xy} \end{bmatrix} $$
$$ u = \begin{bmatrix} u_{x1} \\ u_{y1} \\ \vdots \\ u_{x6} \\ u_{y6} \end{bmatrix} $$

Matriks $B$ disusun dari turunan fungsi bentuk terhadap koordinat fisik ($x, y$).
Kode: `compute_b_matrix` (Baris 86-111).

$$
B_i = \begin{bmatrix}
\frac{\partial N_i}{\partial x} & 0 \\
0 & \frac{\partial N_i}{\partial y} \\
\frac{\partial N_i}{\partial y} & \frac{\partial N_i}{\partial x}
\end{bmatrix}
$$

Matriks $B$ akhir untuk satu elemen adalah penggabungan dari 6 matriks sub-B tersebut ($3 \times 12$):

$$
B = \begin{bmatrix} 
B_1 & B_2 & B_3 & B_4 & B_5 & B_6 
\end{bmatrix}
$$

Atau secara lengkap:

$$
B = \begin{bmatrix}
\frac{\partial N_1}{\partial x} & 0 & \frac{\partial N_2}{\partial x} & 0 & \dots & \frac{\partial N_6}{\partial x} & 0 \\
0 & \frac{\partial N_1}{\partial y} & 0 & \frac{\partial N_2}{\partial y} & \dots & 0 & \frac{\partial N_6}{\partial y} \\
\frac{\partial N_1}{\partial y} & \frac{\partial N_1}{\partial x} & \frac{\partial N_2}{\partial y} & \frac{\partial N_2}{\partial x} & \dots & \frac{\partial N_6}{\partial y} & \frac{\partial N_6}{\partial x}
\end{bmatrix}
$$

Secara visual, hubungan $\epsilon = B \cdot u$ untuk satu elemen T6 adalah:

$$
\begin{bmatrix} 
\epsilon_{xx} \\ \epsilon_{yy} \\ \gamma_{xy} 
\end{bmatrix} = 
\begin{bmatrix}
\frac{\partial N_1}{\partial x} & 0 & \frac{\partial N_2}{\partial x} & 0 & \dots & \frac{\partial N_6}{\partial x} & 0 \\
0 & \frac{\partial N_1}{\partial y} & 0 & \frac{\partial N_2}{\partial y} & \dots & 0 & \frac{\partial N_6}{\partial y} \\
\frac{\partial N_1}{\partial y} & \frac{\partial N_1}{\partial x} & \frac{\partial N_2}{\partial y} & \frac{\partial N_2}{\partial x} & \dots & \frac{\partial N_6}{\partial y} & \frac{\partial N_6}{\partial x}
\end{bmatrix}
\begin{bmatrix} 
u_{x1} \\ u_{y1} \\ u_{x2} \\ u_{y2} \\ \vdots \\ u_{x6} \\ u_{y6} 
\end{bmatrix}
$$

## 4. Matriks Kekakuan Elemen ($K_{el}$)

$$ K_{el} = \int_{V} B^T D B \, dV $$
Untuk kasus 2D Plane Strain dengan ketebalan $t=1$:
$$ K_{el} = \int_{A} B^T D B \, dA $$

Diselesaikan dengan **Integrasi Gauss 3-Titik**:
$$ K_{el} \approx \sum_{g=1}^{3} (B_g^T D B_g) \cdot \det(J)_g \cdot w_g $$

*   $B_g$: Matriks B dievaluasi di titik Gauss.
*   $D$: Matriks Konstitutif Material. Matriks ini mendefinisikan hubungan antara "Stress" dan "Strain" ($\sigma = D \epsilon$). Untuk material elastis, $D$ berisi properti kekakuan tanah seperti Modulus Young dan Poisson's Ratio. (Detail rumus ada di [03_Model_Konstitutif_dan_Drainase.md](file:///e:/Software/New%20folder/TerraSim/Dokumentasi/03_Model_Konstitutif_dan_Drainase.md)).
*   $\det(J)_g$: Determinan Jacobian (transformasi area dari natural ke fisik).
*   $w_g$: Bobot integrasi Gauss ($1/6$ untuk setiap titik).

### Step-by-Step Derivasi Matriks Kekakuan ($K_{el}$)

Bayangkan kita sedang menghitung kekakuan untuk satu elemen T6 dengan material **Linear Elastic**:

**Langkah 1: Tentukan Matriks D (Konstitutif)**
Berdasarkan $E$ dan $\nu$, kita susun matriks $D$ ($3 \times 3$):
$$ D = \begin{bmatrix} d_{11} & d_{12} & 0 \\ d_{21} & d_{22} & 0 \\ 0 & 0 & d_{33} \end{bmatrix} $$

**Langkah 2: Evaluasi Matriks B pada Titik Gauss**
Untuk setiap titik Gauss $g$ (total ada 3), kita hitung matriks $B_g$ ($3 \times 12$):
$$ B_g = [B_1, B_2, B_3, B_4, B_5, B_6]_g $$

**Langkah 3: Perkalian Matriks (Integran)**
Kita hitung produk matriks $B_g^T \cdot D \cdot B_g$ di titik Gauss. Dalam bentuk blok matriks:

$$
B^T D B = \begin{bmatrix} 
B_1^T \\ B_2^T \\ B_3^T \\ B_4^T \\ B_5^T \\ B_6^T 
\end{bmatrix}_{12 \times 3} 
\begin{bmatrix} d_{11} & d_{12} & 0 \\ d_{21} & d_{22} & 0 \\ 0 & 0 & d_{33} \end{bmatrix}_{3 \times 3}
\begin{bmatrix} B_1 & B_2 & B_3 & B_4 & B_5 & B_6 \end{bmatrix}_{3 \times 12}
$$

Hasil perkalian ini akan menghasilkan matriks simetris **$12 \times 12$** yang terdiri dari 36 sub-matriks berukuran $2 \times 2$:

$$
B^T D B = \begin{bmatrix}
[B_1^T D B_1] & [B_1^T D B_2] & \dots & [B_1^T D B_6] \\
[B_2^T D B_1] & [B_2^T D B_2] & \dots & [B_2^T D B_6] \\
\vdots & \vdots & \ddots & \vdots \\
[B_6^T D B_1] & [B_6^T D B_2] & \dots & [B_6^T D B_6]
\end{bmatrix}
$$

**Langkah 4: Contoh Ekspansi Sub-Matriks ($2 \times 2$)**
Setiap blok $[K_{ij}] = B_i^T D B_j$ dihitung sebagai berikut:

$$
\underbrace{\begin{bmatrix} 
\frac{\partial N_i}{\partial x} & 0 & \frac{\partial N_i}{\partial y} \\ 
0 & \frac{\partial N_i}{\partial y} & \frac{\partial N_i}{\partial x} 
\end{bmatrix}}_{B_i^T}
\underbrace{\begin{bmatrix} 
d_{11} & d_{12} & 0 \\ 
d_{21} & d_{22} & 0 \\ 
0 & 0 & d_{33} 
\end{bmatrix}}_{D}
\underbrace{\begin{bmatrix} 
\frac{\partial N_j}{\partial x} & 0 \\ 
0 & \frac{\partial N_j}{\partial y} \\ 
\frac{\partial N_j}{\partial y} & \frac{\partial N_j}{\partial x} 
\end{bmatrix}}_{B_j}
$$

Jika kita kalikan secara manual sesuai urutan matriks di atas, kita dapatkan komponen $[K_{ij}]$:

$$
\begin{aligned}
k_{xx} &= d_{11} \frac{\partial N_i}{\partial x} \frac{\partial N_j}{\partial x} + d_{33} \frac{\partial N_i}{\partial y} \frac{\partial N_j}{\partial y} \\
k_{xy} &= d_{12} \frac{\partial N_i}{\partial x} \frac{\partial N_j}{\partial y} + d_{33} \frac{\partial N_i}{\partial y} \frac{\partial N_j}{\partial x} \\
k_{yx} &= d_{21} \frac{\partial N_i}{\partial y} \frac{\partial N_j}{\partial x} + d_{33} \frac{\partial N_i}{\partial x} \frac{\partial N_j}{\partial y} \\
k_{yy} &= d_{22} \frac{\partial N_i}{\partial y} \frac{\partial N_j}{\partial y} + d_{33} \frac{\partial N_i}{\partial x} \frac{\partial N_j}{\partial x}
\end{aligned}
$$

**Langkah 5: Integrasi Numerik (Penjumlahan)**
Kita jumlahkan hasil perkalian di atas untuk ke-3 titik Gauss, masing-masing dikalikan dengan determinan Jacobian ($\det J$) dan bobot Gauss ($w$):
$$ K_{el} = \sum_{g=1}^{3} (B_g^T D B_g \cdot \det J_g \cdot w_g) $$

Hasil akhir $K_{el}$ adalah matriks simetris **$12 \times 12$** yang siap dirakit ke dalam **Matriks Kekakuan Global**. Berikut adalah visualisasi layout penempatan derajat kebebasan (DOF) di dalam matriks tersebut:

$$
K_{el} = \begin{bmatrix}
k_{1,1}^{xx} & k_{1,1}^{xy} & k_{1,2}^{xx} & k_{1,2}^{xy} & \dots & k_{1,6}^{xy} \\
k_{1,1}^{yx} & k_{1,1}^{yy} & k_{1,2}^{yx} & k_{1,2}^{yy} & \dots & k_{1,6}^{yy} \\
k_{2,1}^{xx} & k_{2,1}^{xy} & k_{2,2}^{xx} & k_{2,2}^{xy} & \dots & k_{2,6}^{xy} \\
k_{2,1}^{yx} & k_{2,1}^{yy} & k_{2,2}^{yx} & k_{2,2}^{yy} & \dots & k_{2,6}^{yy} \\
\vdots & \vdots & \vdots & \vdots & \ddots & \vdots \\
k_{6,1}^{yx} & k_{6,1}^{yy} & k_{6,2}^{yx} & k_{6,2}^{yy} & \dots & k_{6,6}^{yy}
\end{bmatrix}_{12 \times 12}
$$

**Keterangan:**
*   Setiap baris/kolom mewakili DOF dari node 1 s/d 6.
*   Format $k_{i,j}^{ab}$ berarti kekakuan yang menghubungkan **Node $i$** (arah $a$) dengan **Node $j$** (arah $b$).
*   Matriks ini bersifat **simetrik** ($K = K^T$), yang berarti $k_{i,j}^{xy} = k_{j,i}^{yx}$.

Implementasi di kode: `compute_element_matrices_t6` (Baris 134-230).

Beban akibat berat sendiri tanah dihitung sebagai integral volume dari gaya badan (body force) $\mathbf{b} = [0, -\rho]^T$.

### 5. Formulasi Matriks $F_{grav}$

Dalam FEM, beban gravitasi elemen dihitung dengan mengalikan matriks fungsi bentuk $[N]^T$ dengan body force:

$$ \mathbf{F}_{grav} = \int_{V} \mathbf{N}^T \mathbf{b} \, dV $$

Di mana $\mathbf{N}$ adalah matriks shape function berukuran $2 \times 12$ untuk elemen T6:
$$ \mathbf{N} = \begin{bmatrix} 
N_1 & 0 & N_2 & 0 & N_3 & 0 & N_4 & 0 & N_5 & 0 & N_6 & 0 \\
0 & N_1 & 0 & N_2 & 0 & N_3 & 0 & N_4 & 0 & N_5 & 0 & N_6
\end{bmatrix} $$

### Ekspansi Vektor Hasil ($12 \times 1$)

Integral tersebut diselesaikan secara numerik di 3 titik Gauss. Hasilnya adalah vektor kolom $12 \times 1$:

$$
\mathbf{F}_{grav} = \sum_{g=1}^{3} \left( \begin{bmatrix} 
0 \\ -N_1 \rho \\ 0 \\ -N_2 \rho \\ 0 \\ -N_3 \rho \\ 0 \\ -N_4 \rho \\ 0 \\ -N_5 \rho \\ 0 \\ -N_6 \rho 
\end{bmatrix}_g \cdot \det(J)_g \cdot w_g \right)
$$

Vektor akhir yang dihasilkan solver memiliki struktur:

$$
\mathbf{F}_{grav} = \begin{bmatrix} 
F_{x,1} \\ F_{y,1} \\ F_{x,2} \\ F_{y,2} \\ \vdots \\ F_{x,6} \\ F_{y,6} 
\end{bmatrix} = \begin{bmatrix} 
0 \\ F_{y,1} \\ 0 \\ F_{y,2} \\ \vdots \\ 0 \\ F_{y,6} 
\end{bmatrix}_{12 \times 1}
$$

**Keterangan:**
*   $\rho$: Berat volume tanah ($\gamma_{unsat}$ atau $\gamma_{sat}$).
*   $F_{x,i} = 0$: Karena gravitasi hanya bekerja pada arah vertikal.
*   $F_{y,i}$: Total beban vertikal yang didelegasikan ke node $i$ elemen tersebut.

Kode: Baris 225-228 di `element_t6.py`.
Vector `F_grav` ini nantinya digunakan untuk menghitung `delta_F_external` saat elemen diaktifkan atau material berubah.
