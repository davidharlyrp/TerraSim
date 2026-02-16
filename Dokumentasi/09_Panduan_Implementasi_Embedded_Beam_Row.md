# 09. Panduan Implementasi Embedded Beam Row (EBR)

Dokumen ini menjelaskan teori dan langkah-langkah implementasi fitur **Embedded Beam Row** (EBR) ke dalam TerraSim. Fitur ini digunakan untuk memodelkan struktur pondasi tiang (pile), anchor, atau rock bolt yang berinteraksi dengan massa tanah tanpa perlu menyesuaikan mesh tanah (mesh-independent).

## 1. Konsep Dasar

Embedded Beam Row adalah elemen struktur linier yang dapat ditempatkan di mana saja di dalam domain tanah. Berbeda dengan elemen beam biasa, EBR tidak berbagi node dengan elemen tanah (T6). Interaksi antara EBR dan tanah dilakukan melalui **Special Interface** yang mentransfer beban melalui *skin friction* (sepanjang tiang) dan *tip resistance* (di ujung tiang).

## 2. Detail Mekanisme Interaksi & Keruntuhan

User sering bertanya: *"Apakah perlu interface element seperti pada Plate untuk melihat keruntuhannya?"*

Jawabannya: **Secara fungsi iya, namun secara topologi tidak.**

### 2.1 Interface Standar (Plate) vs. Embedded Interface (EB)
Pada **Plate**, interface adalah elemen fisik (misal interface 1D pada mesh 2D) yang berbagi node dengan tanah. Jika tanah bergerak, node interface ikut bergerak. Keruntuhan dideteksi jika tegangan pada elemen interface tersebut melebihi kriteria Mohr-Coulomb.

Pada **Embedded Beam Row (EBR)**:
1.  **Tanpa Node Bersama**: EBR "melayang" di atas elemen tanah T6.
2.  **Virtual Springs**: Interaksi dimodelkan sebagai rangkaian pegas non-linear yang menghubungkan setiap titik integrasi pada balok ($x_{beam}$) ke posisi yang sama di dalam elemen tanah ($x_{soil}$).
3.  **Local Displacement Mapping**: Solver harus menghitung perpindahan tanah di lokasi balok secara dinamis:
    $$ u_{soil}(x_{beam}) = \sum N_i^{soil}(\xi, \eta) \cdot u_i^{soil} $$
    Dimana $(\xi, \eta)$ adalah koordinat lokal di dalam elemen tanah T6 tempat balok berada.

### 2.2 Kriteria Keruntuhan (Failure Mechanism)
Keruntuhan pada EBR tidak terjadi karena elemen interface "patah", melainkan karena **Gaya Antarmuka (Interface Force)** telah mencapai batas plastisnya:

*   **Skin Friction Limit ($T_{max}$)**: Gaya geser aksial maksimum yang bisa ditransfer per satuan panjang (kN/m). 
    *   Jika $t_{axial} < T_{max}$: Hubungan bersifat elastis (pegas kaku).
    *   Jika $t_{axial} \ge T_{max}$: Terjadi "slip" atau leleh. Gaya ditahan tetap pada nilai $T_{max}$ meskipun tanah bergerak lebih jauh. Ini adalah simulasi keruntuhan antarmuka.
*   **Tip Resistance ($F_{max}$)**: Gaya tekan maksimum pada ujung tiang. Jika beban di ujung tiang melebihi $F_{max}$, tiang akan "menusuk" tanah tanpa bisa menahan beban lebih besar lagi (end-bearing failure).

**Algoritma Return Mapping**:
Di setiap iterasi solver:
1. Hitung $\Delta u = u_{beam} - u_{soil}$.
2. Hitung gaya trial: $t_{trial} = R_s \cdot \Delta u$.
3. Cek batas: $t_{final} = \min(t_{trial}, T_{max})$.
4. Jika $t_{final} < t_{trial}$, maka titik tersebut dinyatakan **Yielded** (Runtuh).

### 2.3 Koneksi Ujung (Fixed, Hinged, Pin)
Pada Plaxis, kita dapat mengatur tipe koneksi di bagian **top** atau **bottom** tiang. Implementasi di solver adalah sebagai berikut:

1.  **Hinged (Sendi)**: 
    *   **Konsep**: Hanya perpindahan ($u_x, u_y$) yang tersambung antara tiang dan struktur di atasnya (misal Footing/Plate), sementara rotasi ($\theta$) bebas.
    *   **Implementasi**: Gunakan **Point-to-Point Coupling** pada DOF translasi saja.
