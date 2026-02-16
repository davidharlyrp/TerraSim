# 03. Input dan Inisialisasi (K0 Procedure)

Dokumen ini menjelaskan bagaimana solver menerima input, memproses geometri mesh, dan melakukan inisialisasi tegangan awal (Initial Stress) menggunakan prosedur K0.

## 1. Struktur Data Input (`SolverRequest`)

Solver menerima objek `SolverRequest` (didefinisikan di `backend/models.py`). Objek ini berisi:
*   **Mesh**: Daftar `Nodes` (koordinat x,y) dan `Elements` (konektivitas node).
*   **Materials**: Properti tanah (E, v, c, phi, dll).
*   **Phases**: Urutan tahapan analisis (misal: "Initial Phase", "Excavation", "Loading").
*   **Water Levels**: Garis freatik (phreatic line) untuk tekanan air pori.
*   **Loads**: Beban titik (Point Loads) dan beban garis (Line Loads).

### Parsing Geometri
Solver memetakan elemen ke material berdasarkan `polygon_id`.
*   Setiap elemen memiliki referensi ke `Material` yang aktif pada fase tersebut.
*   Jika material berubah antar fase (misal: penggantian tanah lunak dengan timbunan), solver mendeteksi perubahan ini dan memperbarui properti elemen (Lihat `phase_solver.py` baris 444-534).

## 2. Inisialisasi Tegangan Awal (K0 Procedure)

Untuk analisis geoteknik, kondisi awal tanah **sangat krusial**. Tanah sudah memiliki tegangan akibat berat sendiri sebelum ada beban konstruksi.
Prosedur ini dilakukan di file `backend/solver/k0_procedure.py`.

### Algoritma K0 Procedure
Fungsi utama: `compute_vertical_stress_k0_t6` (Baris 143) & Kernel `compute_k0_stresses_kernel` (Baris 47).

Prosedur ini menghitung tegangan pada setiap **Gauss Point** (titik integrasi) elemen T6 tanpa menyebabkan deformasi (displacement = 0).

#### Langkah-langkah Detail:

1.  **Interpolasi Muka Air (`pwp_results`)**:
    *   Untuk setiap Gauss Point $(x_{gp}, y_{gp})$, solver mencari ketinggian muka air $y_{water}$ di koordinat $x_{gp}$.
    *   Tekanan Air Pori (Pore Water Pressure/PWP), $u_w$:
        $$u_w = \gamma_w \cdot (y_{water} - y_{gp})$$
        Jika $y_{gp} > y_{water}$, maka $u_w = 0$ (zona tak jenuh).
        *(Kode: `k0_procedure.py` baris 70-77)*

2.  **Identifikasi Permukaan Tanah (`y_surf`)**:
    *   Solver mencari koordinat vertikal tertinggi ($y_{max}$) pada posisi horizontal $x_{gp}$. Ini dianggap sebagai permukaan tanah.
    *   *(Kode: `k0_procedure.py` baris 79-84)*

3.  **Integrasi Tegangan Vertikal ($\sigma_v$)**:
    *   Solver mengintegralkan berat unit tanah ($\gamma$) dari permukaan ($y_{surf}$) turun ke titik tinjauan ($y_{gp}$).
    *   $$\sigma_{v, total} = \int_{y_{gp}}^{y_{surf}} \gamma(y) \, dy$$
    *   Gamma ($\gamma$) bisa berupa $\gamma_{unsat}$ (di atas muka air) atau $\gamma_{sat}$ (di bawah muka air).
    *   *(Kode: `k0_procedure.py` baris 88-116. Menggunakan loop diskretisasi 'steps' untuk integrasi numerik)*.

