"""
9-node quadrilateral element (Gmsh Quad9 order) with 3×3 Gauss–Legendre integration.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from engine.models import DrainageType, Material, MaterialModel

NUM_NODES = 9
NUM_DOFS = 18
NUM_GAUSS_POINTS = 9

_SQRT35 = float(np.sqrt(3.0 / 5.0))
GAUSS_POINTS_1D = np.array([-_SQRT35, 0.0, _SQRT35])
GAUSS_WEIGHTS_1D = np.array([5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0])

GAUSS_POINTS_2D: list[tuple[float, float]] = [
    (float(xi), float(eta))
    for xi in GAUSS_POINTS_1D
    for eta in GAUSS_POINTS_1D
]
GAUSS_WEIGHTS_2D = np.array(
    [float(wi * wj) for wi in GAUSS_WEIGHTS_1D for wj in GAUSS_WEIGHTS_1D]
)


def shape_functions_quad9(xi: float, eta: float) -> np.ndarray:
    lx = [0.5 * xi * (xi - 1.0), 1.0 - xi * xi, 0.5 * xi * (xi + 1.0)]
    ly = [0.5 * eta * (eta - 1.0), 1.0 - eta * eta, 0.5 * eta * (eta + 1.0)]
    return np.array(
        [
            lx[0] * ly[0],
            lx[2] * ly[0],
            lx[2] * ly[2],
            lx[0] * ly[2],
            lx[1] * ly[0],
            lx[2] * ly[1],
            lx[1] * ly[2],
            lx[0] * ly[1],
            lx[1] * ly[1],
        ],
        dtype=float,
    )


def shape_derivatives_quad9(xi: float, eta: float) -> Tuple[np.ndarray, np.ndarray]:
    dN_dxi = np.zeros(9)
    dN_deta = np.zeros(9)
    lx = [0.5 * xi * (xi - 1.0), 1.0 - xi * xi, 0.5 * xi * (xi + 1.0)]
    ly = [0.5 * eta * (eta - 1.0), 1.0 - eta * eta, 0.5 * eta * (eta + 1.0)]
    dlx = [xi - 0.5, -2.0 * xi, xi + 0.5]
    dly = [eta - 0.5, -2.0 * eta, eta + 0.5]
    dN_dxi[0] = dlx[0] * ly[0]
    dN_deta[0] = lx[0] * dly[0]
    dN_dxi[1] = dlx[2] * ly[0]
    dN_deta[1] = lx[2] * dly[0]
    dN_dxi[2] = dlx[2] * ly[2]
    dN_deta[2] = lx[2] * dly[2]
    dN_dxi[3] = dlx[0] * ly[2]
    dN_deta[3] = lx[0] * dly[2]
    dN_dxi[4] = dlx[1] * ly[0]
    dN_deta[4] = lx[1] * dly[0]
    dN_dxi[5] = dlx[2] * ly[1]
    dN_deta[5] = lx[2] * dly[1]
    dN_dxi[6] = dlx[1] * ly[2]
    dN_deta[6] = lx[1] * dly[2]
    dN_dxi[7] = dlx[0] * ly[1]
    dN_deta[7] = lx[0] * dly[1]
    dN_dxi[8] = dlx[1] * ly[1]
    dN_deta[8] = lx[1] * dly[1]
    return dN_dxi, dN_deta


def compute_b_matrix(node_coords: np.ndarray, xi: float, eta: float) -> Tuple[np.ndarray, float]:
    """B-matrix (3×18) and det(J) at (xi, eta). node_coords shape (9, 2)."""
    dN_dxi, dN_deta = shape_derivatives_quad9(xi, eta)
    j00 = j01 = j10 = j11 = 0.0
    for n in range(9):
        j00 += dN_dxi[n] * node_coords[n, 0]
        j01 += dN_dxi[n] * node_coords[n, 1]
        j10 += dN_deta[n] * node_coords[n, 0]
        j11 += dN_deta[n] * node_coords[n, 1]
    det_j = j00 * j11 - j01 * j10
    if abs(det_j) < 1e-12:
        return np.zeros((3, NUM_DOFS)), 0.0
    inv_det = 1.0 / det_j
    ji00 = j11 * inv_det
    ji01 = -j01 * inv_det
    ji10 = -j10 * inv_det
    ji11 = j00 * inv_det
    b = np.zeros((3, NUM_DOFS))
    for n in range(9):
        dndx = ji00 * dN_dxi[n] + ji01 * dN_deta[n]
        dndy = ji10 * dN_dxi[n] + ji11 * dN_deta[n]
        b[0, 2 * n] = dndx
        b[1, 2 * n + 1] = dndy
        b[2, 2 * n] = dndy
        b[2, 2 * n + 1] = dndx
    return b, det_j


def get_water_level_at(x: float, water_level_polyline: Optional[List[Dict]] = None) -> Optional[float]:
    if not water_level_polyline:
        return None
    pts = sorted(water_level_polyline, key=lambda p: p["x"])
    if x <= pts[0]["x"]:
        return pts[0]["y"]
    if x >= pts[-1]["x"]:
        return pts[-1]["y"]
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        if p1["x"] <= x <= p2["x"]:
            t = (x - p1["x"]) / (p2["x"] - p1["x"])
            return p1["y"] + t * (p2["y"] - p1["y"])
    return None


def gauss_point_physical_coords(
    nodes: list[list[float]], elem: list[int], gp_index: int
) -> tuple[float, float]:
    xi, eta = GAUSS_POINTS_2D[gp_index]
    n = shape_functions_quad9(xi, eta)
    gx = gy = 0.0
    for k in range(9):
        gx += n[k] * nodes[elem[k]][0]
        gy += n[k] * nodes[elem[k]][1]
    return gx, gy


def all_gauss_point_physical_coords(
    nodes: list[list[float]], elem: list[int]
) -> list[tuple[float, float]]:
    return [gauss_point_physical_coords(nodes, elem, i) for i in range(NUM_GAUSS_POINTS)]


def compute_element_matrices_quad9(
    node_coords: np.ndarray,
    material: Material,
    water_level: Optional[List[Dict]] = None,
    thickness: float = 1.0,
    kh: float = 0.0,
    kv: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, List[Dict], np.ndarray]:
    """Stiffness (18×18), gravity (18), Gauss point data, elastic D (3×3)."""
    if material.material_model in [MaterialModel.LINEAR_ELASTIC,MaterialModel.MOHR_COULOMB,MaterialModel.HOEK_BROWN]:
        if material.drainage_type in [DrainageType.UNDRAINED_C, DrainageType.NON_POROUS]:
            e_mod = material.youngsModulus
        else:
            e_mod = material.effyoungsModulus or 10000.0
    elif material.material_model == MaterialModel.HARDENING_SOIL: #For Hardening Soil
        e_mod = material.youngsModulus50_ref

    nu = material.poissonsRatio
    factor = e_mod / ((1 + nu) * (1 - 2 * nu))
    d_mat = (
        np.array([[1 - nu, nu, 0], [nu, 1 - nu, 0], [0, 0, (1 - 2 * nu) / 2]], dtype=float)
        * factor
    )

    k = np.zeros((NUM_DOFS, NUM_DOFS))
    f_grav = np.zeros(NUM_DOFS)
    gauss_point_data: List[Dict] = []
    gamma_w = 9.81

    for gp_idx, (xi, eta) in enumerate(GAUSS_POINTS_2D):
        weight = float(GAUSS_WEIGHTS_2D[gp_idx])
        b, det_j = compute_b_matrix(node_coords, xi, eta)
        n_vals = shape_functions_quad9(xi, eta)
        gp_coords = n_vals @ node_coords
        gx, gy = float(gp_coords[0]), float(gp_coords[1])

        water_y = get_water_level_at(gx, water_level)
        pwp = 0.0
        if material.drainage_type not in [DrainageType.NON_POROUS, DrainageType.UNDRAINED_C]:
            if water_y is not None and gy < water_y:
                pwp = -gamma_w * (water_y - gy)

        if material.drainage_type == DrainageType.NON_POROUS:
            rho_tot = material.unitWeightUnsaturated
        elif water_y is not None and gy < water_y:
            rho_tot = material.unitWeightSaturated or material.unitWeightUnsaturated
        else:
            rho_tot = material.unitWeightUnsaturated

        k += (b.T @ d_mat @ b) * det_j * weight * thickness
        for i in range(9):
            f_grav[2 * i] += n_vals[i] * kh * rho_tot * det_j * weight * thickness
            f_grav[2 * i + 1] += -n_vals[i] * (1.0 + kv) * rho_tot * det_j * weight * thickness

        gauss_point_data.append(
            {
                "gp_id": gp_idx + 1,
                "xi": xi,
                "eta": eta,
                "x": gx,
                "y": gy,
                "det_J": det_j,
                "B": b,
                "weight": weight,
                "pwp": pwp,
                "rho": rho_tot,
            }
        )

    return k, f_grav, gauss_point_data, d_mat


def quad9_corner_area(node_coords: np.ndarray) -> float:
    """Shoelace area using four corner nodes (0–3)."""
    c = node_coords[:4]
    x = c[:, 0]
    y = c[:, 1]
    return 0.5 * abs(
        x[0] * (y[1] - y[3])
        + x[1] * (y[2] - y[0])
        + x[2] * (y[3] - y[1])
        + x[3] * (y[0] - y[2])
    )
