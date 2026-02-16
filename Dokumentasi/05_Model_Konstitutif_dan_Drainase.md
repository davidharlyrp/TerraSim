# 05. Model Konstitutif Material dan Tipe Drainase

Dokumen ini menjelaskan bagaimana solver menangani hubungan tegangan-regangan ($\sigma - \epsilon$), plastisitas Mohr-Coulomb, dan perilaku drainase air pori.

File terkait: 
*   `backend/solver/mohr_coulomb.py`
*   `backend/solver/phase_solver.py` - Fungsi `compute_elements_stresses_numba`.

## 1. Linear Elastic

Dasar dari semua perhitungan adalah hukum Hooke untuk isotropic linear elastic.
Matriks Elastisitas ($D_{el}$) dihitung di `element_t6.py` (Baris 156-169).

$$
D_{el} = \frac{E(1-\nu)}{(1+\nu)(1-2\nu)} \begin{bmatrix}
1 & \frac{\nu}{1-\nu} & 0 \\
\frac{\nu}{1-\nu} & 1 & 0 \\
0 & 0 & \frac{1-2\nu}{2(1-\nu)}
\end{bmatrix}
$$

Atau sering ditulis dalam bentuk parameter Lamé ($\lambda$ dan $\mu$):

$$
D_{el} = \begin{bmatrix}
\lambda + 2\mu & \lambda & 0 \\
\lambda & \lambda + 2\mu & 0 \\
0 & 0 & \mu
\end{bmatrix}
$$

Di mana:
*   $\mu = G = \frac{E}{2(1+\nu)}$ (Modulus Geser)
*   $\lambda = \frac{E\nu}{(1+\nu)(1-2\nu)}$

### 1.1 Hubungan Tegangan-Regangan (Hukum Hooke 2D)

Persamaan $\boldsymbol{\sigma} = \mathbf{D} \cdot \boldsymbol{\epsilon}$ dalam bentuk matriks penuh untuk satu titik integrasi adalah:

$$
\begin{bmatrix} 
\sigma_{xx} \\ \sigma_{yy} \\ \tau_{xy} 
\end{bmatrix} = 
\frac{E}{(1+\nu)(1-2\nu)}
\begin{bmatrix} 
1-\nu & \nu & 0 \\
\nu & 1-\nu & 0 \\
0 & 0 & \frac{1-2\nu}{2}
\end{bmatrix}
\begin{bmatrix} 
\epsilon_{xx} \\ \epsilon_{yy} \\ \gamma_{xy} 
\end{bmatrix}
$$

**Penjelasan Komponen:**
*   **$\sigma_{xx}, \sigma_{yy}$**: Tegangan normal (Normal Stress) pada arah X dan Y.
*   **$\tau_{xy}$**: Tegangan geser (Shear Stress).
*   **$\epsilon_{xx}, \epsilon_{yy}$**: Regangan normal (Normal Strain).
*   **$\gamma_{xy}$**: Regangan geser (Shear Strain).
*   $E$: Modulus Young.
*   $\nu$: Poisson's Ratio.
  
*Catatan: Solver ini menggunakan asumsi **Plane Strain** (Regangan Bidang), yang berarti regangan arah Z dianggap nol ($\epsilon_z = 0$), namun tegangan arah Z ($\sigma_z$) tetap ada dan dihitung kemudian sebagai $\sigma_z = \nu(\sigma_x + \sigma_y)$.*


## 2. Model Plastisitas Mohr-Coulomb

Jika tegangan melampaui batas kekuatan geser tanah, tanah akan mengalami plastisitas (keruntuhan).

### 2.1 Prediksi Tegangan (Trial Stress)
Sebelum mengecek keruntuhan, solver melakukan prediksi tegangan menggunakan Hukum Hooke (asumsi elastis):

$$ \Delta \boldsymbol{\sigma}_{trial} = \mathbf{D}_{el} \cdot \Delta \boldsymbol{\epsilon} $$
$$ \boldsymbol{\sigma}_{trial} = \boldsymbol{\sigma}_{old} + \Delta \boldsymbol{\sigma}_{trial} $$

