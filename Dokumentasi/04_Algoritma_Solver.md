# 04. Algoritma Solver (Matrix Assembly & Nonlinear Loop)

Dokumen ini menjelaskan "Otak" dari solver: bagaimana persamaan global disusun dan diselesaikan secara iteratif.

File terkait: `backend/solver/phase_solver.py` (Fungsi `solve_phases`).

## 1. Global Matrix Assembly

Solusi Metode Elemen Hingga (FEM) didasarkan pada penyelesaian sistem persamaan linear:
$$ [K] \{u\} = \{F\} $$

### Struktur Matriks Global ($K_{global}$)
Karena matriks kekakuan sangat besar dan jarang (sparse), solver menggunakan format **Sparse Matrix (Coordinate Format / COO)** dari SciPy.

**Apa itu Sparse Matrix?**
Dalam simulasi FEA, sebuah node hanya berhubungan dengan node tetangganya saja. Artinya, sebagian besar entri dalam matriks kekakuan global bernilai **nol (0)**. 
*   Jika kita menggunakan matriks biasa (dense), kita akan membuang memori RAM untuk menyimpan angka nol tersebut. 
*   **Sparse Matrix** hanya menyimpan nilai yang **tidak nol**, sehingga jauh lebih hemat memori dan cepat untuk perhitungan besar.

**Mengenal Format COO (Coordinate):**
Format ini menyimpan matriks menggunakan tiga array:
1.  `data`: Berisi nilai numerik stiffness.
2.  `row`: Berisi indeks baris dari nilai tersebut.
3.  `col`: Berisi indeks kolom dari nilai tersebut.

**Implementasi di Solver (`phase_solver.py`):**
Solver melakukan prakalkulasi indeks baris dan kolom di awal fase (Baris 615-627):
```python
# Prakalkulasi indeks untuk efisiensi
rows.append(r_dof)
cols.append(c_dof)
active_row_indices = np.array(rows, dtype=np.int32)
active_col_indices = np.array(cols, dtype=np.int32)
```
Pada setiap iterasi Newton-Raphson, solver hanya perlu mengumpulkan nilai `data` baru, lalu menyusunnya dengan indeks yang sudah ada:
`K_global = coo_matrix((data, (rows, cols)))`

### 1.1 Proses Assembly (Mapping Element ke Global)

Assembly adalah proses "merakit" potongan-potongan kecil (Matriks Elemen) menjadi satu kesatuan besar (Matriks Global). Bayangkan ini seperti puzzle.

**Bagaimana menghitung alamat (Mapping)?**
Setiap node memiliki 2 Degrees of Freedom (DOF), yaitu gerakan ke arah **X** dan **Y**. 
Solver harus tahu: *"Nilai kekakuan di Node 2 Elemen A harus ditaruh di baris/kolom berapa pada matriks global?"*

Rumus konversinya sangat sederhana:
*   **Global Indeks X** $= 2 \times \text{NodeID}$
*   **Global Indeks Y** $= 2 \times \text{NodeID} + 1$

**Contoh Tabel Mapping untuk Node 2:**
| Identitas      | Arah           | Perhitungan      | Indeks Global |
| :------------- | :------------- | :--------------- | :------------ |
| **Node ID: 2** | Horisontal (X) | $2 \times 2$     | **4**         |
| **Node ID: 2** | Vertikal (Y)   | $2 \times 2 + 1$ | **5**         |

Jadi, jika **Elemen A** dan **Elemen B** sama-sama memiliki **Node 2**, mereka berdua akan menyetor hasil hitungannya ke Baris/Kolom **4** dan **5** di Matriks Global.

**Langkah Kerja Solver:**
1.  **Elemen A** menghitung matriks internalnya ($12 \times 12$).
2.  Suku ke-3 dan ke-4 dari matriks Elemen A (yang secara lokal adalah milik Node ke-2 di elemen tersebut) akan "ditembakkan" ke lokasi Global DOF **[4, 5]**.
3.  **Elemen B** juga menghitung matriksnya sendiri.
4.  Suku yang berhubungan dengan Node 2 di Elemen B juga akan "ditembakkan" ke lokasi yang sama: Global DOF **[4, 5]**.
5.  **Di Matriks Global**: Nilai dari Elemen A dan Elemen B **dijumlahkan** secara otomatis oleh sistem COO Matrix.

### 1.2 Konektivitas dan Penamaan Node (Topology)

Mungkin Anda bertanya: *"Bagaimana solver tahu Node 2 milik Elemen A dan juga Elemen B?"*

**1. Sistem Penamaan (Indexing):**
Solver menggunakan indeks berbasis angka (**0-based integer**). Jika mesh Anda punya 1000 node, maka node tersebut bernama `Node 0, Node 1, ..., Node 999`. Nama ini tidak berubah selama simulasi.

