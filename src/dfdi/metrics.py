"""Area/attenuation metrics on the reference slice and in 3D.

HU conventions (half-integer edges so that integer values fall exactly within the
ranges used in the myosteatosis literature):
  intramuscular fat (IMAT)                  -190 to -30 HU
  low-attenuation muscle (LAMA)              -29 to  29 HU
  normal-attenuation muscle (NAMA)            30 to 150 HU
  total muscle (lean SMA)                    -29 to 150 HU
Excluded as non-soft-tissue ("cleaning"):
  > 200 HU (cortical bone, fragment, metal, calcification) and < -200 HU (air).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

FAT = (-190.5, -29.5)
LOW_ATT = (-29.5, 29.5)
NORMAL_ATT = (29.5, 150.5)
MUSCLE = (-29.5, 150.5)
EXCL_HIGH = 200.0
EXCL_LOW = -200.0

# Plausibility limits for QC flags (not clinical criteria).
QC = {
    "min_pixels": 200,
    "csa_min_mm2": 1000.0,
    "csa_max_mm2": 8000.0,
    "hu_min": 0.0,
    "hu_max": 80.0,
    "max_pct_excluded": 2.0,
    "max_pct_bone_border": 5.0,
}


def _in(v, rng):
    return (v >= rng[0]) & (v < rng[1])


def region_stats(values: np.ndarray, unit_size: float, unit: str = "mm2") -> dict:
    """Statistics of a set of (already cleaned) HU values.

    unit_size = pixel area (mm2) or voxel volume (mm3).
    """
    n = int(values.size)
    out = {"n": n}
    if n == 0:
        for k in ["area", "hu_mean", "hu_median", "hu_sd", "hu_p05", "hu_p95",
                  "pct_fat", "pct_low_attenuation", "pct_normal_attenuation",
                  "lean_muscle_area", "hu_mean_lean_muscle", "normal_attenuation_area"]:
            out[k] = float("nan")
        return out
    v = values.astype(np.float64)
    fat = _in(v, FAT)
    low = _in(v, LOW_ATT)
    nor = _in(v, NORMAL_ATT)
    mus = _in(v, MUSCLE)
    out.update({
        "area": n * unit_size,
        "hu_mean": float(v.mean()),
        "hu_median": float(np.median(v)),
        "hu_sd": float(v.std(ddof=1)) if n > 1 else 0.0,
        "hu_p05": float(np.percentile(v, 5)),
        "hu_p95": float(np.percentile(v, 95)),
        "pct_fat": 100.0 * fat.sum() / n,
        "pct_low_attenuation": 100.0 * low.sum() / n,
        "pct_normal_attenuation": 100.0 * nor.sum() / n,
        "lean_muscle_area": float(mus.sum() * unit_size),
        "normal_attenuation_area": float(nor.sum() * unit_size),
        "hu_mean_lean_muscle": float(v[mus].mean()) if mus.any() else float("nan"),
    })
    return out


def clean_mask(ct: np.ndarray, mask: np.ndarray, excl: np.ndarray | None = None):
    """Remove from the mask pixels outside [-200, 200] HU and exclusion-label pixels.

    Intramuscular fat (-190 to -30) is KEPT: it is the signal we want to measure.
    Hematoma and fluid are NOT separable by HU (they overlap muscle); they only leave
    if the surgeon paints an exclusion label.
    """
    keep = mask & (ct >= EXCL_LOW) & (ct <= EXCL_HIGH)
    if excl is not None:
        keep &= ~excl
    return keep


def slice_metrics(ct2d: np.ndarray, mask2d: np.ndarray, px_area: float,
                  excl2d: np.ndarray | None = None) -> dict:
    """Reference-slice metrics (article replication + extras + flags)."""
    raw = mask2d.astype(bool)
    keep = clean_mask(ct2d, raw, excl2d)
    s = region_stats(ct2d[keep], px_area)
    n_raw = int(raw.sum())
    n_bone = int((raw & (ct2d > EXCL_HIGH)).sum())
    n_air = int((raw & (ct2d < EXCL_LOW)).sum())
    n_excl_label = int((raw & excl2d).sum()) if excl2d is not None else 0

    out = {
        # --- article replication ---
        "csa_mm2": s["area"],
        "hu_mean": s["hu_mean"],
        # --- raw ROI values, no cleaning (what a DICOM viewer would give) ---
        "csa_mm2_raw": n_raw * px_area,
        "hu_mean_raw": float(ct2d[raw].astype(np.float64).mean()) if n_raw else float("nan"),
        # --- extras ---
        "hu_median": s["hu_median"],
        "hu_sd": s["hu_sd"],
        "hu_p05": s["hu_p05"],
        "hu_p95": s["hu_p95"],
        "pct_fat_imat": s["pct_fat"],
        "pct_low_attenuation_lama": s["pct_low_attenuation"],
        "pct_normal_attenuation_nama": s["pct_normal_attenuation"],
        "lean_muscle_area_mm2": s["lean_muscle_area"],
        "normal_attenuation_area_mm2": s["normal_attenuation_area"],
        "hu_mean_lean_muscle": s["hu_mean_lean_muscle"],
        "n_pixels": s["n"],
        "n_pixels_raw": n_raw,
        "n_excluded_bone_200hu": n_bone,
        "n_excluded_air": n_air,
        "n_excluded_label": n_excl_label,
        "pixel_area_mm2": px_area,
    }
    # ROI core eroded by 1 px: estimates the partial-volume bias at the edges
    # (important when the mask was resampled/reoriented)
    core = ndimage.binary_erosion(keep)
    out["hu_mean_eroded_core_1px"] = float(ct2d[core].astype(np.float64).mean()) if core.any() else float("nan")
    out["n_pixels_eroded_core_1px"] = int(core.sum())
    out.update(slice_shape_flags(ct2d, raw, out))
    return out


def slice_shape_flags(ct2d, raw, m) -> dict:
    flags = []
    if m["n_pixels"] < QC["min_pixels"]:
        flags.append("few_pixels")
    if not np.isnan(m["csa_mm2"]) and not (QC["csa_min_mm2"] <= m["csa_mm2"] <= QC["csa_max_mm2"]):
        flags.append("csa_outside_plausible_range")
    if not np.isnan(m["hu_mean"]) and not (QC["hu_min"] <= m["hu_mean"] <= QC["hu_max"]):
        flags.append("hu_outside_plausible_range")
    pct_excl = 100.0 * (m["n_excluded_bone_200hu"] + m["n_excluded_air"]) / max(m["n_pixels_raw"], 1)
    if pct_excl > QC["max_pct_excluded"]:
        flags.append("many_pixels_excluded_bone_or_air")

    # mask touching bone (>200 HU) just outside it
    ring = ndimage.binary_dilation(raw) & ~raw
    n_ring = int(ring.sum())
    n_ring_bone = int((ring & (ct2d > EXCL_HIGH)).sum())
    pct_ring_bone = 100.0 * n_ring_bone / max(n_ring, 1)
    if pct_ring_bone > QC["max_pct_bone_border"]:
        flags.append("mask_touches_bone")

    # touches the image border (deltoid cut off by the FOV?)
    if raw.any() and (raw[0, :].any() or raw[-1, :].any() or raw[:, 0].any() or raw[:, -1].any()):
        flags.append("mask_touches_fov_edge")

    lab, ncomp = ndimage.label(raw)
    filled = ndimage.binary_fill_holes(raw)
    n_holes_px = int(filled.sum() - raw.sum())
    return {
        "pct_neighbor_ring_bone": pct_ring_bone,
        "n_connected_components": int(ncomp),
        "n_hole_pixels": n_holes_px,
        "slice_flags": flags,
    }


def volume_metrics(ct: np.ndarray, mask: np.ndarray, voxel_mm3: float, slice_ax: int,
                   slice_thickness: float, excl: np.ndarray | None = None) -> dict:
    """3D metrics (only meaningful if the mask covers the whole deltoid)."""
    raw = mask.astype(bool)
    keep = clean_mask(ct, raw, excl)
    s = region_stats(ct[keep], voxel_mm3)
    other = tuple(i for i in range(3) if i != slice_ax)
    per_slice = raw.any(axis=other)
    n_sl = int(per_slice.sum())
    return {
        "vol3d_cm3": s["area"] / 1000.0 if s["n"] else float("nan"),
        "hu_mean_3d": s["hu_mean"],
        "hu_median_3d": s["hu_median"],
        "hu_sd_3d": s["hu_sd"],
        "pct_fat_imat_3d": s["pct_fat"],
        "pct_low_attenuation_lama_3d": s["pct_low_attenuation"],
        "pct_normal_attenuation_nama_3d": s["pct_normal_attenuation"],
        "lean_muscle_vol_cm3": s["lean_muscle_area"] / 1000.0 if s["n"] else float("nan"),
        "n_mask_slices": n_sl,
        "craniocaudal_extent_mm": n_sl * slice_thickness,
    }


def multislice_metrics(ct: np.ndarray, mask: np.ndarray, slice_ax: int, idx: int,
                       half_width: int, px_area: float, excl: np.ndarray | None = None) -> dict:
    """Mean CSA and HU over idx +/- half_width slices (robustness to the chosen slice)."""
    csas, hus, allv = [], [], []
    n = mask.shape[slice_ax]
    for k in range(idx - half_width, idx + half_width + 1):
        if k < 0 or k >= n:
            continue
        m2 = np.take(mask, k, axis=slice_ax).astype(bool)
        if not m2.any():
            continue
        c2 = np.take(ct, k, axis=slice_ax)
        e2 = np.take(excl, k, axis=slice_ax) if excl is not None else None
        keep = clean_mask(c2, m2, e2)
        if not keep.any():
            continue
        csas.append(keep.sum() * px_area)
        hus.append(float(c2[keep].astype(np.float64).mean()))
        allv.append(c2[keep])
    if not csas:
        return {"multislice_n_slices": 0, "csa_mm2_multislice": float("nan"),
                "hu_mean_multislice": float("nan"), "csa_cv_pct_multislice": float("nan")}
    csas = np.array(csas)
    return {
        "multislice_n_slices": int(len(csas)),
        "multislice_half_width": int(half_width),
        "csa_mm2_multislice": float(csas.mean()),
        "hu_mean_multislice": float(np.mean(hus)),
        "hu_mean_multislice_weighted": float(np.concatenate(allv).astype(np.float64).mean()),
        "csa_cv_pct_multislice": float(100 * csas.std(ddof=1) / csas.mean()) if len(csas) > 1 else 0.0,
    }


def histogram(values: np.ndarray, lo=-200, hi=200, step=10):
    edges = np.arange(lo, hi + step, step)
    h, _ = np.histogram(values, bins=edges)
    return edges, h