Tegangan trial ini adalah "titik uji" untuk melihat apakah material masih kuat menahan beban atau sudah melampaui batas kekuatannya.

### 2.2 Kriteria Runtuh (Yield Criterion)
Solver menggunakan kriteria **Mohr-Coulomb** yang didefinisikan sebagai fungsi $f$:

$$ f = (\sigma_1 - \sigma_3) + (\sigma_1 + \sigma_3) \sin \phi - 2c \cos \phi $$

**Interpretasi Kondisi:**
*   **$f \le 0$**: Tegangan masih di dalam batas kekuatan (Elastic).
*   **$f > 0$**: Tegangan melampaui batas (Yielding/Plastic). Solver harus melakukan *Return Mapping*.

**Perhitungan tegangan utama ($\sigma_1, \sigma_3$):**
Tegangan utama dihitung dari tegangan Cartesian $(\sigma_{xx}, \sigma_{yy}, \tau_{xy})$ menggunakan lingkaran Mohr:
$$ \sigma_{1,3} = \frac{\sigma_{xx} + \sigma_{yy}}{2} \pm \sqrt{\left( \frac{\sigma_{xx} - \sigma_{yy}}{2} \right)^2 + \tau_{xy}^2} $$

### 2.3 Batas Kekuatan Geser (Shear Strength)
Secara fisik, kriteria ini sama dengan menyatukan garis singgung pada Lingkaran Mohr dengan garis keruntuhan Coulomb:
$$ \tau = c + \sigma'_n \tan \phi $$
Di mana $\tau$ adalah kekuatan geser maksimum yang bisa ditahan tanah pada tegangan normal $\sigma'_n$.

Kode: `mohr_coulomb_yield` (Baris 10-29 di `mohr_coulomb.py`).

### Kriteria Keruntuhan (Yield Function, $f$)
Formula Mohr-Coulomb diimplementasikan di `mohr_coulomb.py` (Baris 11-29).

$$ f = (\sigma_{max} - \sigma_{min}) + (\sigma_{max} + \sigma_{min})\sin\phi - 2c\cos\phi $$

*   $\phi$: Sudut geser dalam (Friction Angle).
*   $c$: Kohesi (Cohesion).
*   $\sigma_{max}, \sigma_{min}$: Tegangan utama maksimum dan minimum.

Jika $f > 0$, maka terjadi plastisitas (Yielding). Tegangan harus dikoreksi kembali ke permukaan yield ($f=0$).

### 2.1 Penanganan Logika pada Loop Numba

Di dalam loop perhitungan tegangan (`compute_elements_stresses_numba` di `phase_solver.py`), solver melakukan pengecekan flag `mmodel` (0: Linear Elastic, 1: Mohr Coulomb) dan alur perhitungan berikut:

### 2.2 Alur Perhitungan (Step-by-Step Formula)

Untuk setiap **Gauss Point**, alur matematis yang terjadi adalah:

1.  **Hitung Inkrement Regangan ($\Delta \epsilon$):**
    $$ \Delta \epsilon = B \cdot \Delta u_{el} $$
    *(Regangan dihitung dari perpindahan nodal elemen)*.

2.  **Hitung Tegangan Trial ($\sigma_{trial}$):**
    $$ \sigma_{trial} = \sigma_{old} + D_{el} \cdot \Delta \epsilon $$
    *(Untuk Undrained, $D_{el}$ dimodifikasi dengan matriks penalti air)*.

3.  **Cek Kondisi Yield ($f_{trial}$):**
    $$ f_{trial} = F(\sigma_{trial}, c, \phi) $$

4.  **Koreksi Tegangan (Jika $f_{trial} > 0$):**
    $$ \sigma_{new} = \text{ReturnMapping}(\sigma_{trial}) $$
    *(Tegangan ditarik kembali ke permukaan yield)*.

5.  **Hitung Gaya Internal Elemen ($F_{int,el}$):**
    $$ F_{int,el} = \sum_{g=1}^3 B_g^T \cdot \sigma_{new} \cdot \det J_g \cdot w_g $$

