import numpy as np

def compute_beam_forces_local(node_coords, u_el, E, A, I, spacing):
    x1, y1 = node_coords[0, 0], node_coords[0, 1]
    x2, y2 = node_coords[1, 0], node_coords[1, 1]
    dx, dy = x2 - x1, y2 - y1
    L = np.sqrt(dx*dx + dy*dy)
    c, s = dx/L, dy/L
    
    T = np.zeros((6, 6))
    T[0,0]=c; T[0,1]=s
    T[1,0]=-s; T[1,1]=c
    T[2,2]=1.0
    T[3,3]=c; T[3,4]=s
    T[4,3]=-s; T[4,4]=c
    T[5,5]=1.0
    
    u_local = T @ u_el
    inv_spacing = 1.0/spacing
    k_axial = (E*A/L)*inv_spacing
    k_bend = (E*I/(L**3))*inv_spacing
    
    k_local = np.zeros((6, 6))
    k_local[0,0]=k_axial; k_local[0,3]=-k_axial
    k_local[3,0]=-k_axial; k_local[3,3]=k_axial
    k_local[1,1]=12*k_bend; k_local[1,2]=6*k_bend*L; k_local[1,4]=-12*k_bend; k_local[1,5]=6*k_bend*L
    k_local[2,1]=6*k_bend*L; k_local[2,2]=4*k_bend*L*L; k_local[2,4]=-6*k_bend*L; k_local[2,5]=2*k_bend*L*L
    k_local[4,1]=-12*k_bend; k_local[4,2]=-6*k_bend*L; k_local[4,4]=12*k_bend; k_local[4,5]=-6*k_bend*L
    k_local[5,1]=6*k_bend*L; k_local[5,2]=2*k_bend*L*L; k_local[5,4]=-6*k_bend*L; k_local[5,5]=4*k_bend*L*L
    
    f_local = k_local @ u_local
    
    # Current Mapping
    m1 = -f_local[2]
    m2 = f_local[5]
    return m1, m2, f_local

# --- TEST ---
E, A, I, spacing = 2e5, 0.1, 1e-6, 1.0

# Case: Slanted beam (45 deg)
# Seg 1: (0,0) -> (1,1)
# Seg 2: (1,1) -> (2,2)
coords1 = np.array([[0,0], [1,1]])
coords2 = np.array([[1,1], [2,2]])

# Apply a rotation of 0.001 at the shared node (1,1)
# u_el = [ux1, uy1, rot1, ux2, uy2, rot2]
u1 = np.array([0, 0, 0, 0, 0, 0.001])
u2 = np.array([0, 0, 0.001, 0, 0, 0])

m1_A, m2_A, f_A = compute_beam_forces_local(coords1, u1, E, A, I, spacing)
m1_B, m2_B, f_B = compute_beam_forces_local(coords2, u2, E, A, I, spacing)

print(f"Segment A: M1={m1_A:.4f}, M2={m2_A:.4f}")
print(f"Segment B: M1={m1_B:.4f}, M2={m2_B:.4f}")
print(f"Node Continuity: dM = {abs(m2_A - m1_B):.4f}")

# Equilibrium Check
print(f"Equilibrium: f_A[5] + f_B[2] = {f_A[5] + f_B[2]:.4f}")
