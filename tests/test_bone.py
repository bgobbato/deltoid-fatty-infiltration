"""Bone negative mask: marrow that looks like muscle (or fat) must leave the ROI."""
import numpy as np
import nibabel as nib

from dfdi.bone import bone_mask_2d
from dfdi.measure import measure_case

PX = 0.5


def _head(n=200, cx=100, cy=100, r_out=40, cortex=3, marrow_hu=50.0, gap_deg=0):
    y, x = np.mgrid[0:n, 0:n]
    d = np.hypot(x - cx, y - cy)
    ang = np.degrees(np.arctan2(y - cy, x - cx)) % 360
    ct = np.full((n, n), -100.0)                     # fat background
    ring = (d <= r_out) & (d > r_out - cortex)
    if gap_deg:
        ring &= ~(ang < gap_deg)                     # porous / broken cortex
    ct[d <= r_out - cortex] = marrow_hu
    ct[ring] = 800.0
    muscle = (d > r_out) & (d <= r_out + 20)
    ct[muscle] = 40.0
    return ct, d, muscle


def test_marrow_is_filled_even_with_small_cortex_gap():
    ct, d, _ = _head(gap_deg=5)                       # ~3.5 mm gap at r=40 px
    b = bone_mask_2d(ct, PX, margin_px=0)
    assert b[d <= 30].all(), "marrow must be inside the bone mask"
    assert not b[d > 45].any(), "bone mask must not grow into the muscle"


def test_bone_exclusion_removes_marrow_from_roi(tmp_path):
    ct2, d, muscle = _head(marrow_hu=50.0)
    roi = muscle | (d <= 30)                          # drawing crosses into the head
    ct = np.repeat(ct2[:, :, None], 3, axis=2).astype(np.int16)
    m = np.zeros(ct.shape, np.uint8)
    m[:, :, 1] = roi
    aff = np.diag([PX, PX, 1.25, 1.0])
    nib.save(nib.Nifti1Image(ct, aff), str(tmp_path / "ct.nii.gz"))
    nib.save(nib.Nifti1Image(m, aff), str(tmp_path / "m.nii.gz"))

    off = measure_case(tmp_path / "ct.nii.gz", tmp_path / "m.nii.gz", make_png=False)
    on = measure_case(tmp_path / "ct.nii.gz", tmp_path / "m.nii.gz", make_png=False,
                      bone_exclusion=True, bone_margin_px=1)
    true_csa = muscle.sum() * PX * PX
    # without the bone mask the marrow (50 HU) is counted as deltoid
    marrow_csa = (d <= 30).sum() * PX * PX
    assert off["csa_mm2"] > true_csa + 0.95 * marrow_csa
    # with it: only the muscle ring remains (minus the 1-px rim next to the cortex)
    assert abs(on["hu_mean"] - 40.0) < 1e-6
    assert true_csa * 0.9 < on["csa_mm2"] <= true_csa
    assert on["bone_exclusion"] is True and on["n_excluded_bone_mask_3d"] > 0


def test_wide_axial_gap_is_closed_by_the_other_planes():
    """A 40-degree cortical gap on a few axial slices (porous greater tuberosity) is too
    wide for the 2D closing; the coronal/sagittal fill must still remove the marrow.
    Known limit: a 70-degree gap leaves ~12% of the marrow unfilled next to the gap."""
    from dfdi.bone import bone_mask
    n, nz, c, R = 120, 60, 60, 25                     # 0.5 mm pixels, 1 mm slices
    z, y, x = np.mgrid[0:nz, 0:n, 0:n]
    dz = (z - nz // 2) * 2.0                          # slice 1 mm = 2 px
    d = np.sqrt((x - c) ** 2 + (y - c) ** 2 + dz ** 2)
    ang = np.degrees(np.arctan2(y - c, x - c)) % 360
    ct = np.full(d.shape, 40.0)                       # muscle around
    ct[d <= R - 3] = 50.0                             # marrow, muscle-like HU
    shell = (d <= R) & (d > R - 3)
    gap = (np.abs(z - nz // 2) <= 3) & (ang < 40)
    ct[shell & ~gap] = 800.0
    ct = np.moveaxis(ct, 0, 2)                        # (x, y, z), slice axis 2
    mid = nz // 2
    b2 = bone_mask(ct, 2, 0.5, slices=[mid], slice_mm=1.0, three_planes=False, margin_px=0)
    b3 = bone_mask(ct, 2, 0.5, slices=[mid], slice_mm=1.0, three_planes=True, margin_px=0)
    yy, xx = np.mgrid[0:n, 0:n]
    marrow = np.hypot(xx - c, yy - c).T <= R - 6
    assert b2[:, :, mid][marrow].mean() < 0.5         # 2D alone fails (documents the limit)
    assert b3[:, :, mid][marrow].mean() > 0.99        # 3 planes fill it (measured 0.999)
    out = np.hypot(xx - c, yy - c).T > R + 3
    assert not b3[:, :, mid][out].any()               # no leak into the muscle