### 2.3 Cuplikan Logika pada Loop Numba

Cuplikan Logika (Simplified):
```python
# phase_solver.py ~Baris 124-131
if mmodel == 1: # Mohr-Coulomb
    # Lakukan Return Mapping untuk mengoreksi tegangan plastis
    sig_new, _, yld = return_mapping_mohr_coulomb(
        sigma_trial[0], sigma_trial[1], sigma_trial[2],
        c_eff, phi_eff, D_el
    )
else: # Linear Elastic
    # Langsung gunakan tegangan trial (tidak ada batas kekuatan)
    sig_new = sigma_trial
    yld = False
```

### 2.4 Perbedaan Perilaku
*   **Linear Elastic**: Tegangan akan terus meningkat secara linear dengan bertambahnya beban/deformasi tanpa batas. Tidak pernah "runtuh".
*   **Mohr-Coulomb**: Tegangan akan dibatasi oleh kriteria MC. Jika beban terlalu besar, elemen akan "leleh" (yielded) dan gaya akan didistribusikan ke elemen tetangga. Jika seluruh struktur leleh, solver akan gagal konvergen (keruntuhan).

---

### 2.5 Algoritma Radial Return (Return Mapping)

Jika $f_{trial} > 0$, tegangan harus diproyeksikan kembali ke permukaan yield. Solver menggunakan metode **Radial Return** yang sangat stabil secara numerik.

Kode: `return_mapping_mohr_coulomb` (Baris 33-95 di `mohr_coulomb.py`).

Berikut adalah alur matematis detailnya:

**Langkah 1: Dekomposisi Lingkaran Mohr**
Ubah tegangan trial ($\sigma_{xx}, \sigma_{yy}, \tau_{xy}$) menjadi parameter pusat dan jari-jari lingkaran Mohr:
*   Pusat (Tegangan Rata-rata), $\sigma_{avg}$:
    $$ \sigma_{avg} = \frac{\sigma_{xx} + \sigma_{yy}}{2} $$
*   Jari-jari (Deviatorik), $R_{trial}$:
    $$ R_{trial} = \sqrt{\left( \frac{\sigma_{xx} - \sigma_{yy}}{2} \right)^2 + \tau_{xy}^2} $$

**Langkah 2: Hitung Batas Jari-jari Maksimum ($R_{limit}$)**
Berdasarkan kriteria Mohr-Coulomb, pada tegangan rata-rata $\sigma_{avg}$ tersebut, jari-jari maksimum yang diizinkan adalah:
$$ R_{limit} = c \cos \phi - \sigma_{avg} \sin \phi $$
*(Catatan: Rumus ini didapat dari memanipulasi $f=0$ di mana $(\sigma_1 - \sigma_3) = 2R$ dan $(\sigma_1 + \sigma_3) = 2\sigma_{avg}$)*.

**Langkah 3: Hitung Faktor Skala (Scaling Factor)**
Bandingkan jari-jari trial dengan batas kekuatan:
$$ \eta = \frac{R_{limit}}{R_{trial}} $$
*   **Kasus 1: $\eta < 0$ (Kondisi Tarik / Tension Cut-off)**
    *   **Kapan Terjadi?**: Saat tegangan rata-rata $\sigma_{avg}$ sangat positif (menarik) sehingga melampaui kapasitas kohesi tanah. Dalam rumus, ini membuat $R_{limit}$ bernilai negatif.
    *   **Makna Fisik**: Tanah telah "terpisah" atau mengalami retak tarik karena tidak mampu menahan beban tarikan yang diberikan. Secara grafis, Lingkaran Mohr trial berada sepenuhnya di luar puncak kerucut Mohr-Coulomb.
    *   **Penanganan Solver**: Solver memaksa nilai $\eta = 0$ dan menarik $\sigma_{avg}$ ke titik *Apex* (puncak kerucut). Hasilnya, tegangan geser menjadi nol ($\tau = 0$) dan tegangan normal dibatasi pada nilai tensile strength maksimum tanah.