4.  **Hitung Tegangan Efektif Vertikal ($\sigma'_v$)**:
    *   $$ \sigma'_v = \sigma_{v, total} - u_w $$
    *   *(Kode: `k0_procedure.py` baris 117)*

5.  **Hitung Tegangan Horizontal ($\sigma_h$)**:
    *   Menggunakan Koefisien Tekanan Tanah Diam ($K_0$).
    *   Formula Jaky (jika $K_0$ tidak ditentukan manual):
        $$ K_0 = 1 - \sin(\phi) $$
    *   Tegangan Horizontal Efektif:
        $$ \sigma'_h = K_0 \cdot \sigma'_v $$
    *   Tegangan Horizontal Total:
        $$ \sigma_{h, total} = \sigma'_h + u_w $$
    *   *(Kode: `k0_procedure.py` baris 120-134)*

6.  **Tegangan Geser ($\tau_{xy}$)**:
    *   Diasumsikan nol pada kondisi awal (tanah datar/level ground assumption).
    *   $$ \tau_{xy} = 0 $$

### Output K0
Hasilnya adalah tensor tegangan awal:
$$
\boldsymbol{\sigma}_0 = \begin{bmatrix}
\sigma_{h,total} & 0 & 0 \\
0 & \sigma_{v,total} & 0 \\
0 & 0 & \sigma_{h,total} \quad (\text{Plane Strain assumption } \sigma_z)
\end{bmatrix}
$$
Disimpan dalam `element_stress_state` di `phase_solver.py` dan digunakan sebagai titik awal untuk fase analisis plastis selanjutnya.

## 3. Penanganan Tipe Drainase (Drainage Handling) pada K0

Prosedur K0 membedakan perhitungan tegangan efektif dan air pori berdasarkan tipe drainase material (`DrainageType`).

Kode: `k0_procedure.py` (Kernel `compute_k0_stresses_kernel`, Baris 73-77, 133-134).

| Tipe Drainase   | Perilaku Air Pori (PWP)                     | Perhitungan Tegangan Horizontal ($\sigma_h$)                                                        |
| :-------------- | :------------------------------------------ | :-------------------------------------------------------------------------------------------------- |
| **DRAINED**     | Dihitung Hidrostatis ($u_w = \gamma_w z_w$) | $\sigma'_{h} = K_0 \cdot (\sigma_{v,total} - u_w)$ <br> $\sigma_{h,total} = \sigma'_{h} + u_w$      |
| **UNDRAINED A** | Dihitung Hidrostatis (Awal)                 | Sama seperti Drained. Analisis selanjutnya menggunakan parameter efektif.                           |
| **UNDRAINED B** | Dihitung Hidrostatis (Awal)                 | Sama seperti Drained. Analisis selanjutnya menggunakan parameter efektif (biarpun $c=S_u, \phi=0$). |
| **UNDRAINED C** | **Diabaikan ($u_w = 0$)**                   | Analisis Tegangan Total. <br> $\sigma_{h,total} = K_0 \cdot \sigma_{v,total}$                       |
| **NON-POROUS**  | **Diabaikan ($u_w = 0$)**                   | Material kedap air. <br> $\sigma_{h,total} = K_0 \cdot \sigma_{v,total}$                            |

### Detail Implementasi:

1.  **Hitung PWP ($u_w$)**:
    *   Jika `UNDRAINED_C` atau `NON_POROUS`: $u_w = 0$.
    *   Lainnya: $u_w$ dihitung berdasarkan jarak vertikal ke muka air (jika di bawah muka air).

2.  **Hitung K0**:
    Jika `k0_x` tidak didefinisikan manual oleh user:
    *   Menggunakan $\phi$ (sudut geser) material.
    *   $K_0 = 1 - \sin(\phi)$.
    *   *Catatan*: Untuk **Undrained B/C**, jika input $\phi = 0$ (karena menggunakan $S_u$), $K_0$ akan bernilai 1.0 (cairan), kecuali user mendefinisikan $K_0$ manual. Jika $\phi=0$ dan $K_0$ tidak diset, solver mungkin fallback ke 0.5 (lihat baris 131 `k0_procedure.py`).

### Details Handling Material Model pada K0:

Meskipun K0 adalah inisialisasi tegangan, solver menggunakan parameter dari model material untuk menentukan nilai $K_0$:

1.  **Mohr-Coulomb**:
    *   Jika user tidak menginput $K_0$ secara manual, solver mencari nilai Friction Angle ($\phi$).
    *   Menggunakan Formula **Jaky (1944)**: $K_0 = 1 - \sin(\phi)$.
    *   Ini adalah standar asumsi untuk tanah terkonsolidasi normal (Normally Consolidated Soil).

2.  **Linear Elastic**:
    *   Model ini tidak memiliki parameter $\phi$.
    *   Jika $K_0$ tidak diatur manual, solver menggunakan teori elastisitas murni: $K_0 = \frac{\nu}{1 - \nu}$.
    *   *(Kode: `k0_procedure.py` Baris 121-131)*.
    *   **Catatan Penting**: Nilai ini biasanya lebih kecil dari formula Jaky. Untuk analisis geoteknik nyata, disarankan menggunakan Mohr-Coulomb agar mendapatkan tegangan horizontal yang realistis.

3.  **Override Manual**:
    *   Jika user mengisi kolom `K0_x` pada tabel material, solver akan mengabaikan formula otomatis dan menggunakan nilai input tersebut secara langsung.

---
*Lanjut ke Dokumen 05 untuk penanganan Material Model saat proses iterasi plastis.*