2.  **Fixed (Jepit)**: 
    *   **Konsep**: Baik perpindahan maupun rotasi terkunci bersama struktur penyambung. Moment akan tertransfer sepenuhnya.
    *   **Implementasi**: Tambahkan constraint pada DOF translasi dan rotasi ($u_x, u_y, \theta$).
3.  **Free (Bebas)**:
    *   **Konsep**: Ujung tiang tidak tersambung ke struktur lain, hanya berinteraksi dengan tanah melalui interface.
    *   **Implementasi**: Tidak ada constraint tambahan, biarkan pegas interface yang bekerja.

---

## 3. Peran Parameter Material & Geometri

Dalam model 2D Plane Strain, properti sebuah tiang tunggal harus dikonversi menjadi properti per satuan panjang (row).

| Parameter | Nama | Peran dalam Kalkulasi |
| :--- | :--- | :--- |
| **$L_{spacing}$** | Spacing | **Paling Krusial**. Digunakan untuk membagi kekakuan tiang tunggal ($EA, EI$) agar menjadi nilai ekivalen per meter lari dalam model 2D. |
| **$E$** | Modulus Young | Menentukan kekakuan aksial dan lentur tiang. |
| **$A$** | Luas Penampang | Dikombinasikan dengan E menjadi kekakuan aksial ($EA$). Dalam solver, nilai yang masuk adalah $EA_{2D} = (E \cdot A) / L_{spacing}$. |
| **$I$** | Inersia | Menentukan kekakuan lentur tiang ($EI$). Nilai masuk: $EI_{2D} = (E \cdot I) / L_{spacing}$. |
| **$w$** | Berat Jenis | Berat tiang per satuan panjang. Berkontribusi pada gaya gravitasi elemen ($F_{grav}$). |

### Hubungan Spacing dalam 2D
Jika Anda memiliki tiang dengan diameter 0.6m setiap jarak 2.0m ($L_{spacing}$), maka solver akan menganggap ada sebuah "dinding virtual" dengan kekakuan yang sudah diencerkan (*smeared stiffness*). Semua input yang bersifat absolut ($EA, EI, t_{max}, f_{max}$) akan **dibagi** dengan $L_{spacing}$ sebelum proses perakitan matriks global.

---

## 4. Formulasi Numerik (Matriks & Kalkulasi)

### 2.1 Diskritisasi Elemen
EPR dimodelkan sebagai elemen garis 3-titik (quadratic beam) untuk menjaga konsistensi dengan elemen tanah T6.
*   **Beam Nodes**: $n_1, n_2, n_3$ (memiliki DOF $u_x, u_y$ dan $\theta$).
*   **Soil Connectivity**: Setiap titik integrasi pada beam harus "tahu" di elemen tanah mana ia berada.

### 2.2 Matriks Kekakuan Elemen ($K_{total}$)
Kekakuan total elemen embedded adalah penjumlahan dari kekakuan beam itu sendiri dan kekakuan antarmuka (interface):
$$ K_{eb} = K_{beam} + K_{interface} $$

#### A. Matriks Kekakuan Beam ($K_{beam}$)
Menggunakan teori balok standard (Euler-Bernoulli atau Timoshenko):
$$ K_{beam} = \int_{L} B_b^T D_b B_b \, dL $$
Dimana $B_b$ adalah matriks regangan-perpindahan balok dan $D_b$ adalah matriks kekakuan material balok ($EA$ dan $EI$).

#### B. Matriks Kekakuan Antarmuka ($K_{interface}$)
Ini adalah bagian krusial yang menghubungkan balok dengan tanah. Misalkan $u_s$ adalah perpindahan tanah dan $u_b$ adalah perpindahan balok. Perpindahan relatif $\Delta u$ adalah:
$$ \Delta u = u_b - u_s $$
Gaya interaksi $t$ (traction) didefinisikan sebagai:
$$ t = R_s \cdot \Delta u $$
Dimana $R_s$ adalah matriks kekakuan antarmuka (coupling spring stiffness).

Dalam formulasi elemen hingga, interface menyumbangkan kekakuan ke node balok ($bb$), node tanah ($ss$), dan cross-coupling ($bs$ dan $sb$):
$$ K_{interface} = \begin{bmatrix} K_{bb} & K_{bs} \\ K_{sb} & K_{ss} \end{bmatrix} $$

