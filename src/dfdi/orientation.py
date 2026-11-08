"""Reorientation perpendicular to the humeral shaft and reference-slice suggestion.

Everything here is SEMI-automatic: the axis and the candidate slice need visual
confirmation by the surgeon (see docs/protocolo_medicao_DFDI.md, section 4).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from .io import Volume


def _world_points(vol: Volume, thr: float = 0.5, max_pts: int = 400_000, with_border: bool = False):
    idx = np.argwhere(vol.data > thr)
    if len(idx) > max_pts:
        rng = np.random.default_rng(0)
        idx = idx[rng.choice(len(idx), max_pts, replace=False)]
    P = idx @ vol.affine[:3, :3].T + vol.affine[:3, 3]
    if not with_border:
        return P
    # voxel on the volume face = bone cut by the FOV (the section there is oblique/incomplete)
    shp = np.array(vol.shape)
    border = ((idx == 0) | (idx == shp - 1)).any(axis=1)
    return P, border


def _line_fit(P: np.ndarray):
    c = P.mean(axis=0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    u = vt[0]
    if u[2] < 0:            # points cranially (S+)
        u = -u
    return c, u


def fit_shaft_axis(humerus: Volume, shaft_fraction: float = 0.5, bin_mm: float = 2.0,
                   n_iter: int = 3) -> dict:
    """Humeral shaft axis by PCA + line fit through the centroids.

    1) PCA of all humerus voxels -> approximate long axis (biased by the head).
    2) Repeat: take only the distal portion (shaft_fraction of the visible length),
       slice into slabs of `bin_mm` perpendicular to the current axis, compute the
       centroid of each slab and fit a line through the centroids (SVD).
    """
    P, border = _world_points(humerus, with_border=True)
    if len(P) < 500:
        raise ValueError("humerus mask empty or too small to fit the axis")
    c, u = _line_fit(P)
    cents = np.empty((0, 3))
    for _ in range(n_iter):
        t = (P - c) @ u
        tmin, tmax = t.min(), t.max()
        L = tmax - tmin
        sel = (t >= tmin + 2.0) & (t <= tmin + shaft_fraction * L)
        edges = np.arange(tmin + 2.0, tmin + shaft_fraction * L + bin_mm, bin_mm)
        b = np.digitize(t[sel], edges)
        Ps, Bs = P[sel], border[sel]
        # discard slabs touching the volume border (humerus cut off by the FOV)
        cents = np.array([Ps[b == i].mean(axis=0) for i in np.unique(b)
                          if (b == i).sum() >= 20 and not Bs[b == i].any()])
        if len(cents) < 4:
            break
        c, u = _line_fit(cents)
    t = (P - c) @ u
    L = float(t.max() - t.min())
    if len(cents) >= 2:
        d = cents - c
        resid = np.linalg.norm(d - np.outer(d @ u, u), axis=1)
        rms = float(np.sqrt((resid ** 2).mean()))
    else:
        rms = float("nan")
    angle = float(np.degrees(np.arccos(np.clip(abs(u[2]), 0, 1))))
    flags = []
    if L < 80:
        flags.append("visible_humerus_short_axis_unreliable")
    if len(cents) < 8:
        flags.append("few_centroids_in_shaft")
    if not np.isnan(rms) and rms > 2.0:
        flags.append("curved_shaft_or_irregular_mask")
    return {"axis": u.tolist(), "point": c.tolist(), "angle_vs_S_axis_deg": angle,
            "visible_humerus_length_mm": L, "n_centroids": int(len(cents)),
            "rms_centroids_mm": rms, "axis_flags": flags}


def basis_from_axis(u: np.ndarray, lateral_hint: np.ndarray | None = None) -> np.ndarray:
    """Orthonormal basis [e1 e2 e3] (columns) with e3 = shaft axis.

    The in-plane rotation (e1) does NOT change the area or HU of the axial slice; it
    only changes the presentation. If there is a reference direction (e.g. the normal
    of the scapular plane), pass it in `lateral_hint` so the coronal plane is parallel
    to the scapula.
    """
    e3 = np.asarray(u, float) / np.linalg.norm(u)
    ref = np.array([1.0, 0, 0]) if lateral_hint is None else np.asarray(lateral_hint, float)
    if abs(ref @ e3) > 0.9:
        ref = np.array([0, 1.0, 0])
    e1 = ref - (ref @ e3) * e3
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(e3, e1)
    return np.column_stack([e1, e2, e3])


def reslice(volumes: dict[str, tuple[Volume, str]], axis: np.ndarray, crop_points: np.ndarray,
            spacing: tuple[float, float, float], margin_mm: float = 15.0,
            lateral_hint: np.ndarray | None = None) -> dict[str, Volume]:
    """Resample volumes onto a new grid whose k axis follows the shaft (increasing k = cranial).

    volumes: name -> (Volume, mode) with mode in {"ct", "binary", "label"}.
      ct: linear interpolation (outside the FOV = -1024)
      binary: linear and 0.5 threshold (area more faithful than nearest neighbor)
      label: nearest neighbor (preserves labels)
    """
    E = basis_from_axis(axis, lateral_hint)
    q = crop_points @ E
    qmin = q.min(axis=0) - margin_mm
    qmax = q.max(axis=0) + margin_mm
    sp = np.asarray(spacing, float)
    shape = tuple(int(np.ceil((qmax[i] - qmin[i]) / sp[i])) + 1 for i in range(3))
    A_new = np.eye(4)
    A_new[:3, :3] = E * sp
    A_new[:3, 3] = E @ qmin
    out = {}
    for name, (vol, mode) in volumes.items():
        M = np.linalg.inv(vol.affine) @ A_new
        if mode == "ct":
            arr = ndimage.affine_transform(vol.data.astype(np.float32), M[:3, :3], offset=M[:3, 3],
                                           output_shape=shape, order=1, mode="constant", cval=-1024.0)
        elif mode == "binary":
            arr = ndimage.affine_transform((vol.data > 0).astype(np.float32), M[:3, :3], offset=M[:3, 3],
                                           output_shape=shape, order=1, mode="constant", cval=0.0)
            arr = (arr >= 0.5).astype(np.uint8)
        else:
            arr = ndimage.affine_transform(vol.data, M[:3, :3], offset=M[:3, 3], output_shape=shape,
                                           order=0, mode="constant", cval=0)
        out[name] = Volume(data=arr, affine=A_new.copy(), path=vol.path + " (reoriented)", meta=vol.meta)
    return out


def humerus_area_profile(hum: np.ndarray, slice_ax: int, px_area: float) -> np.ndarray:
    other = tuple(i for i in range(3) if i != slice_ax)
    return (hum > 0).sum(axis=other) * px_area


def candidate_reference_slice(hum: np.ndarray, deltoid: np.ndarray, slice_ax: int, cranial_sign: int,
                              px_area: float, slice_mm: float, area_fraction: float = 0.70,
                              search_mm: float = 60.0, min_area_mm2: float = 20.0) -> dict:
    """Suggest the reference slice from the humeral head area profile.

    Heuristic (NOT validated; calibrate against the slices chosen by the surgeon):
      - descends from the head apex in the craniocaudal direction;
      - the humerus cross-section area grows to a maximum (anatomical neck /
        tuberosities region) and then falls toward the surgical neck;
      - candidate = first slice (top to bottom) with area >= area_fraction x
        maximum area of the head window. It always sits above the maximum, i.e.
        above the surgical neck.
    """
    prof = humerus_area_profile(hum, slice_ax, px_area)
    n = len(prof)
    order = np.arange(n) if cranial_sign < 0 else np.arange(n)[::-1]   # from cranial to caudal
    present = [k for k in order if prof[k] > min_area_mm2]
    flags = []
    if not present:
        return {"candidate_index": None, "auto_slice_flags": ["humerus_absent"]}
    top = present[0]
    win = int(round(search_mm / slice_mm))
    pos_top = list(order).index(top)
    window = list(order[pos_top: pos_top + win])
    k_max = max(window, key=lambda k: prof[k])
    a_max = prof[k_max]
    cand = next(k for k in window if prof[k] >= area_fraction * a_max)
    other = tuple(i for i in range(3) if i != slice_ax)
    delt_present = (deltoid > 0).any(axis=other)
    if not delt_present[cand]:
        flags.append("deltoid_absent_at_candidate")
    if k_max == window[-1]:
        flags.append("max_area_at_window_limit")
    return {
        "candidate_index": int(cand),
        "head_apex_index": int(top),
        "max_humerus_area_index": int(k_max),
        "apex_distance_mm": float(abs(cand - top) * slice_mm),
        "candidate_humerus_area_mm2": float(prof[cand]),
        "max_humerus_area_mm2": float(a_max),
        "candidate_area_ratio": float(prof[cand] / a_max),
        "area_fraction_used": area_fraction,
        "auto_slice_flags": flags,
        "humerus_area_profile_mm2": [float(x) for x in prof],
    }


def area_ratio_at(hum: np.ndarray, slice_ax: int, cranial_sign: int, px_area: float,
                  slice_mm: float, k: int, search_mm: float = 60.0) -> dict:
    """For a slice chosen by the surgeon: ratio area(k)/maximum head area and distance
    from the apex. Used to CALIBRATE `area_fraction` on the first cases."""
    r = candidate_reference_slice(hum, hum, slice_ax, cranial_sign, px_area, slice_mm,
                                  area_fraction=1.0, search_mm=search_mm)
    if r.get("candidate_index") is None:
        return {}
    prof = np.asarray(r["humerus_area_profile_mm2"])
    return {
        "calib_humerus_area_ratio_at_slice": float(prof[k] / r["max_humerus_area_mm2"]),
        "calib_apex_distance_mm": float(abs(k - r["head_apex_index"]) * slice_mm),
    }


def basis_from_points(p_prox, p_dist, g_ant=None, g_post=None) -> tuple[np.ndarray, dict]:
    """Orthonormal basis [e1 e2 e3] (columns, world RAS) from surgeon-picked points.

    e3 = humeral shaft axis, from the distal to the proximal shaft centre (cranial).
    e2 = anterior. If the anterior and posterior glenoid rim are given, e2 follows the
         glenoid AP direction, so the coronal plane (e1, e3) is parallel to the scapular
         plane (as in the article). Otherwise e2 = world anterior projected.
    e1 = e2 x e3 (patient right, right-handed like RAS).
    The in-plane rotation does not change CSA or HU; only e3 matters for the measurement.
    """
    p_prox, p_dist = np.asarray(p_prox, float), np.asarray(p_dist, float)
    v = p_prox - p_dist
    length = float(np.linalg.norm(v))
    if length < 20:
        raise ValueError(f"shaft points only {length:.1f} mm apart; pick them at least 20 mm apart")
    e3 = v / length
    info = {"shaft_points_distance_mm": length,
            "shaft_angle_vs_S_axis_deg": float(np.degrees(np.arccos(abs(e3[2])))),
            "scapular_plane_from_glenoid": False}
    if g_ant is not None and g_post is not None:
        a = np.asarray(g_ant, float) - np.asarray(g_post, float)
        a = a - (a @ e3) * e3
        if np.linalg.norm(a) < 5:
            raise ValueError("glenoid rim points too close (after projection); pick the anterior and posterior rim")
        e2 = a / np.linalg.norm(a)
        info["scapular_plane_from_glenoid"] = True
    else:
        ref = np.array([0.0, 1.0, 0.0])
        if abs(ref @ e3) > 0.9:
            ref = np.array([1.0, 0.0, 0.0])
        e2 = ref - (ref @ e3) * e3
        e2 /= np.linalg.norm(e2)
    e1 = np.cross(e2, e3)
    return np.column_stack([e1, e2, e3]), info


def reorient_by_points(ct: Volume, p_prox, p_dist, g_ant=None, g_post=None,
                       half_width_mm: float = 100.0, below_mm: float = 20.0, above_mm: float = 110.0,
                       spacing: tuple[float, float, float] | None = None) -> tuple[Volume, dict]:
    """Reslice the CT so the axial plane is perpendicular to the humeral shaft.

    The new box is centred on the shaft line: +-half_width_mm in-plane, from below_mm under
    the distal point to above_mm over the proximal point (head and acromion included).
    Default spacing = original in-plane pixel and original slice thickness.
    """
    E, info = basis_from_points(p_prox, p_dist, g_ant, g_post)
    if spacing is None:
        sp = ct.spacing()
        ax = int(np.argmax(np.abs(ct.axis_vectors()[2, :]) / sp))
        inplane = float(min(sp[i] for i in range(3) if i != ax))
        spacing = (inplane, inplane, float(sp[ax]))
    p_dist = np.asarray(p_dist, float)
    p_prox = np.asarray(p_prox, float)
    e1, e2, e3 = E[:, 0], E[:, 1], E[:, 2]
    lo = p_dist - below_mm * e3
    hi = p_prox + above_mm * e3
    corners = np.array([base + s1 * half_width_mm * e1 + s2 * half_width_mm * e2
                        for base in (lo, hi) for s1 in (-1, 1) for s2 in (-1, 1)])
    # reslice() works in the E frame given by basis_from_axis; build it from our E directly
    q = corners @ E
    qmin, qmax = q.min(axis=0), q.max(axis=0)
    sp = np.asarray(spacing, float)
    shape = tuple(int(np.ceil((qmax[i] - qmin[i]) / sp[i])) + 1 for i in range(3))
    A_new = np.eye(4)
    A_new[:3, :3] = E * sp
    A_new[:3, 3] = E @ qmin
    M = np.linalg.inv(ct.affine) @ A_new
    arr = ndimage.affine_transform(ct.data.astype(np.float32), M[:3, :3], offset=M[:3, 3],
                                   output_shape=shape, order=1, mode="constant", cval=-1024.0)
    info.update({"reoriented_shape": list(shape), "reoriented_spacing_mm": [float(x) for x in sp],
                 "basis_E_columns": E.tolist()})
    return Volume(data=arr, affine=A_new, path=ct.path + " (reoriented)", meta=ct.meta), info
