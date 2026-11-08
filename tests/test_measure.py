"""Tests of the DFDI engine on synthetic phantoms. Run:  .venv/bin/pytest -v -s"""

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from phantom import make_axial_phantom, make_tilted_phantom  # noqa: E402

from dfdi import ARTICLE_REFERENCE  # noqa: E402
from dfdi.cohort import dfdi, icc_a1  # noqa: E402
from dfdi.measure import main, measure_case, run_batch  # noqa: E402

K_REF = 20


def _report(title, pairs):
    print(f"\n=== {title} ===")
    for k, got, exp in pairs:
        print(f"  {k:<28} got={got:>12.4f}   expected={exp:>12.4f}")


def test_ring_reference_slice_exact_values(tmp_path):
    ct, mk, exp = make_axial_phantom(tmp_path)
    r = measure_case(ct, mk, slice_index=K_REF, out_dir=tmp_path)
    e = exp[K_REF]
    _report("Ring phantom, slice 20 (no noise)", [
        ("csa_mm2", r["csa_mm2"], e["csa_mm2"]),
        ("csa_mm2_raw", r["csa_mm2_raw"], e["csa_mm2_raw"]),
        ("analytic csa pi(R2-r2)", r["csa_mm2_raw"], e["csa_analytic_mm2"]),
        ("hu_mean", r["hu_mean"], e["hu_mean"]),
        ("hu_mean_raw", r["hu_mean_raw"], e["hu_mean_raw"]),
        ("pct_fat_imat", r["pct_fat_imat"], e["pct_fat"]),
        ("pct_low_attenuation_lama", r["pct_low_attenuation_lama"], e["pct_lama"]),
        ("pct_normal_attenuation_nama", r["pct_normal_attenuation_nama"], e["pct_nama"]),
        ("lean_muscle_area_mm2", r["lean_muscle_area_mm2"], e["lean_muscle_area_mm2"]),
    ])
    assert r["csa_mm2"] == pytest.approx(e["csa_mm2"], abs=1e-6)
    assert r["csa_mm2_raw"] == pytest.approx(e["csa_mm2_raw"], abs=1e-6)
    assert r["csa_mm2_raw"] == pytest.approx(e["csa_analytic_mm2"], rel=0.01)  # discretization
    assert r["hu_mean"] == pytest.approx(e["hu_mean"], abs=1e-9)
    assert r["hu_mean_raw"] == pytest.approx(e["hu_mean_raw"], abs=1e-9)
    assert r["pct_fat_imat"] == pytest.approx(e["pct_fat"], abs=1e-9)
    assert r["pct_low_attenuation_lama"] == pytest.approx(e["pct_lama"], abs=1e-9)
    assert r["pct_normal_attenuation_nama"] == pytest.approx(e["pct_nama"], abs=1e-9)
    assert r["lean_muscle_area_mm2"] == pytest.approx(e["lean_muscle_area_mm2"], abs=1e-6)
    assert r["n_excluded_bone_200hu"] == e["n_bone"]
    # 3D: 30 slices with mask, 5-slice multi-slice
    assert r["n_mask_slices"] == 30
    assert r["multislice_n_slices"] == 5
    vol_exp = sum(v["n_clean"] for v in exp.values()) * 0.75 * 0.75 * 1.25 / 1000
    print(f"  vol3d_cm3                    got={r['vol3d_cm3']:>12.4f}   expected={vol_exp:>12.4f}")
    assert r["vol3d_cm3"] == pytest.approx(vol_exp, rel=1e-9)
    # DFDI with the article reference, checked by hand
    zh = (e["hu_mean"] - 42.9) / 3.8
    zc = (e["csa_mm2"] - 3651.6) / 662.2
    dexp = 0.5 * (-zh) + 0.5 * (-zc)
    print(f"  dfdi_article_approx          got={r['dfdi_article_approx']:>12.4f}   expected={dexp:>12.4f}")
    assert r["dfdi_article_approx"] == pytest.approx(dexp, abs=1e-9)
    assert (tmp_path / "phantom_ct_overlay.png").exists()
    assert r["flags"] == []          # clean phantom: no QC alerts


