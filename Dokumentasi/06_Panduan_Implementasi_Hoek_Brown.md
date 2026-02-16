# 06. Panduan Pengembangan: Model Material Hoek-Brown (Rock)

Dokumen ini berisi panduan teknis untuk mengimplementasikan model konstitutif **Hoek-Brown** ke dalam TerraSim. Model ini sangat penting untuk simulasi mekanika batuan.

## 1. Parameter Input Baru

Untuk mendukung Hoek-Brown, kelas `Material` di `backend/models.py` perlu ditambahkan parameter berikut:

| Parameter                         | Simbol        | Satuan | Deskripsi                                           |
| :-------------------------------- | :------------ | :----- | :-------------------------------------------------- |
| **Uniaxial Compressive Strength** | $\sigma_{ci}$ | kPa    | Kuat tekan uniaksial batuan utuh (intact rock).     |
| **Geological Strength Index**     | $GSI$         | -      | Indeks kualitas massa batuan (0-100).               |
| **Intact Rock Parameter**         | $m_i$         | -      | Konstanta material batuan utuh (5-35).              |
| **Disturbance Factor**            | $D$           | -      | Faktor kerusakan akibat peledakan/penggalian (0-1). |

## 2. Formulasi Matematika

### 2.1 Parameter Turunan
Sebelum menghitung kekuatan, solver harus menghitung parameter $m_b, s,$ dan $a$:

$$ m_b = m_i \cdot \exp \left( \frac{GSI - 100}{28 - 14D} \right) $$
$$ s = \exp \left( \frac{GSI - 100}{9 - 3D} \right) $$
$$ a = \frac{1}{2} + \frac{1}{6} \left( \exp \left( -\frac{GSI}{15} \right) - \exp \left( -\frac{20}{3} \right) \right) $$

### 2.2 Kriteria Keruntuhan (Yield Function)
Kriteria keruntuhan Hoek-Brown didefinisikan sebagai:

$$ f = \sigma_1 - \sigma_3 - \sigma_{ci} \left( m_b \frac{\sigma_3}{\sigma_{ci}} + s \right)^a = 0 $$

*Catatan: $\sigma_1$ adalah tegangan utama maksimum (paling tekan) dan $\sigma_3$ adalah tegangan utama minimum.*

## 3. Rencana Perubahan Kode

### A. Backend: `backend/models.py`
1.  Tambahkan `HOEK_BROWN = "hoek_brown"` ke dalam enum `MaterialModel`.
2.  Tambahkan field opsional ke kelas `Material`:
    ```python
    sig_ci: Optional[float] = None
    gsi: Optional[float] = None
    m_i: Optional[float] = None
    disturbance_factor: Optional[float] = None
    ```

### B. Solver: `backend/solver/hoek_brown.py`
Implementasikan fungsi baru dengan JIT (Numba):
1.  `@njit hoek_brown_yield(...)`: Menghitung nilai $f$.
2.  `@njit return_mapping_hoek_brown(...)`: Melakukan proyeksi tegangan jika $f > 0$.

#### Referensi: Logika Radial Return (MC)
Sebagai acuan, pelajari fungsi `return_mapping_mohr_coulomb` (Baris 33-95). Berikut adalah alur yang harus diadaptasi untuk Hoek-Brown:

*   **Langkah 1: Transformasi ke Mohr Space**
    Hitung pusat ($\sigma_{avg}$) dan jari-jari ($R_{trial}$) dari tegangan trial.
*   **Langkah 2: Hitung Kapasitas ($R_{limit}$)**
    Pada MC, $R_{limit}$ dihitung secara eksplisit: $c \cos \phi - \sigma_{avg} \sin \phi$.
*   **Langkah 3: Scaling & Koreksi**
    Koreksi dilakukan secara radial (pusat tetap, jari-jari diciutkan):
    $$ \eta = \frac{R_{limit}}{R_{trial}} $$
*   **Langkah 4: Rekonstruksi Cartesian**
    Kembalikan $R_{corrected}$ ke $\sigma_{xx}, \sigma_{yy}, \tau_{xy}$ menggunakan sudut orientasi asli.

