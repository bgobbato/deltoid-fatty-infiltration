"""DFDI measurement engine: one case (measure) or a folder/list of cases (batch).

Quick usage (see README.md):
  python -m dfdi measure --ct ct.nii.gz --mask deltoid.nii.gz --slice-index 112 --out output/
  python -m dfdi batch --manifest cases.csv --out output/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np

from . import __version__
from .cohort import article_reference, dfdi, icc_a1, reference_from_csv, reference_from_values
from .io import (Volume, load_nifti, obliquity_deg, pixel_area_mm2, resample_to, same_grid,
                 save_nifti, slice_axis)
from .metrics import multislice_metrics, slice_metrics, volume_metrics
from .orientation import (_world_points, area_ratio_at, candidate_reference_slice,
                          fit_shaft_axis, reslice)
from .bone import bone_mask
from .qc import candidates_png, overlay_png

ARTICLE_SLICE_MM = 1.25

# columns that appear first in the CSV
MAIN_COLS = [
    "case_id", "slice_index", "slice_source", "csa_mm2", "hu_mean",
    "dfdi_cohort", "z_hu_cohort", "z_csa_cohort", "dfdi_article_approx", "z_hu_article", "z_csa_article",
    "pct_fat_imat", "pct_low_attenuation_lama", "pct_normal_attenuation_nama",
    "lean_muscle_area_mm2", "hu_mean_lean_muscle", "hu_median", "hu_sd",
    "csa_mm2_multislice", "hu_mean_multislice", "csa_cv_pct_multislice", "multislice_n_slices",
    "vol3d_cm3", "hu_mean_3d", "pct_fat_imat_3d", "n_mask_slices",
    "csa_mm2_raw", "hu_mean_raw", "n_pixels", "flags", "error",
]


def _parse_labels(s):
    if s is None or s == "" or (isinstance(s, float) and math.isnan(s)):
        return None
    if isinstance(s, (list, tuple)):
        return [int(x) for x in s]
    return [int(x) for x in str(s).split(",") if x.strip()]


def measure_case(ct_path, mask_path, *, case_id=None, humerus_path=None, slice_index=None,
                 auto_slice=False, reorient=False, labels=None, exclude_label=None, neighbors=2,
                 cohort_ref: dict | None = None, weight_hu=0.5, out_dir=None,
                 resample_mask=False, area_fraction=0.70, save_reoriented=False,
                 make_png=True, bone_exclusion=False, bone_margin_px=1) -> dict:
    case_id = case_id or Path(str(ct_path)).name.split(".")[0]
    flags: list[str] = []
    res: dict = {"case_id": case_id, "dfdi_version": __version__, "ct": str(ct_path),
                 "mask": str(mask_path)}
    out_dir = Path(out_dir) if out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    ct = load_nifti(ct_path, np.float32)
    mk = load_nifti(mask_path, np.float32)
    hum = load_nifti(humerus_path, np.float32) if humerus_path else None
    if ct.meta:
        res["ct_metadata"] = ct.meta

    ok, why = same_grid(ct, mk)
    if not ok:
        if not resample_mask:
            raise ValueError(f"CT and mask on different grids ({why}). "
                             "Use --resample-mask to resample the mask onto the CT grid.")
        mk = resample_to(mk, ct, order=0)
        flags.append("mask_resampled_to_ct_grid")
    if hum is not None and not same_grid(ct, hum)[0]:
        hum = resample_to(hum, ct, order=0)
        flags.append("humerus_resampled_to_ct_grid")

    # --- HU scale sanity ---
    res["ct_hu_min"] = float(ct.data.min())
    res["ct_hu_max"] = float(ct.data.max())
    if res["ct_hu_min"] > -500:
        flags.append("ct_may_not_be_in_HU_air_absent_or_offset")

    # --- deltoid mask and exclusion label ---
    lab = np.rint(mk.data).astype(np.int32)
    labels = _parse_labels(labels)
    excl = (lab == int(exclude_label)) if exclude_label is not None else None
    delt = np.isin(lab, labels) if labels else (lab > 0)
    if excl is not None:
        delt &= ~excl
    present_labels = sorted(int(x) for x in np.unique(lab[delt]))
    res["labels_present"] = present_labels

    ax0, _ = slice_axis(ct)
    other0 = tuple(i for i in range(3) if i != ax0)
    n_mask_slices = int(delt.any(axis=other0).sum())
    if n_mask_slices == 0:
        raise ValueError("deltoid mask is empty (check --labels / label used)")

    # --- shaft axis / reorientation ---
    axis_info = None
    if hum is not None:
        axis_info = fit_shaft_axis(hum)
        res.update({f"axis_{k}": v for k, v in axis_info.items() if k not in ("axis", "point")})
        res["shaft_axis_vector"] = axis_info["axis"]
        flags += axis_info["axis_flags"]

    if reorient:
        if hum is None:
            raise ValueError("--reorient requires --humerus")
        if n_mask_slices == 1:
            raise ValueError("a single-slice mask cannot be reoriented; "
                             "draw the ROI directly on the reoriented image")
        sp = ct.spacing()
        inplane = float(min(sp[i] for i in other0))
        through = float(sp[ax0])
        pts = np.vstack([_world_points(Volume(delt.astype(np.float32), ct.affine)),
                         _world_points(hum)])
        vols = {"ct": (ct, "ct"), "delt": (Volume(delt.astype(np.float32), ct.affine), "binary"),
                "hum": (hum, "binary"), "lab": (Volume(lab, ct.affine), "label")}
        if excl is not None:
            vols["excl"] = (Volume(excl.astype(np.float32), ct.affine), "binary")
        rv = reslice(vols, np.array(axis_info["axis"]), pts, (inplane, inplane, through))
        ct = rv["ct"]
        delt = rv["delt"].data.astype(bool)
        hum = rv["hum"]
        lab = rv["lab"].data
        excl = rv["excl"].data.astype(bool) if "excl" in rv else None
        res["reoriented"] = True
        flags.append("auto_reoriented_check_axis")
        if save_reoriented and out_dir:
            save_nifti(ct.data, ct.affine, out_dir / f"{case_id}_ct_reoriented.nii.gz", np.int16)
            save_nifti(delt.astype(np.uint8), ct.affine, out_dir / f"{case_id}_deltoid_reoriented.nii.gz")
            save_nifti(hum.data.astype(np.uint8), ct.affine, out_dir / f"{case_id}_humerus_reoriented.nii.gz")
    else:
        res["reoriented"] = False
        if axis_info and axis_info["angle_vs_S_axis_deg"] > 5:
            a = axis_info["angle_vs_S_axis_deg"]
            over = 100 * (1 / math.cos(math.radians(a)) - 1)
            flags.append(f"shaft_tilted_{a:.0f}deg_CSA_overestimated_~{over:.0f}pct")

    ax, sign = slice_axis(ct)
    other = tuple(i for i in range(3) if i != ax)
    px = pixel_area_mm2(ct, ax)
    thick = float(ct.spacing()[ax])
    res.update({"slice_axis": ax, "slice_thickness_mm": thick, "pixel_area_mm2": px,
                "grid_obliquity_deg": obliquity_deg(ct)})
    if abs(thick - ARTICLE_SLICE_MM) > 0.3:
        flags.append(f"slice_thickness_{thick:.2f}mm_differs_from_article_1.25mm")

    per_slice = delt.any(axis=other)
    mask_slices = np.flatnonzero(per_slice)
    res["n_mask_slices"] = int(len(mask_slices))
    is_single = len(mask_slices) == 1

    # --- automatic bone mask as a negative mask (cortex + marrow, all bones) ---
    res["bone_exclusion"] = bool(bone_exclusion)
    if bone_exclusion:
        px_mm = float(math.sqrt(px))
        bone = bone_mask(ct.data, ax, px_mm, slices=mask_slices, slice_mm=thick, margin_px=bone_margin_px)
        res["n_excluded_bone_mask_3d"] = int((delt & bone).sum())
        res["bone_margin_px"] = int(bone_margin_px)
        excl = bone if excl is None else (excl | bone)
    auto = None
    if hum is not None:
        hum_bin = hum.data > 0.5
        auto = candidate_reference_slice(hum_bin, delt, ax, sign, px, thick, area_fraction=area_fraction)
    if slice_index is not None:
        k, origin = int(slice_index), "user_provided"
    elif is_single:
        k, origin = int(mask_slices[0]), "single_slice_mask"
    elif auto_slice:
        if auto is None or auto.get("candidate_index") is None:
            raise ValueError("--auto-slice requires a valid --humerus")
        k, origin = auto["candidate_index"], "auto_candidate"
        flags.append("auto_slice_requires_confirmation")
        flags += auto["auto_slice_flags"]
    else:
        k, origin = None, "not_defined"
        flags.append("reference_slice_not_defined_3d_metrics_only")
    res["slice_index"] = k
    res["slice_source"] = origin
    if auto is not None:
        res.update({f"auto_{kk}": vv for kk, vv in auto.items()
                    if kk not in ("humerus_area_profile_mm2", "auto_slice_flags")})

    # --- slice metrics ---
    if k is not None:
        if not (0 <= k < ct.shape[ax]):
            raise ValueError(f"slice index {k} outside the volume (0..{ct.shape[ax]-1})")
        m2 = np.take(delt, k, axis=ax)
        c2 = np.take(ct.data, k, axis=ax)
        e2 = np.take(excl, k, axis=ax) if excl is not None else None
        if not m2.any():
            flags.append("mask_empty_in_chosen_slice")
        sm = slice_metrics(c2, m2, px, e2)
        flags += sm.pop("slice_flags")
        res.update(sm)
        if len(present_labels) > 1:
            l2 = np.take(lab, k, axis=ax)
            for L in present_labels:
                res[f"csa_mm2_label_{L}"] = float(((l2 == L) & m2).sum() * px)
        if not is_single:
            res.update(multislice_metrics(ct.data, delt, ax, k, neighbors, px, excl))
        if hum is not None:
            res.update(area_ratio_at(hum.data > 0.5, ax, sign, px, thick, k))

    # --- 3D metrics ---
    if not is_single:
        res.update(volume_metrics(ct.data, delt, ct.voxel_volume_mm3(), ax, thick, excl))

    # --- DFDI ---
    if k is not None and not math.isnan(res.get("hu_mean", float("nan"))):
        da = dfdi(res["hu_mean"], res["csa_mm2"], article_reference(), weight_hu)
        res.update({"dfdi_article_approx": da["dfdi"], "z_hu_article": da["z_hu"], "z_csa_article": da["z_csa"]})
        if cohort_ref is not None:
            dc = dfdi(res["hu_mean"], res["csa_mm2"], cohort_ref, weight_hu)
            res.update({"dfdi_cohort": dc["dfdi"], "z_hu_cohort": dc["z_hu"], "z_csa_cohort": dc["z_csa"],
                        "dfdi_reference": cohort_ref["name"]})
    res["dfdi_weight_hu"] = weight_hu
    res["flags"] = flags

    # --- figures ---
    if out_dir and make_png:
        if k is not None:
            show = dict(res)
            show["dfdi"] = res.get("dfdi_cohort", res.get("dfdi_article_approx"))
            show["dfdi_reference"] = "cohort" if "dfdi_cohort" in res else "article, approx."
            overlay_png(ct, np.take(delt, k, axis=ax), ax, k, show, str(out_dir / f"{case_id}_overlay.png"),
                        title=f"{case_id} ({origin})",
                        excl2d=np.take(excl, k, axis=ax) if excl is not None else None)
            res["overlay_png"] = str(out_dir / f"{case_id}_overlay.png")
        if auto is not None and auto.get("candidate_index") is not None:
            candidates_png(ct, delt, hum.data, ax, sign, auto["candidate_index"],
                           str(out_dir / f"{case_id}_slice_candidates.png"),
                           profile=auto["humerus_area_profile_mm2"])
            res["candidates_png"] = str(out_dir / f"{case_id}_slice_candidates.png")
    if auto is not None:
        res["_humerus_area_profile_mm2"] = auto.get("humerus_area_profile_mm2")
    return res


# ----------------------------------------------------------------------------- output

def _flat(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if k.startswith("_"):
            continue
        if isinstance(v, (list, tuple)):
            v = ";".join(str(x) for x in v)
        elif isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, float):
            v = "" if math.isnan(v) else round(v, 4)
        out[k] = v
    return out


def write_csv(rows: list[dict], path):
    flat = [_flat(r) for r in rows]
    keys = [c for c in MAIN_COLS if any(c in r for r in flat)]
    for r in flat:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(flat)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    return str(o)


def write_json(obj, path):
    def clean(x):
        if isinstance(x, float) and math.isnan(x):
            return None
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        if isinstance(x, list):
            return [clean(v) for v in x]
        return x
    Path(path).write_text(json.dumps(clean(obj), indent=2, ensure_ascii=False, default=_json_default))


# ----------------------------------------------------------------------------- batch

def read_manifest(path) -> list[dict]:
    base = Path(path).resolve().parent
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
            for col in ("ct", "mask", "humerus"):
                if r.get(col):
                    p = Path(r[col])
                    r[col] = str(p if p.is_absolute() else base / p)
            rows.append(r)
    return rows


def discover(root, ct_name, mask_name, humerus_name) -> list[dict]:
    rows = []
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        ct, mk = d / ct_name, d / mask_name
        if not (ct.exists() and mk.exists()):
            continue
        r = {"case_id": d.name, "ct": str(ct), "mask": str(mk)}
        if humerus_name and (d / humerus_name).exists():
            r["humerus"] = str(d / humerus_name)
        sl = d / "slice.txt"             # index confirmed by the surgeon, optional
        if sl.exists():
            r["slice_index"] = sl.read_text().strip()
        rows.append(r)
    return rows


def run_batch(cases: list[dict], out_dir, *, cohort_csv=None, weight_hu=0.5, **kw) -> list[dict]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in cases:
        cid = c.get("case_id") or Path(c["ct"]).parent.name
        si = c.get("slice_index")
        si = int(si) if si not in (None, "") else None
        print(f"[dfdi] {cid} ...", file=sys.stderr)
        try:
            r = measure_case(c["ct"], c["mask"], case_id=cid, humerus_path=c.get("humerus") or None,
                             slice_index=si, out_dir=out_dir / "figures", weight_hu=weight_hu,
                             labels=c.get("labels") or kw.get("labels"), **{k: v for k, v in kw.items()
                                                                           if k != "labels"})
        except Exception as e:  # one bad case does not take down the batch
            r = {"case_id": cid, "error": f"{type(e).__name__}: {e}", "flags": ["error"]}
            traceback.print_exc()
        rows.append(r)

    # reference for z-scores: external CSV or the batch cohort itself
    valid = [r for r in rows if not math.isnan(r.get("hu_mean", float("nan")))]
    ref = None
    if cohort_csv:
        ref = reference_from_csv(cohort_csv)
    elif len(valid) >= 3:
        ref = reference_from_values([r["hu_mean"] for r in valid], [r["csa_mm2"] for r in valid],
                                    f"batch_cohort_n{len(valid)}")
    if ref is not None:
        for r in valid:
            d = dfdi(r["hu_mean"], r["csa_mm2"], ref, weight_hu)
            r.update({"dfdi_cohort": d["dfdi"], "z_hu_cohort": d["z_hu"], "z_csa_cohort": d["z_csa"],
                      "dfdi_reference": ref["name"]})
    write_csv(rows, out_dir / "results.csv")
    write_json(rows, out_dir / "results.json")
    write_json({"z_reference": ref, "article_reference": article_reference(),
                "n_cases": len(rows), "n_valid": len(valid)}, out_dir / "cohort_reference.json")
    return rows


# ----------------------------------------------------------------------------- CLI

def _common(p):
    p.add_argument("--labels", help="deltoid labels in the mask, e.g. 1,2,3 (default: any >0)")
    p.add_argument("--exclude-label", type=int, help="label painted over hematoma/fluid/fragment to exclude")
    p.add_argument("--auto-slice", action="store_true",
                   help="suggest the reference slice from the humerus (CANDIDATE, check it)")
    p.add_argument("--reorient", action="store_true", help="reorient perpendicular to the shaft (requires --humerus)")
    p.add_argument("--save-reoriented", action="store_true", help="save reoriented CT/masks for review")
    p.add_argument("--neighbors", type=int, default=2, help="half-width of the multi-slice (default 2 => 5 slices)")
    p.add_argument("--area-fraction", type=float, default=0.70,
                   help="fraction of the maximum humerus area used by the slice heuristic (calibrate)")
    p.add_argument("--weight-hu", type=float, default=0.5, help="weight of -Z_HU in the DFDI (article: 0.5)")
    p.add_argument("--cohort-csv", help="CSV with hu_mean,csa_mm2 columns of the reference cohort")
    p.add_argument("--resample-mask", action="store_true", help="resample the mask if the grid differs")
    p.add_argument("--no-png", action="store_true")
    p.add_argument("--bone-exclusion", action="store_true",
                   help="automatic bone mask (cortex + marrow, all bones) removed from the ROI")
    p.add_argument("--bone-margin-px", type=int, default=1, help="dilation of the bone mask in pixels (default 1)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dfdi", description="DFDI measurement engine (deltoid, CT)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("measure", help="measure one case")
    pm.add_argument("--ct", required=True)
    pm.add_argument("--mask", required=True)
    pm.add_argument("--humerus")
    pm.add_argument("--slice-index", type=int, help="0-based slice index along the file's craniocaudal axis")
    pm.add_argument("--case-id")
    pm.add_argument("--out", default="output")
    _common(pm)

    pb = sub.add_parser("batch", help="measure several cases and compute cohort z-scores/DFDI")
    g = pb.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest", help="CSV: case_id,ct,mask[,humerus,slice_index,labels]")
    g.add_argument("--root", help="folder with one subfolder per case")
    pb.add_argument("--ct-name", default="ct.nii.gz")
    pb.add_argument("--mask-name", default="deltoid.nii.gz")
    pb.add_argument("--humerus-name", default="humerus.nii.gz")
    pb.add_argument("--out", default="output")
    _common(pb)

    pi = sub.add_parser("icc", help="ICC(A,1) of repeated measurements")
    pi.add_argument("--csv", required=True)
    pi.add_argument("--cols", required=True, help="rating columns, e.g. obs1,obs2")

    a = ap.parse_args(argv)

    if a.cmd == "icc":
        cols = a.cols.split(",")
        with open(a.csv, newline="") as f:
            X = [[float(r[c]) for c in cols] for r in csv.DictReader(f)]
        print(json.dumps(icc_a1(np.array(X)), indent=2))
        return 0

    kw = dict(auto_slice=a.auto_slice, reorient=a.reorient, labels=a.labels, exclude_label=a.exclude_label,
              neighbors=a.neighbors, resample_mask=a.resample_mask, area_fraction=a.area_fraction,
              save_reoriented=a.save_reoriented, make_png=not a.no_png,
              bone_exclusion=a.bone_exclusion, bone_margin_px=a.bone_margin_px)

    if a.cmd == "measure":
        ref = reference_from_csv(a.cohort_csv) if a.cohort_csv else None
        r = measure_case(a.ct, a.mask, case_id=a.case_id, humerus_path=a.humerus, slice_index=a.slice_index,
                         cohort_ref=ref, weight_hu=a.weight_hu, out_dir=a.out, **kw)
        out = Path(a.out)
        write_json(r, out / f"{r['case_id']}_metrics.json")
        write_csv([r], out / f"{r['case_id']}_metrics.csv")
        show = {k: r.get(k) for k in MAIN_COLS if k in r}
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in show.items()},
                         indent=2, ensure_ascii=False, default=_json_default))
        return 0

    cases = read_manifest(a.manifest) if a.manifest else discover(a.root, a.ct_name, a.mask_name, a.humerus_name)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 1
    rows = run_batch(cases, a.out, cohort_csv=a.cohort_csv, weight_hu=a.weight_hu, **kw)
    n_err = sum(1 for r in rows if r.get("error"))
    print(f"[dfdi] {len(rows)} cases, {n_err} with errors -> {Path(a.out) / 'results.csv'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