def test_single_slice_mask_detects_the_slice(tmp_path):
    ct, mk, exp = make_axial_phantom(tmp_path, single_slice=17, name="single")
    r = measure_case(ct, mk, out_dir=tmp_path)
    assert r["slice_index"] == 17
    assert r["slice_source"] == "single_slice_mask"
    assert r["csa_mm2"] == pytest.approx(exp[17]["csa_mm2"])
    assert r["hu_mean"] == pytest.approx(exp[17]["hu_mean"])
    assert "vol3d_cm3" not in r     # no 3D when there is only one slice


def test_gaussian_noise_tolerance(tmp_path):
    ct, mk, exp = make_axial_phantom(tmp_path, noise_sd=8.0, seed=3, name="noise")
    r = measure_case(ct, mk, slice_index=K_REF, out_dir=tmp_path, make_png=False)
    e = exp[K_REF]
    # noise sd 8 HU with ~7800 pixels => standard error of the mean ~0.1 HU
    _report("Phantom with Gaussian noise sd=8 HU", [("hu_mean", r["hu_mean"], e["hu_mean"]),
                                                   ("csa_mm2", r["csa_mm2"], e["csa_mm2"])])
    assert r["hu_mean"] == pytest.approx(e["hu_mean"], abs=0.5)
    assert r["csa_mm2"] == pytest.approx(e["csa_mm2"], rel=0.002)


def test_labels_anterior_middle_posterior(tmp_path):
    ct, mk, exp = make_axial_phantom(tmp_path, split_labels=True, name="labels")
    r = measure_case(ct, mk, slice_index=K_REF, out_dir=tmp_path, make_png=False)
    parts = [r[f"csa_mm2_label_{L}"] for L in (1, 2, 3)]
    assert sum(parts) == pytest.approx(exp[K_REF]["csa_mm2_raw"])
    r1 = measure_case(ct, mk, slice_index=K_REF, labels="1", out_dir=tmp_path, make_png=False)
    assert r1["csa_mm2_raw"] == pytest.approx(parts[0])


def test_exclusion_label(tmp_path):
    ct, mk, exp = make_axial_phantom(tmp_path, split_labels=True, name="excl")
    # treat label 3 as "hematoma painted by the surgeon"
    r = measure_case(ct, mk, slice_index=K_REF, exclude_label=3, out_dir=tmp_path, make_png=False)
    r_all = measure_case(ct, mk, slice_index=K_REF, out_dir=tmp_path, make_png=False)
    assert r["csa_mm2_raw"] == pytest.approx(r_all["csa_mm2_label_1"] + r_all["csa_mm2_label_2"])


def test_dfdi_article_reference_at_center_is_zero():
    d = dfdi(ARTICLE_REFERENCE["hu_mean"], ARTICLE_REFERENCE["csa_mean"], ARTICLE_REFERENCE)
    assert d["dfdi"] == pytest.approx(0.0)
    d = dfdi(42.9 - 3.8, 3651.6 - 662.2, ARTICLE_REFERENCE)   # -1 SD on both => DFDI = +1
    assert d["dfdi"] == pytest.approx(1.0)


def test_batch_cohort_zscores(tmp_path):
    rows_in = []
    for i, ff in enumerate([0.0, 0.05, 0.10, 0.20, 0.30]):
        ct, mk, _ = make_axial_phantom(tmp_path / f"c{i}", fat_frac=ff, r_out=48 - 2 * i, seed=i, name=f"c{i}")
        rows_in.append({"case_id": f"c{i}", "ct": str(ct), "mask": str(mk), "slice_index": str(K_REF)})
    man = tmp_path / "cases.csv"
    with open(man, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_in[0]))
        w.writeheader()
        w.writerows(rows_in)
    out = tmp_path / "output"
    assert main(["batch", "--manifest", str(man), "--out", str(out), "--no-png"]) == 0
    with open(out / "results.csv") as f:
        rows = list(csv.DictReader(f))
    d = np.array([float(r["dfdi_cohort"]) for r in rows])
    zh = np.array([float(r["z_hu_cohort"]) for r in rows])
    print("\n=== Batch of 5 phantoms (fat 0..30%) ===")
    for r in rows:
        print(f"  {r['case_id']}: CSA={float(r['csa_mm2']):8.1f}  HU={float(r['hu_mean']):6.2f}  "
              f"fat={float(r['pct_fat_imat']):5.1f}%  DFDI_cohort={float(r['dfdi_cohort']):+.3f}")
    assert d.mean() == pytest.approx(0.0, abs=1e-3)          # z-scores of the cohort itself (CSV with 4 decimals)
    assert zh.std(ddof=1) == pytest.approx(1.0, abs=1e-3)
    # more fat AND less area in each case => DFDI must increase monotonically
    assert np.all(np.diff(d) > 0)
    ref = json.loads((out / "cohort_reference.json").read_text())
    assert ref["z_reference"]["n"] == 5


