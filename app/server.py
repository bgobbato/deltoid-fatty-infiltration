"""DFDI web server.

Phase 2: upload a CT (DICOM zip or NIfTI), list series, serve the NIfTI to the viewer.
Phase 3: receive the deltoid mask drawn in the browser and run the measurement engine.

Run:   .venv/bin/uvicorn app.server:app --port 8080
Data:  folder DFDI_DATA (default ./dados), never committed to git.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))  # measurement engine (src/dfdi)

DATA = Path(os.environ.get("DFDI_DATA", ROOT.parent / "dados")).resolve()
CASES = DATA / "cases"
CASES.mkdir(parents=True, exist_ok=True)
RESULTS_CSV = DATA / "results.csv"

app = FastAPI(title="DFDI")

SAFE = re.compile(r"^[A-Za-z0-9._-]+$")

# Keys shown in the UI and written to the cohort CSV (engine output names).
SUMMARY_KEYS = [
    "csa_mm2", "hu_mean", "dfdi_article_approx", "z_hu_article", "z_csa_article",
    "pct_fat_imat", "pct_low_attenuation_lama", "pct_normal_attenuation_nama",
    "lean_muscle_area_mm2", "hu_mean_lean_muscle", "hu_median", "hu_sd",
    "csa_mm2_raw", "hu_mean_raw", "n_pixels", "slice_index",
    "bone_exclusion", "n_excluded_bone_mask_3d", "n_excluded_bone_200hu",
]


def _dcm2niix() -> str:
    """dcm2niix from the venv (pip package) or from the system."""
    venv_bin = Path(sys.executable).parent / "dcm2niix"
    if venv_bin.exists():
        return str(venv_bin)
    found = shutil.which("dcm2niix")
    if not found:
        raise HTTPException(500, "dcm2niix not found")
    return found


def _case_dir(case_id: str) -> Path:
    if not SAFE.match(case_id):
        raise HTTPException(400, "invalid case id")
    d = CASES / case_id
    if not d.is_dir():
        raise HTTPException(404, "case not found")
    return d


def _series_path(d: Path, name: str) -> Path:
    if not SAFE.match(name) or not name.endswith(".nii.gz"):
        raise HTTPException(400, "invalid series file")
    f = d / "series" / name
    if not f.exists():
        raise HTTPException(404, "series not found")
    return f


def _series_info(nii: Path) -> dict:
    """Series summary from the dcm2niix sidecar (already anonymized)."""
    import nibabel as nib

    js = nii.with_name(nii.name.replace(".nii.gz", ".json"))
    meta = json.loads(js.read_text()) if js.exists() else {}
    img = nib.load(str(nii))
    shape = [int(x) for x in img.shape[:3]]
    zooms = [round(float(x), 3) for x in img.header.get_zooms()[:3]]
    kernel = str(meta.get("ConvolutionKernel", ""))
    desc = str(meta.get("SeriesDescription", nii.name)).strip()
    warnings = []
    if meta.get("KVP") and abs(float(meta["KVP"]) - 120) > 1:
        warnings.append(f"{meta['KVP']} kVp (article: 120)")
    if meta.get("ContrastBolusAgent"):
        warnings.append("contrast-enhanced (article: non-contrast)")
    if shape[2] < 20:
        warnings.append("few slices")
    return {
        "file": nii.name,
        "description": desc,
        "kernel": kernel,
        "manufacturer": meta.get("Manufacturer", ""),
        "kvp": meta.get("KVP"),
        "dims": shape,
        "voxel_mm": zooms,
        "soft_tissue": bool(re.search(r"soft|sft|moles|std|standard|FC0[0-9]|B3|B30|STND", desc + " " + kernel, re.I)),
        "warnings": warnings,
        "reoriented": "DFDI_reorientation" in meta,
        "reorientation": meta.get("DFDI_reorientation"),
    }


# ---------------------------------------------------------------- phase 2

@app.post("/api/cases")
async def upload(file: UploadFile = File(...)):
    """Accept .nii/.nii.gz or a .zip with DICOM. Creates a new case."""
    case_id = uuid.uuid4().hex[:12]
    d = CASES / case_id
    (d / "series").mkdir(parents=True)
    name = (file.filename or "").lower()
    with tempfile.TemporaryDirectory() as tmp:
        suf = ".nii.gz" if name.endswith(".nii.gz") else ".nii" if name.endswith(".nii") else ".zip"
        tmpf = Path(tmp) / ("upload" + suf)
        with tmpf.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        if name.endswith((".nii.gz", ".nii")):
            import nibabel as nib

            try:
                nib.save(nib.load(str(tmpf)), str(d / "series" / "ct.nii.gz"))
            except Exception:
                shutil.rmtree(d, ignore_errors=True)
                raise HTTPException(400, "invalid NIfTI")
        elif name.endswith(".zip"):
            ext = Path(tmp) / "dicom"
            with zipfile.ZipFile(tmpf) as z:
                for m in z.infolist():  # no paths outside the folder
                    if not str((ext / m.filename).resolve()).startswith(str(ext.resolve())):
                        shutil.rmtree(d, ignore_errors=True)
                        raise HTTPException(400, "zip contains an unsafe path")
                z.extractall(ext)
            r = subprocess.run(
                [_dcm2niix(), "-z", "y", "-ba", "y", "-f", "%s_%d", "-o", str(d / "series"), str(ext)],
                capture_output=True, text=True,
            )
            if not list((d / "series").glob("*.nii.gz")):
                shutil.rmtree(d, ignore_errors=True)
                raise HTTPException(400, "no DICOM series found in the zip")
        else:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(400, "send a .nii.gz, .nii or a .zip with DICOM")
    return {"case": case_id, "series": list_series(case_id)["series"]}


@app.get("/api/cases")
def list_cases():
    return {"cases": sorted(p.name for p in CASES.iterdir() if p.is_dir())}


@app.get("/api/cases/{case_id}/series")
def list_series(case_id: str):
    d = _case_dir(case_id)
    series = []
    for nii in sorted((d / "series").glob("*.nii.gz")):
        try:
            series.append(_series_info(nii))
        except Exception as e:  # one broken series does not break the list
            series.append({"file": nii.name, "error": str(e)})
    # soft-tissue series with more slices first
    series.sort(key=lambda s: (not s.get("reoriented", False), not s.get("soft_tissue", False),
                               -(s.get("dims") or [0, 0, 0])[2]))
    return {"case": case_id, "series": series}


@app.get("/api/cases/{case_id}/series/{name}")
def get_series(case_id: str, name: str):
    f = _series_path(_case_dir(case_id), name)
    return FileResponse(f, media_type="application/gzip", filename=name)


# ---------------------------------------------------------------- phase 3

@app.get("/api/cases/{case_id}/series/{name}/bone.nii.gz")
def get_bone_mask(case_id: str, name: str):
    """Automatic bone mask (cortex + marrow, all bones) for display. Cached per series."""
    import numpy as np
    from dfdi.bone import bone_mask
    from dfdi.io import load_nifti, pixel_area_mm2, save_nifti, slice_axis

    d = _case_dir(case_id)
    ct_path = _series_path(d, name)
    out = d / "bone" / name
    if not out.exists():
        out.parent.mkdir(exist_ok=True)
        ct = load_nifti(str(ct_path), np.float32)
        ax, _ = slice_axis(ct)
        px_mm = float(pixel_area_mm2(ct, ax)) ** 0.5
        save_nifti(bone_mask(ct.data, ax, px_mm, slice_mm=float(ct.spacing()[ax])).astype(np.uint8),
                   ct.affine, out, np.uint8)
    return FileResponse(out, media_type="application/gzip", filename="bone.nii.gz")


def _append_results_csv(row: dict):
    new = not RESULTS_CSV.exists()
    cols = ["timestamp", "case", "series", "run"] + SUMMARY_KEYS + ["slice_checklist_ok", "flags"]
    with RESULTS_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


@app.post("/api/cases/{case_id}/measure")
async def measure(case_id: str, series: str = Form(...), mask: UploadFile = File(...),
                  exclude_label: int = Form(2), checklist: str = Form("{}"),
                  bone_exclusion: bool = Form(True)):
    """Save the drawn mask (label 1 = deltoid, label 2 = exclude) and run the engine."""
    import nibabel as nib
    import numpy as np

    d = _case_dir(case_id)
    ct_path = _series_path(d, series)
    run = time.strftime("%Y%m%d-%H%M%S")
    run_dir = d / "results" / run
    run_dir.mkdir(parents=True)
    mask_path = run_dir / "mask.nii.gz"
    with mask_path.open("wb") as f:
        shutil.copyfileobj(mask.file, f)

    try:
        m = np.asanyarray(nib.load(str(mask_path)).dataobj)
        ct_img = nib.load(str(ct_path))
    except Exception:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise HTTPException(400, "could not read the mask")
    if m.shape[:3] != ct_img.shape[:3]:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise HTTPException(400, f"mask grid {m.shape[:3]} differs from CT {ct_img.shape[:3]}")
    if not (m == 1).any():
        shutil.rmtree(run_dir, ignore_errors=True)
        raise HTTPException(400, "no deltoid drawn (label 1 is empty)")

    from dfdi.measure import measure_case, write_json  # imported late: engine may be updated

    try:
        res = measure_case(str(ct_path), str(mask_path), case_id=case_id, labels=[1],
                           exclude_label=exclude_label, out_dir=str(run_dir), make_png=True,
                           bone_exclusion=bone_exclusion)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:  # reference-slice checklist confirmed by the surgeon (article criteria)
        res["slice_checklist"] = json.loads(checklist)
    except ValueError:
        res["slice_checklist"] = {}
    write_json(res, run_dir / "result.json")
    png = next(run_dir.glob("*overlay*.png"), None)
    summary = {k: res.get(k) for k in SUMMARY_KEYS}
    _append_results_csv({"timestamp": run, "case": case_id, "series": series, "run": run,
                         **summary,
                         "slice_checklist_ok": bool(res["slice_checklist"]) and all(res["slice_checklist"].values()),
                         "flags": ";".join(res.get("flags", []))})
    return {
        "case": case_id, "series": series, "run": run,
        "summary": summary, "flags": res.get("flags", []),
        "overlay": f"/api/cases/{case_id}/results/{run}/{png.name}" if png else None,
        "mask": f"/api/cases/{case_id}/results/{run}/mask.nii.gz",
    }


@app.get("/api/cases/{case_id}/results/{run}/{name}")
def get_result_file(case_id: str, run: str, name: str):
    d = _case_dir(case_id)
    if not SAFE.match(run) or not SAFE.match(name):
        raise HTTPException(400, "invalid path")
    f = d / "results" / run / name
    if not f.exists():
        raise HTTPException(404, "not found")
    return FileResponse(f)


@app.get("/api/results.csv")
def results_csv():
    if not RESULTS_CSV.exists():
        raise HTTPException(404, "no results yet")
    return FileResponse(RESULTS_CSV, media_type="text/csv", filename="dfdi_results.csv")


# ---------------------------------------------------------------- phase 4

class ReorientRequest(BaseModel):
    series: str
    p_prox: list[float]            # shaft centre, proximal (world mm, RAS)
    p_dist: list[float]            # shaft centre, distal
    g_ant: list[float] | None = None   # anterior glenoid rim (optional, scapular plane)
    g_post: list[float] | None = None  # posterior glenoid rim


@app.post("/api/cases/{case_id}/reorient")
def reorient(case_id: str, req: ReorientRequest):
    """New series with the axial plane perpendicular to the humeral shaft."""
    import numpy as np
    from dfdi.io import load_nifti, save_nifti
    from dfdi.orientation import reorient_by_points

    d = _case_dir(case_id)
    src = _series_path(d, req.series)
    for name in ("p_prox", "p_dist", "g_ant", "g_post"):
        v = getattr(req, name)
        if v is not None and len(v) != 3:
            raise HTTPException(400, f"{name} must have 3 coordinates")
    if (req.g_ant is None) != (req.g_post is None):
        raise HTTPException(400, "give both glenoid rim points or none")
    ct = load_nifti(str(src), np.float32)
    try:
        vol, info = reorient_by_points(ct, req.p_prox, req.p_dist, req.g_ant, req.g_post)
    except ValueError as e:
        raise HTTPException(400, str(e))
    stem = req.series.replace(".nii.gz", "")
    if stem.startswith("reoriented_"):
        raise HTTPException(400, "reorient the original series, not an already reoriented one")
    run = time.strftime("%Y%m%d-%H%M%S")
    out = d / "series" / f"reoriented_{stem}_{run}.nii.gz"
    save_nifti(np.rint(vol.data).astype(np.int16), vol.affine, out, np.int16)
    src_js = src.with_name(src.name.replace(".nii.gz", ".json"))
    meta = json.loads(src_js.read_text()) if src_js.exists() else {}
    meta["SeriesDescription"] = "REORIENTED " + str(meta.get("SeriesDescription", stem)).strip()
    meta["DFDI_reorientation"] = {"source_series": req.series, "created": run,
                                  "points_world_mm_ras": req.model_dump(exclude={"series"}), **info}
    out.with_name(out.name.replace(".nii.gz", ".json")).write_text(json.dumps(meta, indent=2))
    return {"series": _series_info(out), "info": info}


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
