# 07. Struktur Output (NPY Files)

Dokumen ini menjelaskan format data yang dikembalikan oleh solver ke frontend setelah analisis selesai.

File terkait: `backend/models.py` (Definisi Schema), `backend/solver/phase_solver.py` (Pengumpulan hasil).

## 1. Objek `SolverResponse`

Hasil analisis dikemas dalam JSON dengan struktur berikut:

```json
{
  "phases": [
    {
      "phase_id": "string",
      "success": true,
      "displacements": [...],
      "stresses": [...],
      "reached_m_stage": 1.0,
      "step_points": [...]
    }
  ],
  "log": ["..."]
}
```

## 2. Detail Hasil per Fase (`PhaseResult`)

Setiap fase memiliki hasil independen yang menggambarkan keadaan akhir fase tersebut.

### a. Displacement (Perpindahan)
List of `NodeResult`. Setiap item merepresentasikan perpindahan satu node.

```python
# backend/models.py
class NodeResult(BaseModel):
    id: int          # ID Node
    ux: float        # Perpindahan arah X (meter)
    uy: float        # Perpindahan arah Y (meter)
```

Di `phase_solver.py` (Baris 1103-1105):
```python
p_displacements = []
for i in range(num_nodes):
    p_displacements.append(NodeResult(
        id=i+1, 
        ux=final_u_total[i*2], 
        uy=final_u_total[i*2+1]
    ))
```

### b. Stresses (Tegangan)
List of `StressResult`. Tegangan dihitung di setiap **Gauss Point** (3 per elemen).

```python
# backend/models.py
class StressResult(BaseModel):
    element_id: int
    gp_id: int       # 1, 2, atau 3
    sig_xx: float    # Tegangan normal arah X (kPa)
    sig_yy: float    # Tegangan normal arah Y (kPa)
    sig_zz: float    # Tegangan normal arah Z (Out of plane)
    sig_xy: float    # Tegangan geser
    pwp_excess: float # Tekanan air pori berlebih
    pwp_total: float  # Tekanan air pori total
    is_yielded: bool  # Status plastis (True jika f > 0)
```

Proses kalkulasi Output (Baris 1134-1143 `phase_solver.py`):
```python
p_stresses.append(StressResult(
    element_id=eid, 
    gp_id=gp_idx+1,
    sig_xx=sig[0], sig_yy=sig[1], sig_xy=sig[2],
    sig_zz=sig_zz_val,
    pwp_steady=pwp_static,
    pwp_excess=pwp_excess,
    pwp_total=pwp_total,
    is_yielded=yld, 
    m_stage=current_m_stage
))
```

### c. Kurva Langkah (`step_points`)
Digunakan untuk memplot kurva Load vs Displacement di frontend.
Setiap langkah (step) dalam loop Newton-Raphson dicatat.

```python
# Contoh data step_points
[
  {"m_stage": 0.1, "max_disp": 0.001},
  {"m_stage": 0.2, "max_disp": 0.0025},
  ...
  {"m_stage": 1.0, "max_disp": 0.015}
]
```

## 3. Penanganan Kegagalan (Failure Handling)

Jika fase gagal (misal soil collapse), `success` akan bernilai `false`.
*   `reached_m_stage`: Menunjukkan beban maksimum yang bisa ditahan sebelum runtuh (misal 0.65 artinya runtuh saat 65% beban terpasang).
*   `error`: Pesan error yang menjelaskan penyebab kegagalan.

Frontend menggunakan informasi ini untuk menampilkan peringatan "Calculation Failed" atau menunjukkan Safety Factor yang didapat.
