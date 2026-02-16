# 01. UI/UX Frontend TerraSim

Dokumen ini menjelaskan antarmuka pengguna (UI) dan pengalaman pengguna (UX) dalam menggunakan TerraSim, termasuk fitur-fitur utama dan alur kerja aplikasi.

## 1. Filosofi Desain
TerraSim dirancang untuk memberikan pengalaman simulasi geoteknik yang intuitif, modern, dan efisien. Aplikasi ini menggunakan antarmuka berbasis web dengan pembagian tugas yang jelas melalui tab navigasi.

## 2. Struktur Aplikasi
Aplikasi dibagi menjadi 5 tab utama yang mencerminkan alur kerja simulasi:
*   **Input**: Definisi geometri, beban, muka air, dan material.
*   **Mesh**: Diskretisasi geometri menjadi elemen hingga.
*   **Staging**: Pengaturan tahapan konstruksi (Phase).
*   **Results**: Eksekusi analisis dan visualisasi hasil.
*   **Project**: Manajemen file dan pengaturan global.

## 3. Detail Fitur Per Tab

### 3.1 Tab Input (Geometry & Load)
Tab ini adalah tempat utama untuk membangun model fisik.
*   **Geometry**: Pengguna dapat menggambar poligon atau persegi panjang secara langsung di canvas atau mengimpor dari file DXF.
*   **Load**: Penambahan beban titik (Point Load) dan beban garis/terbagi rata (Line Load).
*   **Water Table**: Definisi garis freatik menggunakan polylines.
*   **Material Properties**: Pendefinisian parameter tanah (E, v, c, phi, dll) dengan model Mohr-Coulomb atau Linear Elastic.

### 3.2 Tab Mesh (Mesh Generation)
Mengubah geometri kontinu menjadi model diskrit.
*   **Mesh Size**: Mengatur ukuran maksimum elemen.
*   **Refinement**: Mengatur faktor perapatan mesh di sekitar batas geometri.
*   **Generation**: Proses pembuatan mesh yang dilakukan di sisi server.

### 3.3 Tab Staging (Construction Stages)
Mensimulasikan urutan konstruksi nyata.
*   **Phase Types**: K0 Procedure, Gravity Loading, Plastic Analysis, dan Safety Analysis (SRM).
*   **Component Activation**: Mengaktifkan atau menonaktifkan poligon (misal untuk galian) dan beban di setiap fase.
*   **Water Level Selection**: Memilih muka air yang aktif untuk setiap fase.

### 3.4 Tab Results (Analysis & Visualization)
Mengeksekusi perhitungan dan melihat hasil.
*   **Live Monitoring**: Grafik konvergensi dan log analisis ditampilkan secara real-time.
*   **Visualization**: Contour plot untuk displacement, stress (total/efektif), dan Pore Water Pressure (PWP).
*   **Safety Factor**: Hasil dari analisis Safety ditampilkan langsung di sidebar.

### 3.5 Tab Project (Management)
*   **File Management**: Simpan dan buka file `.tsm`.
*   **Cloud Sync**: Sinkronisasi proyek ke akun pengguna.
*   **Settings**: Pengaturan visual (Dark Mode, Grid) dan parameter solver (Tolerance, Max Iterations).

## 4. Alur Kerja Pengguna (User Experience)
Alur kerja standar dalam TerraSim adalah:
1.  **Mendefinisikan Geometri** di tab Input.
2.  **Membuat Material** dan meng-assign ke setiap bagian geometri.
3.  **Membuat Mesh** untuk mendiskretisasi model.
4.  **Menyusun Fase** konstruksi di tab Staging.
5.  **Menjalankan Analisis** dan menginterpretasikan hasil di tab Results.

---
*Lanjut ke Dokumen 02 untuk detail teknis tentang Mesh Generator.*
