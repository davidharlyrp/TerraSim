# 00. Overview Dahar Solver

Dokumen ini memberikan gambaran umum tentang **Dahar Solver**, mesin Finite Element Analysis (FEA) yang digunakan dalam TerraSim untuk melakukan analisis geoteknik (stabilitas lereng, deformasi, konsolidasi, dll).

Solver ini ditulis menggunakan **Python** dengan akselerasi **Numba** untuk performa komputasi numerik yang tinggi, mendekati performa C++.

## 1. Arsitektur Solver

Solver ini dirancang dengan pendekatan **Staged Construction** (Konstruksi Bertahap), di mana analisis dilakukan fase demi fase. Setiap fase mewarisi kondisi (stress, strain, deformation) dari fase sebelumnya atau biasa disebut dengan stress history.

### Komponen Utama:
1.  **Frontend (React/TypeScript)**: User mendefinisikan geometri, material, dan tahapan (Phases). Data dikirim sebagai JSON (`SolverRequest`) ke backend.
2.  **Backend (Python/FastAPI)**: Menerima request, memvalidasi, dan menjalankan solver.
3.  **Solver Core (`backend/solver`)**: Modul inti yang melakukan perhitungan FEM.

## 2. Struktur File Solver

Kode sumber solver terletak di folder `backend/solver/`. Berikut adalah penjelasan detail setiap file:

| File              | Deskripsi                                                                                                                                                   |
| :---------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `phase_solver.py` | **Jantung Solver**. Mengatur loop utama analisis, Newton-Raphson iteration, assembly matriks global, dan integrasi waktu/load stepping (M-Stage).           |
| `element_t6.py`   | Definisi elemen **Triangular 6-Node (T6)**. Berisi fungsi bentuk (shape functions), matriks B (strain-displacement), dan integrasi numerik Gauss (3 titik). |
| `mohr_coulomb.py` | Implementasi model material konstitutif, khususnya **Mohr-Coulomb**. Menghitung fungsi yield dan algoritma *return mapping* untuk plastisitas.              |
| `k0_procedure.py` | Prosedur inisialisasi tegangan in-situ (**K0 Procedure**). Menghitung tegangan vertikal dan horizontal awal berdasarkan berat tanah dan muka air.           |
| `element_cst.py`  | (Legacy) Elemen Constant Strain Triangle (3-Node). Jarang digunakan, digantikan oleh T6 untuk akurasi lebih tinggi.                                         |

## 3. Alur Kerja Solver (High-Level)

Saat user menekan tombol "Calculate", berikut yang terjadi:

1.  **Parsing Input**: `main.py` menerima JSON dan mengonversinya menjadi objek Python (Mesh, Materials, Phases).
2.  **K0 Procedure (Optional)**: Jika fase pertama adalah "K0 Procedure", solver menghitung tegangan awal tanah horizontal ($\sigma_h = K_0 \sigma_v$) tanpa deformasi.
3.  **Phase Loop**: Solver iterasi melalui setiap fase yang didefinisikan user.
    *   **Load Stepping**: Beban (gravitasi, beban luar) diaplikasikan secara bertahap (M-Stage: 0.0 -> 1.0).
    *   **Global Matrix Assembly**: Matriks kekakuan elemen ($K_{el}$) dihitung dan dirakit menjadi Matriks Kekakuan Global ($K_{global}$).
    *   **Newton-Raphson Solver**: Menyelesaikan persamaan non-linear $K \cdot \Delta u = F_{ext} - F_{int}$ secara iteratif hingga konvergen.
    *   **State Update**: Update tegangan ($\sigma$), regangan ($\epsilon$), dan tekanan air pori ($u_w$) di setiap titik integrasi (Gauss Point).
4.  **Output**: Hasil (Displacement, Stress, Safety Factor) dikemas dalam JSON dan dikirim balik ke frontend.

## 4. Daftar Dokumentasi
Berikut adalah daftar dokumen teknis yang tersedia:

| No | File | Deskripsi |
| :-- | :--- | :--- |
| 00 | [Overview](00_Dahar_Solver_Overview.md) | Gambaran umum solver dan arsitektur sistem. |
| 01 | [UI/UX Frontend](01_UI_UX_Frontend.md) | Fitur antarmuka dan pengalaman pengguna. |
| 02 | [Mesh Generator](02_Mesh_Generator.md) | Implementasi teknis pembuatan mesh T6. |
| 03 | [Input & K0 Procedure](03_Input_and_Inisialisasi_K0.md) | Parsing input dan inisialisasi tegangan. |
| 04 | [Formulasi Elemen T6](04_Formulasi_Elemen_T6.md) | Detail matematis elemen T6. |
| 05 | [Model Konstitutif](05_Model_Konstitutif_dan_Drainase.md) | Mohr-Coulomb dan perilaku drainase. |
| 06 | [Algoritma Solver](06_Algoritma_Solver.md) | Iterasi Newton-Raphson dan assembly global. |
| 07 | [Struktur Output](07_Struktur_Output.md) | Format hasil analisis (NPY). |
| 08 | [Panduan Hoek-Brown](08_Panduan_Implementasi_Hoek_Brown.md) | Implementasi model material batuan. |
| 09 | [Panduan EBR](09_Panduan_Implementasi_Embedded_Beam_Row.md) | Implementasi tiang dan angkur. |

---
*Lanjut ke Dokumen 01 untuk detail UI/UX Frontend.*