**2. Konektivitas Elemen (Connectivity List):**
Data mesh yang masuk ke solver (dari `MeshResponse`) memiliki daftar konektivitas. Contohnya:
*   `Elemen[0] = [10, 25, 30, 45, 12, 0]` -> Artinya Elemen 0 dibentuk oleh node-node dengan ID tersebut.
*   `Elemen[1] = [25, 50, 60, 75, 80, 10]` -> Perhatikan ada Node **10** dan **25** yang muncul lagi di sini.

**3. Cara Solver Tahu Bertetangga:**
Solver tidak mencari tetangga secara geografis, melainkan secara **Topologis**.
*   Elemen-elemen yang memiliki angka ID Node yang sama di dalam daftar konektivitasnya otomatis dianggap bertetangga dan saling berbagi kekakuan.
*   Inilah alasan mengapa ID Node harus unik dan konsisten: ID tersebut adalah "alamat" di mana energi kekakuan akan disimpan di Matriks Global.

**Analogi:** ID Node adalah nomor rekening bank. Elemen A mentransfer uang ke Rekening 10, Elemen B juga mentransfer ke Rekening 10. Di akhir hari, Bank (Solver) hanya menjumlahkan total saldo di Rekening 10.

**Visualisasi Matriks Global:**
Jika kita punya 4 node total (8 DOF), bentuk assembly-nya akan seperti ini:

$$
K_{global} = \begin{bmatrix}
[k_1^A] & [k_{12}^A] & [k_{13}^A] & 0 \\
[k_{21}^A] & \mathbf{[k_2^A + k_2^B]} & [k_{23}^{A+B}] & [k_{24}^B] \\
[k_{31}^A] & [k_{32}^{A+B}] & \mathbf{[k_3^A + k_3^B]} & [k_{34}^B] \\
0 & [k_{42}^B] & [k_{43}^B] & [k_4^B]
\end{bmatrix}_{8 \times 8}
$$

*   **Kotak $[k]$**: Adalah sub-matriks $2 \times 2$.
*   **Elemen A**: Mengisi area warna 'A'.
*   **Elemen B**: Mengisi area warna 'B'.
*   **$\mathbf{k^A + k^B}$**: Area "pertemuan" (overlap) di mana nilai kekakuan dari kedua elemen saling memperkuat satu sama lain.
*   **Nol (0)**: Area kosong (sparse) karena Node 1 tidak terhubung langsung dengan Node 4.

### Boundary Conditions (Syarat Batas)
Node yang terkekang (Fixed Nodes) tidak boleh bergerak.
*   **Full Fixity**: $u_x = 0, u_y = 0$.
*   **Normal Fixity (Roller)**: $u_x = 0$ (pada dinding vertikal) atau $u_y = 0$ (pada dasar).

Solver menangani ini dengan mempartisi matriks global:
1.  Identifikasi *Free DOFs* (derajat kebebasan yang boleh bergerak).
2.  Hanya `K_free` (sub-matriks dari Free DOFs) yang diselesaikan.
    *(Baris 1056 : `du_free = spsolve(K_free, R_free)`)*

## 2. Nonlinear Solver Loop (Newton-Raphson)

Tanah bukan material linear; kekuatannya terbatas dan perilakunya berubah seiring deformasi. Oleh karena itu, beban tidak bisa diberikan sekaligus 100%. Solver menggunakan kombinasi **Incremental Loading** dan **Newton-Raphson Iteration**.

### 2.1 Konsep M-Stage ($\Sigma M_{load}$)
Solver menerapkan beban secara bertahap menggunakan pengali beban yang disebut `m_stage`:
*   $M_{stage} = 0$: Belum ada beban tambahan.
*   $M_{stage} = 1$: Beban fase ini (misal kenaikan timbunan) sudah terpasang 100%.

Jika solver gagal di tengah jalan (misal pada 0.65), artinya model tanah **runtuh** sebelum beban penuh tercapai.

### 2.2 Makna "Runtuh" dalam Analisis Geoteknik

Kondisi "Runtuh" atau *Collapse* memiliki dua interpretasi yang saling berkaitan:

**1. Makna Fisik (Mechanical Failure):**
Tanah sudah tidak sanggup lagi menahan beban tambahan. Secara fisik, telah terbentuk **Mekanisme Keruntuhan** (seperti bidang gelincir atau *slip surface* yang menyambung dari satu sisi ke sisi lain). 
*   Pada titik ini, perpindahan tanah akan bertambah sangat besar meskipun beban tidak ditambah lagi. 
*   Tanah berperilaku seperti cairan kental yang terus mengalir (*plastic flow*).

