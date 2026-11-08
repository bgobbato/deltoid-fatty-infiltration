"""Automatic bone mask used as a NEGATIVE mask (never counted as deltoid).

Why: a cortical threshold (> 200 HU) alone leaves the marrow inside the humeral head.
Marrow can be 0-150 HU (looks like muscle) or negative (fatty marrow looks like
intramuscular fat). If the drawn ROI crosses the cortex, those pixels would bias HU
and fat %. Filling the cortical ring removes the whole bone, marrow included.

Method (per slice, in the slice plane, no machine learning):
  1. cortex = HU > threshold (default 200)
  2. morphological closing (bridges thin / porous osteoporotic cortex)
  3. fill holes  -> cortex + marrow
  4. drop tiny specks (calcifications, noise)
  5. dilate by `margin_px` (partial-volume rim next to the cortex)

It includes every bone in the slice (humerus, glenoid, acromion, coracoid, clavicle):
for a negative mask that is what we want.
Limit: a humeral head whose cortex is broken over a wide gap (fracture, large cyst)
may not fill. The QC image shows the bone mask; check it.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

BONE_HU = 200.0


def _disk(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def bone_mask_2d(ct2d: np.ndarray, px_mm: float, threshold: float = BONE_HU,
                 close_mm: float = 6.0, join_mm: float = 2.0, min_area_mm2: float = 4.0,
                 margin_px: int = 1) -> np.ndarray:
    """close_mm: radius of the closing that seals gaps in the cortex (gaps up to ~2x this
    are bridged, e.g. thin osteoporotic cortex at the greater tuberosity).

    The closing is applied to EACH bone separately (connected components of the cortex),
    so two different bones (head and glenoid, head and coracoid) are never bridged and the
    soft tissue between them is not removed. Concavities of one bone (bicipital groove)
    are filled; fine for a negative mask, the deltoid is never there."""
    cortex = ct2d > threshold
    if not cortex.any():
        return cortex
    st = ndimage.generate_binary_structure(2, 1)
    r = max(1, int(round(close_mm / px_mm)))
    disk = _disk(r)
    # group cortical fragments of the same bone (porous cortex breaks into pieces):
    # pieces closer than ~2*join_mm belong to one bone
    rj = max(1, int(round(join_mm / px_mm)))
    groups, n = ndimage.label(ndimage.binary_dilation(cortex, structure=_disk(rj)), structure=np.ones((3, 3)))
    lab = np.where(cortex, groups, 0)
    filled = np.zeros_like(cortex)
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        comp = lab[sl] == i
        if comp.sum() * px_mm * px_mm < min_area_mm2:
            continue
        p = r + 2  # pad: the closing must not touch the crop border
        cp = np.pad(comp, p)
        closed = ndimage.binary_closing(cp, structure=disk)
        f = ndimage.binary_fill_holes(closed | cp)[p:-p, p:-p]
        filled[sl] |= f
    if margin_px > 0:
        filled = ndimage.binary_dilation(filled, structure=st, iterations=margin_px)
    return filled


def _fill_along(mask: np.ndarray, axis: int) -> np.ndarray:
    out = mask.copy()
    for k in range(mask.shape[axis]):
        sl = [slice(None)] * 3
        sl[axis] = k
        out[tuple(sl)] = ndimage.binary_fill_holes(mask[tuple(sl)])
    return out


def bone_mask(ct: np.ndarray, slice_axis: int, px_mm: float, slices=None, slice_mm: float | None = None,
              slab_mm: float = 25.0, three_planes: bool = True, margin_px: int = 1, **kw) -> np.ndarray:
    """Bone mask for the whole volume, or for `slices` (indices along slice_axis).

    Step 1: per axial slice, bone_mask_2d (cortex closed per bone, holes filled).
    Step 2 (three_planes): holes are ALSO filled in the two orthogonal planes. A cortical
    gap open in the axial plane (wide, porous greater tuberosity) is usually closed in the
    coronal or sagittal plane. Needs a slab of neighbouring slices (slab_mm each side).
    The margin (dilation) is applied at the end.
    """
    n = ct.shape[slice_axis]
    want = np.arange(n) if slices is None else np.asarray(sorted(set(int(s) for s in slices)))
    if len(want) == 0:
        return np.zeros(ct.shape, dtype=bool)
    half = int(round(slab_mm / slice_mm)) if (three_planes and slice_mm) else (0 if slices is not None else 0)
    lo, hi = max(0, want.min() - half), min(n, want.max() + half + 1)
    sub = np.moveaxis(ct, slice_axis, 2)[:, :, lo:hi]
    a = np.zeros(sub.shape, dtype=bool)
    for j in range(sub.shape[2]):
        a[:, :, j] = bone_mask_2d(sub[:, :, j], px_mm, margin_px=0, **kw)
    if three_planes and sub.shape[2] > 2:
        a = a | _fill_along(a, 0) | _fill_along(a, 1)
        a = _fill_along(a, 2)  # holes closed by the other planes, filled back axially
    if margin_px > 0:
        st = ndimage.generate_binary_structure(2, 1)
        for j in range(a.shape[2]):
            a[:, :, j] = ndimage.binary_dilation(a[:, :, j], structure=st, iterations=margin_px)
    out = np.zeros(np.moveaxis(ct, slice_axis, 2).shape, dtype=bool)
    out[:, :, lo:hi] = a
    if slices is not None:  # only the requested slices are returned
        keep = np.zeros(n, dtype=bool)
        keep[want] = True
        out[:, :, ~keep] = False
    return np.moveaxis(out, 2, slice_axis)
