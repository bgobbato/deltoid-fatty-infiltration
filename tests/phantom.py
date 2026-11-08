"""Synthetic CT phantoms to test the DFDI engine (no patient data).

Expected values are computed from the phantom's own construction (pixel counts of
each type), independently of the code in src/dfdi.
"""

from __future__ import annotations

import math
from pathlib import Path

import nibabel as nib
import numpy as np

HU_MUSCLE = 50.0
HU_FAT = -80.0      # inside the IMAT range (-190..-30)
HU_LOW = 10.0       # inside the LAMA range (-29..29)
HU_BONE = 800.0     # > 200 HU: must be excluded by the cleaning
HU_SUBCUT = -100.0
HU_AIR = -1000.0


def make_axial_phantom(out_dir, shape=(200, 200, 40), spacing=(0.75, 0.75, 1.25), r_in=25.0, r_out=45.0,
                       fat_frac=0.10, low_frac=0.05, n_bone=3, z_range=(5, 35), seed=0,
                       noise_sd=0.0, split_labels=False, single_slice=None, name="phantom"):
    """Ring of 'deltoid' (HU 50) around a 'humerus' (bone), with subcutaneous fat.

    In each slice of the ring: exactly round(fat_frac*n) pixels become fat (-80 HU),
    round(low_frac*n) become low-attenuation muscle (10 HU) and `n_bone` pixels become
    bone (800 HU, simulating a contour error that touches the bone).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    nx, ny, nz = shape
    sx, sy, sz = spacing
    cx, cy = (nx - 1) / 2, (ny - 1) / 2
    X, Y = np.meshgrid((np.arange(nx) - cx) * sx, (np.arange(ny) - cy) * sy, indexing="ij")
    R = np.hypot(X, Y)
    ring2d = (R >= r_in) & (R <= r_out)

    ct = np.full(shape, HU_AIR, np.float32)
    mask = np.zeros(shape, np.uint8)
    expected = {}
    for z in range(nz):
        sl = np.full((nx, ny), HU_AIR, np.float32)
        sl[R <= 60] = HU_SUBCUT
        sl[(R > 22) & (R < r_in)] = 20.0          # cuff/bursa (outside the mask)
        sl[R <= 22] = 700.0                       # cortical
        sl[R <= 18] = -50.0                       # medullary
        in_mask = z_range[0] <= z < z_range[1] and (single_slice is None or z == single_slice)
        if z_range[0] <= z < z_range[1]:
            sl[ring2d] = HU_MUSCLE
            idx = np.flatnonzero(ring2d.ravel())
            n = len(idx)
            n_fat, n_low = round(fat_frac * n), round(low_frac * n)
            perm = rng.permutation(idx)
            fat_i, low_i, bone_i = perm[:n_fat], perm[n_fat:n_fat + n_low], perm[n_fat + n_low:n_fat + n_low + n_bone]
            flat = sl.ravel()
            flat[fat_i] = HU_FAT
            flat[low_i] = HU_LOW
            flat[bone_i] = HU_BONE
            sl = flat.reshape(nx, ny)
            n_mus = n - n_fat - n_low - n_bone
            n_clean = n - n_bone
            expected[z] = {
                "n_ring": n,
                "n_clean": n_clean,
                "csa_mm2": n_clean * sx * sy,
                "csa_mm2_raw": n * sx * sy,
                "csa_analytic_mm2": math.pi * (r_out ** 2 - r_in ** 2),
                "hu_mean": (n_mus * HU_MUSCLE + n_fat * HU_FAT + n_low * HU_LOW) / n_clean,
                "hu_mean_raw": (n_mus * HU_MUSCLE + n_fat * HU_FAT + n_low * HU_LOW + n_bone * HU_BONE) / n,
                "pct_fat": 100 * n_fat / n_clean,
                "pct_lama": 100 * n_low / n_clean,
                "pct_nama": 100 * n_mus / n_clean,
                "lean_muscle_area_mm2": (n_mus + n_low) * sx * sy,
                "n_bone": n_bone,
            }
            if in_mask:
                if split_labels:   # 1=anterior, 2=middle, 3=posterior (by angle)
                    ang = np.degrees(np.arctan2(Y, X)) % 360
                    lab = np.where(ang < 120, 1, np.where(ang < 240, 2, 3)).astype(np.uint8)
                    mask[:, :, z][ring2d] = lab[ring2d]
                else:
                    mask[:, :, z][ring2d] = 1
        ct[:, :, z] = sl
    if noise_sd:
        ct += rng.normal(0, noise_sd, ct.shape).astype(np.float32)
    aff = np.diag([sx, sy, sz, 1.0])
    ctp, mkp = out_dir / f"{name}_ct.nii.gz", out_dir / f"{name}_deltoid.nii.gz"
    nib.save(nib.Nifti1Image(np.rint(ct).astype(np.int16), aff), str(ctp))
    nib.save(nib.Nifti1Image(mask, aff), str(mkp))
    return ctp, mkp, expected


def make_tilted_phantom(out_dir, theta_deg=20.0, shape=(200, 200, 140), spacing=(0.8, 0.8, 1.25),
                        r_shaft=12.0, r_head=22.0, t_head=35.0, d_in=26.0, d_out=42.0, name="tilted"):
    """Humerus (cylindrical shaft + spherical head) tilted `theta_deg` in the XZ plane,
    with a 'deltoid' tube (HU 50) coaxial with the shaft.

    True CSA (perpendicular to the axis) = pi*(d_out^2 - d_in^2).
    On the original axial the section is an ellipse: CSA_axial = CSA_true / cos(theta).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    nx, ny, nz = shape
    sp = np.array(spacing)
    c = (np.array(shape) - 1) / 2 * sp
    th = math.radians(theta_deg)
    u = np.array([math.sin(th), 0.0, math.cos(th)])
    I, J, K = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    P = np.stack([I * sp[0], J * sp[1], K * sp[2]], -1) - c
    t = P @ u
    d = np.linalg.norm(P - t[..., None] * u, axis=-1)
    hum = ((d <= r_shaft) & (t <= t_head)) | (np.linalg.norm(P - t_head * u, axis=-1) <= r_head)
    delt = (d >= d_in) & (d <= d_out) & (t >= -40) & (t <= 60)
    ct = np.full(shape, HU_AIR, np.float32)
    ct[d <= 55] = HU_SUBCUT
    ct[delt] = HU_MUSCLE
    ct[hum] = 400.0
    aff = np.diag([*sp, 1.0])
    paths = {}
    for nm, arr, dt in [("ct", ct, np.int16), ("deltoid", delt, np.uint8), ("humerus", hum, np.uint8)]:
        p = out_dir / f"{name}_{nm}.nii.gz"
        nib.save(nib.Nifti1Image(arr.astype(dt), aff), str(p))
        paths[nm] = p
    true_csa = math.pi * (d_out ** 2 - d_in ** 2)
    # axial slice at the center (t=0): center k
    expected = {
        "theta": theta_deg,
        "csa_true_mm2": true_csa,
        "csa_axial_expected_mm2": true_csa / math.cos(th),
        "k_center": int(round(c[2] / sp[2])),
        # slice heuristic (fraction 0.70): r(t) >= sqrt(0.7)*R  ->  t <= t_head + R*sqrt(0.3)
        "apex_dist_expected_mm": r_head - r_head * math.sqrt(0.3),
    }
    return paths, expected


if __name__ == "__main__":
    # Generate phantoms in output/phantom/ to try the CLI (see README.md)
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/phantom")
    ct, mk, exp = make_axial_phantom(out, name="ring")
    print(f"ring: {ct}  {mk}  -> slice 20: CSA={exp[20]['csa_mm2']:.2f} mm2, HU={exp[20]['hu_mean']:.4f}")
    paths, e2 = make_tilted_phantom(out, name="tilted")
    print(f"tilted 20 degrees: {paths['ct']}  true CSA={e2['csa_true_mm2']:.1f} mm2")