**2. Makna Numeris (Numerical Divergence):**
Secara matematis, ini berarti iterasi Newton-Raphson **divergen** (gagal konvergen).
*   **Ketidakseimbangan Gaya**: Gaya Eksternal ($F_{ext}$) terus memaksa, sementara Gaya Internal ($F_{int}$) tidak bisa bertambah karena semua elemen di jalur keruntuhan sudah mencapai batas Mohr-Coulomb (tegangannya "dipangkas").
*   **Residual Abadi**: Karena $F_{int}$ tidak bisa naik lagi, maka sisa gaya $R = F_{ext} - F_{int}$ tidak akan pernah bisa mencapai nol seberapa banyak pun iterasi yang dilakukan.
*   **Matriks Singular**: Saat mekanisme runtuh terbentuk, matriks kekakuan tangen $[K_t]$ menjadi tidak stabil atau mendekati *singular*, sehingga sistem persamaan tidak bisa lagi diselesaikan secara akurat.

### 2.3 Matriks Kekakuan Tangen ($K_t$)

Jika Matriks Kekakuan Global $[K]$ adalah nilai kekakuan awal, maka **Matriks Kekakuan Tangen** $[K_t]$ adalah nilai kekakuan "seketika" (kemiringan kurva beban-deformasi) pada kondisi beban saat ini.

**Formulasi Matriks:**
Matriks $K_t$ global dibangun dari integrasi matriks konstitutif tangen ($D_{ep}$) di setiap elemen:
$$ [K_t] = \sum_{elemen} \int_{V} \mathbf{B}^T \cdot \mathbf{D}_{ep} \cdot \mathbf{B} \, dV $$

Di mana:
*   $\mathbf{D}_{ep}$: Adalah matriks yang menghubungkan inkremen tegangan dan regangan ($\Delta \sigma = D_{ep} \Delta \epsilon$). 
*   Jika tanah **Elastis**: $D_{ep} = D_{elastic}$.
*   Jika tanah **Plastis (Leleh)**: $D_{ep}$ seharusnya berkurang nilainya karena tanah sudah "lunak".

**Strategi Solver (Modified Newton-Raphson):**
Dalam implementasi ini (Baris 1045 di `phase_solver.py`), solver menggunakan **Modified Newton-Raphson**. 
*   Alih-alih memperbarui $D_{ep}$ di setiap iterasi kecil (yang sangat lambat dan sering membuat error numerik), solver menggunakan matriks kekakuan tangen yang stabil (menggunakan $D_{elastic}$ atau $D$ awal langkah) untuk mengarahkan prediksi $\delta u$.
*   Koreksi keruntuhan material tetap dilakukan secara presisi melalui **Return Mapping** pada saat menghitung gaya internal ($F_{int}$).

**Kenapa bisa Singular?**
Matriks menjadi singular (tidak bisa di-invers) saat nilai-nilai di dalam $[K_t]$ menjadi sedemikian kecil atau tidak stabil sehingga determinannya mendekati nol. Secara fisik, ini berarti struktur sudah kehilangan stabilitas statisnya; tidak ada lagi "perlawanan" (stiffness) dari tanah terhadap beban tambahan.

Oleh karena itu, angka $M_{stage}$ terakhir (misal 0.65) adalah indikasi bahwa struktur Anda hanya mampu menahan 65% dari beban rencana sebelum mengalami kegagalan.

### 2.4 Alur Iterasi Newton-Raphson (Detail)

Setiap satu langkah beban ($M_{stage} + \Delta step$), solver akan melakukan iterasi berikut hingga seimbang:

**1. Hitung Gaya Eksternal Target ($F_{ext}$):**
$$ F_{ext, target} = F_{initial} + (\Sigma M_{stage} \cdot \Delta F_{fase}) $$
*(Ini adalah beban total yang 'seharusnya' ditahan oleh struktur pada langkah ini)*.

**2. Hitung Gaya Internal ($F_{int}$):**
Solver memanggil kernel `compute_elements_stresses_numba` untuk menghitung tegangan di setiap Gauss Point yang sudah dikoreksi oleh batas Mohr-Coulomb:
$$ F_{int} = \sum \int_V B^T \cdot \sigma_{corrected} \, dV $$

**3. Cek Gaya Tidak Seimbang (Residual $R$):**
Inilah kunci dari metode ini. Jika ada elemen yang "leleh", maka $F_{int}$ akan lebih kecil dari $F_{ext}$. Selisihnya disebut **Residual**:
$$ R = F_{ext, target} - F_{int} $$
Jika $R$ sangat kecil (di bawah toleransi), maka langkah beban ini dianggap **Lulus (Konvergen)**.

**4. Koreksi Displacement ($\delta u$):**
Jika $R$ masih besar, sisa gaya ini harus "dibuang" ke elemen lain yang masih kuat. Solver menghitung tambahan gerakan ($\delta u$) menggunakan matriks kekakuan tangen ($K_t$):
$$ [K_t] \cdot \{\delta u\} = \{R\} $$
$$ u_{baru} = u_{lama} + \delta u $$