#### Perbedaan Vital untuk Hoek-Brown:
Karena kriteria Hoek-Brown memiliki pangkat $a$ (non-linear), $R_{limit}$ tidak bisa dihitung langsung sesederhana MC. Solver menggunakan **Newton-Raphson Iteration** untuk mencari jari-jari lingkaran Mohr ($R$) yang memenuhi $f=0$ pada $\sigma_{avg}$ yang konstan (Radial Return).

**Matematika Newton-Raphson untuk HB:**

Kita ingin mencari akar dari fungsi $g(R)$:
$$ g(R) = 2R - \sigma_{ci} \left( \frac{m_b (-\sigma_{avg} - R)}{\sigma_{ci}} + s \right)^a = 0 $$

*   **Turunan $g'(R)$**:
    $$ g'(R) = 2 + a \cdot m_b \left( \frac{m_b (-\sigma_{avg} - R)}{\sigma_{ci}} + s \right)^{a-1} $$
*   **Update Iterasi**:
    $$ R_{baru} = R_{lama} - \frac{g(R_{lama})}{g'(R_{lama})} $$

Proses ini biasanya konvergen dalam 3-5 iterasi. Jika nilai di dalam kurung pangkat menjadi negatif, solver akan memaksa kondisi ke batas **Tension Cut-off** (titik puncak kerucut HB).

### C. Solver Kernel: `backend/solver/phase_solver.py`
Di dalam fungsi `compute_elements_stresses_numba`:
1.  Tambahkan percabangan logika:
    ```python
    if mmodel == 2: # Hoek-Brown
        sig_new, _, yld = return_mapping_hoek_brown(
            sigma_trial, sig_ci, gsi, m_i, D_factor, D_el
        )
    ```
2.  **Batasan Drainase**: Tambahkan validasi agar Hoek-Brown hanya bisa digunakan jika `drainage_type` adalah `DRAINED` atau `NON_POROUS`. Jika user memilih Undrained, kirim error sebelum perhitungan dimulai.

### D. Inisialisasi K0: `backend/solver/k0_procedure.py`
Untuk batuan (Hoek-Brown), nilai $K_0$ biasanya dihitung berdasarkan teori elastisitas:
$$ K_0 = \frac{\nu}{1 - \nu} $$

## 4. Penanganan SRM (Safety Analysis)

Pada analisis kestabilan lereng batuan, parameter kekuatan harus direduksi bertahap hingga terjadi keruntuhan numerik.

### 4.1 Rumus Reduksi SRM
Untuk model Hoek-Brown, parameter yang direduksi oleh faktor keamanan (SF) adalah $\sigma_{ci}, m_b,$ dan $s$:

1.  **Reduksi Uniaxial Strength:**
    $$ \sigma_{ci, trial} = \frac{\sigma_{ci, original}}{SF} $$
2.  **Reduksi Parameter Massa Batuan:**
    $$ m_{b, trial} = \frac{m_{b, original}}{SF} $$
    $$ s_{trial} = \frac{s_{original}}{SF} $$

*Catatan: Parameter 'a' biasanya dianggap konstan karena lebih berkaitan dengan geometri rekahan (GSI) daripada kekuatan material itu sendiri.*

update, formula terbaru digunakan dari artikel jurnal
*"A strength reduction method based on the Generalized Hoek-Brown criterion for rock slope stability analysis"*
oleh Yuan Wei, Li Jiaxin, Li Zonghong, Wang Wei, Sun Xiaoyun


### 4.2 Implementasi di Loop Solver
Di dalam `compute_elements_stresses_numba`, jika `is_srm` bernilai true, maka nilai `sigma_ci_val`, `mb_val`, dan `s_val` harus dibagi dengan `target_m_stage` sebelum memanggil fungsi `return_mapping_hoek_brown`.

---

## 5. Perubahan di Frontend
1.  **Material Editor**: Tambahkan form input untuk $\sigma_{ci}, GSI, m_i,$ dan $D$.
2.  **Logic Visibility**: Form MC (c, phi) harus disembunyikan jika user memilih model Hoek-Brown, dan sebaliknya.
3.  **Drainage Guard**: Berikan peringatan jika user memilih Hoek-Brown tapi tipe drainasenya bukan Drained/Non-Porous.

---
> [!IMPORTANT]
> Karena Hoek-Brown memiliki permukaan yield yang melengkung (non-linear), implementasi **Newton-Raphson** pada level Return Mapping harus memiliki kontrol konvergensi yang ketat untuk menghindari divergensi numerik.
