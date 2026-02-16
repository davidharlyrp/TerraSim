# 02. Mesh Generator

Dokumen ini menjelaskan implementasi teknis dari modul pembuatan mesh (`backend/mesh_generator.py`) yang digunakan untuk mendiskretisasi geometri menjadi elemen T6 (6-node quadratic triangle).

## 1. Algoritma Utama
Mesh generator menggunakan library **Triangle** (oleh Jonathan Richard Shewchuk) sebagai engine inti untuk triangulasi Constrained Delaunay.

Proses pembuatan mesh dilakukan melalui fungsi `generate_mesh` dengan langkah-langkah berikut:

### A. Persiapan Geometri (Geometry Preparation)
1.  **Vertex Snapping**: Semua koordinat vertex ditarik ke grid (`GRID_SIZE = 1e-3`) untuk memastikan topologi yang bersih dan menghindari masalah numerik akibat *float noise*.
2.  **Boundary Cleaning**: Menggunakan library `shapely` (operasi `unary_union`) untuk membersihkan garis batas yang tumpang tindih atau berpotongan.
3.  **Discretization**: Garis batas dibagi menjadi segmen-segmen kecil berdasarkan parameter `mesh_size` dan `refinement_factor`.

### B. Pendefinisian Region (Material)
1.  **Region Identification**: Setiap poligon diidentifikasi sebagai sebuah region dengan atribut material tertentu.
2.  **Max Area Constraint**: Luas maksimum elemen dalam sebuah region ditentukan oleh $Area_{max} = 0.5 \cdot (MeshSize)^2$.
3.  **Polygon Splitting**: Jika terdapat *Embedded Beam Row* (EBR), poligon akan dipotong untuk memastikan node mesh terbentuk tepat di sepanjang jalur EBR.

### C. Triangulasi
Input yang sudah disiapkan (vertices, segments, regions) dikirim ke library `triangle` dengan opsi:
*   `p`: Planar Straight Line Graph (PSLG).
*   `q`: Quality mesh (sudut minimal ~20 derajat).
*   `a`: Menghormati batasan area per region.
*   `A`: Memberikan atribut material ke setiap elemen.

## 2. Transformasi ke Elemen T6
Library `triangle` secara default menghasilkan elemen T3 (3-node linear triangle). TerraSim melakukan transformasi manual menjadi elemen **T6 (6-node quadratic triangle)** untuk akurasi yang lebih tinggi.

Proses transformasi:
1.  Mengidentifikasi 3 titik sudut asli (n1, n2, n3).
2.  Menambahkan 3 node baru di titik tengah (midpoint) setiap sisi (n12, n23, n31).
3.  Memastikan node tengah yang dibagikan oleh dua elemen hanya dibuat satu kali (deduplikasi menggunakan map).

Struktur urutan node T6: `[n1, n2, n3, n12, n23, n31]`.

## 3. Penanganan Beban dan Fitur Khusus
Mesh generator juga memastikan bahwa node terbentuk di lokasi-lokasi penting:
*   **Point Loads**: Node dipaksa terbentuk tepat di koordinat beban titik.
*   **Line Loads**: Segmen mesh dipaksa mengikuti jalur beban garis.
*   **Embedded Beam Rows**: Node-node mesh dipaksa sejajar dengan geometri balok tertanam.

## 4. Kondisi Batas (Boundary Conditions)
Setelah mesh terbentuk, generator secara otomatis mendeteksi batas model untuk memberikan tumpuan:
*   **Bottom (y = min)**: Dibuat jepit penuh (*Full Fixed*).
*   **Sides (x = min, x = max)**: Dibuat tumpuan rol (*Normal Fixed*), hanya bisa bergerak ke arah vertikal.

---
*Lanjut ke Dokumen 03 untuk proses inisialisasi tegangan pada mesh yang telah dibuat.*