**Formulasi Coupling:**
Jika $N_{soil}$ adalah fungsi bentuk tanah dan $N_{beam}$ adalah fungsi bentuk balok, maka:
$$ K_{ss} = \int_{L} N_{soil}^T R_s N_{soil} \, dL $$
$$ K_{bb} = \int_{L} N_{beam}^T R_s N_{beam} \, dL $$
$$ K_{sb} = -\int_{L} N_{soil}^T R_s N_{beam} \, dL $$

### 2.3 Mekanisme Transfer Beban
Terdapat dua komponen utama transfer beban:
1.  **Skin Friction ($T_{max}$)**: Batas gaya geser sepanjang selimut tiang.
2.  **Base Resistance ($F_{max}$)**: Batas gaya tekan di ujung tiang (axial tip resistance).

Kekakuan $R_s$ akan bersifat elastis sampai mencapai nilai $T_{max}$ atau $F_{max}$, kemudian akan berperilaku plastis (limit state) menggunakan algoritma *return mapping* serupa dengan Mohr-Coulomb.

---

## 5. Rencana Perubahan Kode

### A. Backend: `backend/models.py`
1.  Tambahkan class `EmbeddedBeamRow`:
    ```python
    class EmbeddedBeamRow(BaseModel):
        id: str
        nodes: List[Point]  # Koordinat geometri beam
        material_id: str
        spacing: float      # Jarak antar tiang (out-of-plane)
        t_max: float        # Skin friction limit
        f_max: float        # Tip resistance limit
    ```
2.  Update `SolverRequest` untuk menyertakan daftar `embedded_beams`.

### B. Solver: `backend/solver/element_embedded_beam.py` [NEW FILE]
File ini akan menangani logika integrasi beam-soil:
1.  `find_containing_soil_element(point, mesh)`: Fungsi untuk mencari elemen T6 yang membungkus koordinat beam.
2.  `compute_embedded_beam_matrices(...)`: Menghitung $K_{eb}$ dan gaya internal $F_{int}$ dari beam dan interface.
3.  `mapping_soil_displacement(u_global, soil_element_id, local_coords)`: Mendapatkan $u_s$ dari hasil iterasi global.

### C. Solver Kernel: `backend/solver/phase_solver.py`
Modifikasi pada loop `solve_phases`:
1.  **Assembly Tahap 1**: Rakit $K_{global}$ tanah seperti biasa.
2.  **Assembly Tahap 2**: Iterasi setiap `EmbeddedBeamRow`.
    *   Cari elemen tanah yang beririsan.
    *   Hitung $K_{eb}$ dan tambahkan ke $K_{global}$ di alamat DOF yang sesuai (Node balok baru + Node tanah terkait).
3.  **Newton-Raphson Loop**:
    *   Hitung gaya residual $R = F_{ext} - (F_{int,soil} + F_{int,beam} + F_{int,interface})$.
    *   Lakukan update $u$ hingga konvergen.

---

## 6. Langkah Implementasi Detail (Step-by-Step)

1.  **Definisi Struktur Data**: Buat model data di frontend dan backend untuk menyimpan properti EBR (E, I, Spacing, Friction).
2.  **Preprocessing (Geometry Mapping)**: Di awal setiap fase, identifikasi posisi EBR terhadap mesh tanah. Lakukan *quadtree search* untuk mengoptimalkan pencarian elemen tanah yang mengandung titik integrasi beam.
3.  **Kalkulasi Stiffness**: Implementasikan integrasi numerik (Gauss 2-titik untuk beam) untuk menghitung kontribusi interface terhadap matriks global.
4.  **Batas Plastisitas**: Tambahkan logika pengecekan $T_{max}$ pada setiap titik integrasi interface. Jika $\tau > T_{max}$, maka gaya interaksi dipangkas ke $T_{max}$ (perfectly plastic).
5.  **Output & Visualisasi**: Tambahkan hasil gaya aksial ($N$) dan momen lentur ($M$) balok ke dalam metadata respon solver agar bisa digambar di frontend.

---
> [!TIP]
> **Penting untuk Stabilitas**: Nilai kekakuan antarmuka ($R_s$) harus dipilih secara hati-hati. Jika terlalu kaku, matriks bisa menjadi ill-conditioned. Jika terlalu lunak, akan terjadi penetrasi numerik yang tidak realistis antara tiang dan tanah.
