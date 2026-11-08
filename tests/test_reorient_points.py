"""Reorientation from surgeon-picked shaft points (web app, phase 4)."""
import math

import numpy as np

from dfdi.io import load_nifti, resample_to
from dfdi.metrics import slice_metrics
from dfdi.orientation import basis_from_points, reorient_by_points
from phantom import make_tilted_phantom


def _shaft_point(exp_shape, sp, theta, t):
    c = (np.array(exp_shape) - 1) / 2 * np.array(sp)
    th = math.radians(theta)
    return c + t * np.array([math.sin(th), 0.0, math.cos(th)])


def test_points_recover_tilted_shaft_and_true_csa(tmp_path):
    shape, sp = (200, 200, 140), (0.8, 0.8, 1.25)
    paths, exp = make_tilted_phantom(tmp_path, theta_deg=20.0, shape=shape, spacing=sp)
    ct = load_nifti(paths["ct"])
    mk = load_nifti(paths["deltoid"])
    # shaft centre picked at two levels (distal t=-40 mm, proximal t=+20 mm), 1 mm click error
    p_dist = _shaft_point(shape, sp, 20.0, -40.0) + np.array([0.7, -0.5, 0.0])
    p_prox = _shaft_point(shape, sp, 20.0, 20.0) + np.array([-0.6, 0.4, 0.0])
    E, info = basis_from_points(p_prox, p_dist)
    assert abs(info["shaft_angle_vs_S_axis_deg"] - 20.0) < 1.5
    assert np.allclose(E.T @ E, np.eye(3), atol=1e-9) and np.linalg.det(E) > 0

    rct, rinfo = reorient_by_points(ct, p_prox, p_dist, half_width_mm=60, below_mm=10, above_mm=10)
    rmk = resample_to(mk, rct, order=0)
    # slice through the shaft centre (t = 0) in the new grid
    centre = _shaft_point(shape, sp, 20.0, 0.0)
    k = int(round(np.linalg.solve(rct.affine[:3, :3], centre - rct.affine[:3, 3])[2]))
    px = float(np.prod(rinfo["reoriented_spacing_mm"][:2]))
    m = slice_metrics(rct.data[:, :, k], rmk.data[:, :, k] > 0, px)
    # 1 mm click error tilts the axis ~1 degree: area error ~0.02%; pixelation ~1%
    assert abs(m["csa_mm2"] - exp["csa_true_mm2"]) / exp["csa_true_mm2"] < 0.02
    # a mask resampled together with the CT mixes edge HU (partial volume): the web app avoids
    # this because the surgeon draws on the reoriented image. The ROI core is unbiased.
    assert abs(m["hu_mean_eroded_core_1px"] - 50.0) < 0.5
    # native axial is inflated by 1/cos(20) = +6.4 %
    assert exp["csa_axial_expected_mm2"] / exp["csa_true_mm2"] > 1.06


def test_glenoid_points_set_the_coronal_plane():
    E, info = basis_from_points([0, 0, 100], [0, 0, 0], g_ant=[10, 30, 50], g_post=[10, -30, 50])
    assert info["scapular_plane_from_glenoid"]
    assert np.allclose(E[:, 1], [0, 1, 0]) and np.allclose(E[:, 2], [0, 0, 1]) and np.allclose(E[:, 0], [1, 0, 0])