**5. Ulangi (Iterasi):**
Dengan $u_{baru}$ tersebut, solver menghitung ulang tegangan, $F_{int}$, dan $R$ yang baru. Proses ini berulang (biasanya 3-15 kali) sampai sisa gaya $R$ benar-benar hilang.

### 2.5 Kriteria Konvergensi
Solver menghentikan iterasi jika rasio norma residual terhadap beban dasar sudah di bawah batas:
$$ \frac{||R_{free}||}{||F_{base}||} < \text{Toleransi} $$
Default toleransi adalah **0.01 (1%)**.

*(Lihat implementasi lengkap di `phase_solver.py` Baris 991-1062)*.

### Fitur Penting:
*   **Automatic Step Sizing**: Jika iterasi gagal (divergen), `step_size` dikurangi setengahnya, dan langkah diulang. Jika terlalu cepat konvergen, `step_size` diperbesar.
*   **Numba Optimization**: Perhitungan $F_{int}$ dan $K_{element}$ dilakukan menggunakan JIT compiler (Numba) parallel untuk kecepatan maksimal.

## 3. Safety Analysis (Strength Reduction Method / SRM)

Selain deformasi, salah satu fitur krusial solver adalah menghitung **Safety Factor (SF)** atau Faktor Keamanan menggunakan metode **Strength Reduction Method (SRM)**.

### 3.1 Filosofi SRM
Dalam geoteknik, Faktor Keamanan didefinisikan sebagai rasio kekuatan geser yang tersedia terhadap kekuatan geser yang dibutuhkan untuk keseimbangan:
$$ SF = \frac{\tau_{tersedia}}{\tau_{dibutuhkan}} $$

Lahirnya keruntuhan terjadi saat kekuatan tanah direduksi sedemikian rupa hingga struktur berada di ambang keruntuhan.

### 3.2 Formulasi Reduksi Kekuatan
Pada fase `SAFETY_ANALYSIS`, solver tidak menambah beban eksternal (beban tetap konstan), melainkan **mengurangi secara bertahap** parameter kekuatan tanah ($c$ dan $\phi$) menggunakan faktor reduksi $\Sigma M_{sf}$ (yang direpresentasikan oleh parameter `m_stage` dalam kode).

Rumus reduksi untuk setiap langkah iterasi adalah:
1.  **Reduksi Kohesi ($c$):**
    $$ c_{trial} = \frac{c_{original}}{\Sigma M_{sf}} $$
2.  **Reduksi Sudut Geser Dalam ($\phi$):**
    Karena hubungan geser bersifat nonlinear ($\tan \phi$), maka yang direduksi adalah nilai tangen-nya:
    $$ \tan(\phi_{trial}) = \frac{\tan(\phi_{original})}{\Sigma M_{sf}} $$
    $$ \phi_{trial} = \arctan \left( \frac{\tan(\phi_{original})}{\Sigma M_{sf}} \right) $$

### 3.3 Alur Kerja SRM di Solver
1.  **Inisialisasi**: $\Sigma M_{sf}$ dimulai dari 1.0 (kekuatan asli).
2.  **Incremental Reduction**: $\Sigma M_{sf}$ naik perlahan (misal: 1.0 $\to$ 1.1 $\to$ 1.2 ...). Di setiap kenaikan, solver mencoba menyelesaikan iterasi Newton-Raphson hingga konvergen.
3.  **Pengecekan Konvergensi**: 
    *   Selama solver **Konvergen**: Artinya tanah masih stabil meskipun kekuatannya sudah direduksi. Langkah dilanjutkan ke $\Sigma M_{sf}$ yang lebih tinggi.
    *   Saat solver **Divergen (Runtuh)**: Artinya tanah sudah tidak sanggup lagi menahan beban dengan kekuatan yang tersisa.
4.  **Penentuan SF**: Nilai $\Sigma M_{sf}$ terakhir yang masih konvergen dicatat sebagai **Faktor Keamanan (Safety Factor)**.

### 3.4 Implementasi Kode (`phase_solver.py`)
Cuplikan logika reduksi di dalam kernel Numba:
```python
# Baris 153-156
if is_srm:
    c_eff /= target_m_stage # target_m_stage adalah MSF
    if phi_eff > 0:
        phi_rad = np.deg2rad(phi_eff)
        # Reduksi tan(phi) lalu kembalikan ke derajat
        phi_eff = np.rad2deg(np.arctan(np.tan(phi_rad) / target_m_stage))
```
Jika Anda melihat grafik di frontend yang berhenti di angka 1.45, itu berarti tanah Anda memiliki **Safety Factor 1.45**.
