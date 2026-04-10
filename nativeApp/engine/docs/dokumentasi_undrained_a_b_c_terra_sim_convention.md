# Dokumentasi Analisis Undrained A, B, C

> **Khusus untuk TerraSim**  
> Konvensi tanda: **kompresi (−)**, **tarik (+)**

Dokumen ini menjelaskan **secara matematis dan algoritmik** bagaimana Undrained A, B, dan C dihitung dalam konteks **solver FEA elasto‑plastik (Mohr–Coulomb)**, dan bagaimana konsep ini **diimplementasikan ke dalam TerraSim**, termasuk untuk *anti‑gravity / solver otomatis*.

---

## 1. Dasar Umum yang Berlaku untuk Semua Undrained

### 1.1 Relasi Tegangan

Semua analisis undrained **tetap mematuhi**:

\[ \boldsymbol{\sigma} = \boldsymbol{\sigma}' + u \mathbf{I} \]

Dengan:
- \(\boldsymbol{\sigma}\) : **total stress**
- \(\boldsymbol{\sigma}'\) : **effective stress**
- \(u\) : pore water pressure
- \(\mathbf{I}\) : identity tensor

📌 **Perbedaan Undrained A, B, C bukan pada persamaan ini, tapi pada:**
- apakah \(u\) dihitung
- stress mana yang masuk ke yield function

---

## 2. Undrained A (Effective Stress Based, Fully Coupled)

### 2.1 Input Material

| Parameter | Makna |
|--------|------|
| \(c'\) | cohesion efektif |
| \(\phi'\) | sudut geser efektif |
| \(E'\) | modulus elastis efektif |
| \(\nu'\) | poisson ratio efektif |
| k | kecil (undrained) |

Tanah diasumsikan **jenuh**, dan air **tidak sempat drain**.

---

### 2.2 Alur Perhitungan (Numerik)

#### Step 1 – Hitung trial total stress

\[ \boldsymbol{\sigma}_{trial} = \mathbf{D}_{elastic} : \boldsymbol{\varepsilon} \]

> \(\boldsymbol{\varepsilon}\) berasal dari displacement hasil Newton iteration.

---

#### Step 2 – Hitung excess pore pressure

Untuk kondisi undrained:

\[ \Delta u = K_w \; \varepsilon_v \]

Dengan:
- \(\varepsilon_v = \varepsilon_{xx} + \varepsilon_{yy}\)
- tanda **negatif penting** karena kompresi = negatif

📌 Artinya:
- kompresi tanah (εᵥ < 0) → Δu < 0
- tanah mengembang (εᵥ > 0) → Δu > 0 (suction/tension)

---

#### Step 3 – Hitung effective stress trial

\[ \boldsymbol{\sigma}'_{trial} = \boldsymbol{\sigma}_{trial} - u \mathbf{I} \]

---

### 2.3 Yield Check (Mohr–Coulomb)

Yield **SELALU di effective stress space**:

\[ f(\boldsymbol{\sigma}') = \tau - (c' + \sigma'_n \tan \phi') \]

Jika:
- \(f \le 0\) → elastic
- \(f > 0\) → plastic → return mapping

---

### 2.4 Return Mapping (Undrained A)

Return mapping dilakukan di **σ′‑space**:

1. Koreksi \(\boldsymbol{\sigma}'\) ke yield surface
2. Update plastic strain
3. Update tangent stiffness \(\mathbf{D}_{tangent}\)

Setelah valid:

\[ \boldsymbol{\sigma} = \boldsymbol{\sigma}' + u \mathbf{I} \]

---

### 2.5 Karakter Numerik

- Paling fisik
- Bisa menghasilkan excess PWP
- Mahal secara komputasi
- Digunakan PLAXIS untuk analisis lanjutan

---

## 3. Undrained B (Total Stress, Tresca‑like)

### 3.1 Input Material

| Parameter | Nilai |
|-------|------|
| Su | undrained shear strength |
| \(\phi\) | 0 |
| c | Su |
| \(E\) | total modulus |

---

### 3.2 Yield Function

Karena \(\phi = 0\):

\[ \tau_f = Su \]

atau dalam principal stress:

\[ \sigma_1 - \sigma_3 = 2 Su \]

📌 **Langsung pakai total stress**.

---

### 3.3 Alur Solver

1. Hitung \(\boldsymbol{\sigma}\)
2. Yield check di \(\boldsymbol{\sigma}\)
3. Return mapping di **total stress space**

❌ Tidak ada:
- effective stress
- pore pressure

---

## 4. Undrained C (Pure Total Stress, Constant Strength)

### 4.1 Karakter

- Sama dengan Undrained B secara matematis
- Tapi **tidak ada konsep u sama sekali**
- Strength **tidak berubah selamanya**

Digunakan untuk:
- analisis cepat
- stabilitas jangka pendek

---

## 5. Perbandingan Ringkas

| Aspek | Undrained A | Undrained B | Undrained C |
|---|---|---|---|
| Stress untuk yield | σ′ | σ | σ |
| Δu dihitung | ✔ | ❌ | ❌ |
| Plasticity space | Effective | Total | Total |
| Fisik | Tinggi | Sedang | Rendah |

---

## 6. Implementasi ke TerraSim Solver

### 6.1 Pseudocode Umum

```text
for load_step:
  for newton_iteration:
    compute strain ε

    if Undrained A:
      compute σ_trial
      compute Δu = Kw * εv
      σ'_trial = σ_trial - uI
      yield check on σ'
      return mapping σ'
      reconstruct σ

    if Undrained B or C:
      compute σ_trial
      yield check on σ
      return mapping σ

    assemble F_int
    R = F_ext - F_int
    solve Kt Δu = R
```

---

## 7. Catatan Penting untuk Anti‑Gravity / Auto Solver

- Jangan **reset u** antar Newton iteration
- Jangan clamp u = 0 di atas GWT
- Collapse dideteksi dari:
  - non‑convergence
  - displacement melonjak
  - chain of yielded integration points

---

## 8. Penutup

> **Undrained A adalah analisis total stress dengan plasticity di effective stress space.**  
> Undrained B dan C adalah penyederhanaan berbasis total stress.

Dokumen ini dapat langsung digunakan sebagai **design reference TerraSim**.