def test_tilted_reorientation_and_auto_slice(tmp_path):
    paths, exp = make_tilted_phantom(tmp_path, theta_deg=20.0)
    k0 = exp["k_center"]
    # 1) without reorienting: CSA on the axial is larger (ellipse) and the engine warns
    r_ax = measure_case(paths["ct"], paths["deltoid"], humerus_path=paths["humerus"], slice_index=k0,
                        out_dir=tmp_path, make_png=False)
    # 2) reoriented + automatic slice
    r_ro = measure_case(paths["ct"], paths["deltoid"], humerus_path=paths["humerus"], reorient=True,
                        auto_slice=True, out_dir=tmp_path, case_id="tilted_reo", save_reoriented=True)
    _report("Tilted phantom 20 degrees", [
        ("recovered axis angle", r_ax["axis_angle_vs_S_axis_deg"], exp["theta"]),
        ("original axial CSA", r_ax["csa_mm2"], exp["csa_axial_expected_mm2"]),
        ("reoriented CSA (auto)", r_ro["csa_mm2"], exp["csa_true_mm2"]),
        ("apex -> auto slice dist mm", r_ro["auto_apex_distance_mm"], exp["apex_dist_expected_mm"]),
    ])
    print("  axial flags:", r_ax["flags"])
    print("  reoriented flags:", r_ro["flags"])
    assert r_ax["axis_angle_vs_S_axis_deg"] == pytest.approx(20.0, abs=1.0)
    assert r_ax["csa_mm2"] == pytest.approx(exp["csa_axial_expected_mm2"], rel=0.02)
    assert any(f.startswith("shaft_tilted_20") for f in r_ax["flags"])
    assert r_ro["csa_mm2"] == pytest.approx(exp["csa_true_mm2"], rel=0.02)
    # linear resampling mixes the ROI edge with the neighboring fat (-100 HU):
    # expected bias of a few HU in hu_mean; the 1 px eroded core returns to ~50
    print(f"  Reoriented HU: hu_mean={r_ro['hu_mean']:.2f}  eroded_core_1px={r_ro['hu_mean_eroded_core_1px']:.2f}"
          f"  (true 50; original axial hu_mean={r_ax['hu_mean']:.2f})")
    assert r_ax["hu_mean"] == pytest.approx(50.0, abs=1e-6)
    assert r_ro["hu_mean"] == pytest.approx(50.0, abs=4.0)
    assert r_ro["hu_mean_eroded_core_1px"] == pytest.approx(50.0, abs=0.5)
    assert r_ro["auto_apex_distance_mm"] == pytest.approx(exp["apex_dist_expected_mm"], abs=1.5)
    assert "auto_slice_requires_confirmation" in r_ro["flags"]
    assert (tmp_path / "tilted_reo_slice_candidates.png").exists()
    assert (tmp_path / "tilted_reo_ct_reoriented.nii.gz").exists()


def test_icc_shrout_fleiss():
    # Shrout & Fleiss (1979), 6 subjects x 4 raters: ICC(2,1)=0.29, ICC(3,1)=0.71
    X = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])
    r = icc_a1(X)
    assert r["icc_a1"] == pytest.approx(0.29, abs=0.005)
    assert r["icc_c1"] == pytest.approx(0.71, abs=0.005)