*   **Kasus 2: $0 \le \eta < 1$ (Kondisi Leleh Geser / Shear Yielding)**
    *   **Kapan Terjadi?**: Saat jari-jari trial ($R_{trial}$) lebih besar dari batas kekuatan geser yang diizinkan ($R_{limit}$) pada level tegangan tersebut.
    *   **Makna Fisik**: Tanah mengalami deformasi plastis permanen akibat geseran. Tanah masih "solid", tapi sudah mencapai batas kekuatannya dan mulai "mengalir" secara plastis.
    *   **Penanganan Solver**: Solver mempertahankan pusat lingkaran Mohr ($\sigma_{avg}$) dan orientasi tegangan (sudut $\theta$), namun "menciutkan" jari-jari lingkaran Mohr trial tepat ke garis keruntuhan Coulomb. Energi yang hilang dalam proses "penciutan" ini (distorsi) adalah apa yang kita sebut sebagai regangan plastis.

**Langkah 4: Rekonstruksi Tegangan Baru**
Tegangan dikembalikan ke koordinat Cartesian dengan menjaga sudut orientasi tetap sama, namun jari-jarinya telah diciutkan:
$$ \sigma_{xx, new} = \sigma_{avg} + \eta \left( \frac{\sigma_{xx} - \sigma_{yy}}{2} \right) $$
$$ \sigma_{yy, new} = \sigma_{avg} - \eta \left( \frac{\sigma_{xx} - \sigma_{yy}}{2} \right) $$
$$ \tau_{xy, new} = \eta \cdot \tau_{xy} $$

---

### 2.6 Penanganan Puncak Kerucut (Tension Cut-off)
Pada kondisi di mana $\sigma_{avg}$ sangat positif (tarik), $R_{limit}$ bisa bernilai negatif. Solver menangani ini dengan membatasi tegangan pada titik puncak kerucut MC (Apex):
$$ \sigma_{max\_apex} = \frac{c \cos \phi}{\sin \phi} $$
Jika $\sigma_{avg} > \sigma_{max\_apex}$, maka seluruh komponen tegangan akan didorong ke titik puncak tersebut untuk menghindari hasil yang tidak stabil secara fisik.

1.  Hitung tegangan percobaan ($\sigma^{trial}_{elastic}$).
2.  Cek apakah $f(\sigma^{trial}) > 0$.
3.  Jika ya, proyeksikan kembali ke garis Mohr-Coulomb.
    *   Tension Cut-off juga diterapkan (tanah tidak kuat tarik).

### 2.7 Pasca Return Mapping (Post-Stress Update)

Setelah solver mendapatkan tegangan yang telah dikoreksi ($\sigma_{new}$), data ini tidak hanya disimpan, tetapi digunakan untuk menggerakkan mesin solver:

**1. Update State Elemen:**
Tegangan $\sigma_{new}$ disimpan sebagai kondisi tegangan saat ini untuk Gauss Point tersebut. Ini akan menjadi $\sigma_{old}$ untuk iterasi atau load step berikutnya.

**2. Perhitungan Gaya Internal ($F_{int}$):**
Inilah bagian terpenting. Tegangan yang sudah "terpotong" oleh batas kekuatan (yield) akan menghasilkan gaya internal yang **lebih kecil** daripada jika tanah bersifat elastis murni:
$$ F_{int, el} = \int_V B^T \cdot \sigma_{new} \, dV $$

**3. Penghitungan Residual ($R$):**
Solver membandingkan Gaya Eksternal (beban yang ingin kita pasang) dengan Gaya Internal (kekuatan yang sanggup diberikan tanah):
$$ R = F_{ext} - F_{int} $$
*   Jika tanah masih **Elastis**: $F_{int}$ akan mengimbangi $F_{ext}$, sehingga $R$ mendekati nol (Konvergen).
*   Jika tanah **Luluh (Yield)**: Karena tegangannya "terpotong" oleh batas MC, $F_{int}$ tidak cukup besar untuk mengimbangi $F_{ext}$. Akibatnya, muncul sisa gaya ($R > \text{tol}$).

**4. Reditribusi Beban (Newton-Raphson):**
Sisa gaya $R$ inilah yang memaksa solver melakukan iterasi Newton-Raphson berikutnya. Solver akan mencoba menambah deformasi ($\Delta u$) agar elemen-elemen di sekitarnya yang masih elastis bisa membantu memikul sisa beban tersebut.

**5. Output dan Visualisasi:**
*   **Yield Flag**: Status `is_yielded = True` disimpan agar di frontend Anda bisa melihat area mana yang sudah "runtuh" (biasanya berwarna merah pada plot kriteria keruntuhan).
*   **Plastic Strain**: Selisih antara regangan total dan regangan elastis dianggap sebagai regangan plastis (deformasi permanen).

---

## 3. Tipe Drainase (Drainage Types)

Perilaku air pori sangat mempengaruhi kekuatan tanah. Solver mendukung 5 tipe drainase:

| Tipe            | Deskripsi                                                                   | Parameter Efektif         | Tekanan Air Pori ($P_{excess}$)            |
| :-------------- | :-------------------------------------------------------------------------- | :------------------------ | :----------------------------------------- |
| **DRAINED**     | Air mengalir bebas. Tidak ada kelebihan tekanan air pori.                   | $E', \nu', c', \phi'$     | $0$ (Lihat `phase_solver.py` Baris 186)    |
| **UNDRAINED A** | Analisis Tegangan Efektif. Air terjebak. Kompresi menyebabkan $P_{excess}$. | $E', \nu', c', \phi'$     | Dihitung dari $\Delta V$ (Lihat Baris 141) |
| **UNDRAINED B** | Mirip Undrained A, tapi kekuatan geser dianggap $c=S_u, \phi=0$.            | $E', \nu', S_u, \phi=0$   | Dihitung dari $\Delta V$ (Lihat Baris 141) |
| **UNDRAINED C** | Analisis Tegangan Total. Tidak menghitung air pori eksplisit.               | $E_u, \nu_u, S_u, \phi=0$ | $0$ (Lihat Baris 135)                      |
| **NON-POROUS**  | Material tidak berpori (beton, baja).                                       | $E, \nu$                  | $0$ (Lihat Baris 186)                      |

### 3.1 Formulasi Pore Water Pressure (PWP) $u_w$

Untuk tipe **UNDRAINED A & B**, solver menggunakan metode **Penalty Formulation** untuk menghitung kenaikan tekanan air pori akibat beban (kelebihan air pori / $P_{excess}$).

**Rumus Utama:**
$$ P_{excess, new} = P_{excess, old} + K_{water} \cdot \Delta \epsilon_{vol} $$

Di mana:
*   $K_{water}$: *Penalty Value* atau bisa disebut juga Bulk Modulus Air (mewakili inkompresibilitas air, biasanya bernilai sangat besar, misal $10^7 \sim 10^9$ kPa).
*   $\Delta \epsilon_{vol} = \Delta \epsilon_{xx} + \Delta \epsilon_{yy}$: Perubahan volume elemen.



Bulk modulus air ($K_w$) yang sangat tinggi ditambahkan ke matriks kekakuan material.

$$ D_{total} = D_{eff} + D_{water} $$
$$ K_w = 2.2 \times 10^6 \text{ kPa} / n \quad (n = \text{porositas}) $$

Perubahan tekanan air pori ekses:
$$ \Delta u_{excess} = B \cdot \Delta \epsilon_{vol} \cdot K_w $$
*(Lihat `phase_solver.py` Baris 134-142)*.

Penerapan ini memungkinkan simulasi perilaku jangka pendek (short-term) lempung jenuh air menggunakan parameter efektif.

**Logika Kode (`phase_solver.py`):**
```python
# Baris 140-142
d_vol = d_epsilon_step[0] + d_epsilon_step[1]
p_exc_new = pwp_excess_start + penalty_val * d_vol
p_total = p_static + p_exc_new
```
Tegangan efektif kemudian dihitung sebagai:
$$ \sigma'_{trial} = \sigma_{total, trial} - P_{total} $$
*(Tegangan total dikurangi tekanan air pori statis + excess)*.