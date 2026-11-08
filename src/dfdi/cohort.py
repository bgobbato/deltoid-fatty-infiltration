"""Z-scores, DFDI and ICC.

DFDI = w_hu * (-Z_HU) + w_csa * (-Z_CSA), with w_hu = w_csa = 0.50 in the article.
Z = (X - mean) / SD, with mean and SD (sample, ddof=1) from the REFERENCE COHORT.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

from . import ARTICLE_REFERENCE


def reference_from_values(hu: list[float], csa: list[float], name: str) -> dict:
    hu = np.array([x for x in hu if x is not None and not math.isnan(x)], float)
    csa = np.array([x for x in csa if x is not None and not math.isnan(x)], float)
    if len(hu) < 3 or len(csa) < 3:
        raise ValueError(f"reference '{name}': needs >= 3 valid cases (has {len(hu)})")
    return {"name": name, "hu_mean": float(hu.mean()), "hu_sd": float(hu.std(ddof=1)),
            "csa_mean": float(csa.mean()), "csa_sd": float(csa.std(ddof=1)), "n": int(len(hu))}


def reference_from_csv(path: str | Path, hu_col: str = "hu_mean", csa_col: str = "csa_mm2") -> dict:
    hu, csa = [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                h, c = float(row[hu_col]), float(row[csa_col])
            except (KeyError, ValueError, TypeError):
                continue
            hu.append(h)
            csa.append(c)
    return reference_from_values(hu, csa, f"cohort_csv:{Path(path).name}")


def article_reference() -> dict:
    return dict(ARTICLE_REFERENCE)


def dfdi(hu_mean: float, csa_mm2: float, ref: dict, w_hu: float = 0.5) -> dict:
    w_csa = 1.0 - w_hu
    z_hu = (hu_mean - ref["hu_mean"]) / ref["hu_sd"]
    z_csa = (csa_mm2 - ref["csa_mean"]) / ref["csa_sd"]
    return {"z_hu": z_hu, "z_csa": z_csa, "dfdi": w_hu * (-z_hu) + w_csa * (-z_csa),
            "dfdi_reference": ref["name"], "dfdi_weight_hu": w_hu}


def icc_a1(data: np.ndarray) -> dict:
    """McGraw & Wong ICC(A,1): two-way, absolute agreement, single measure.

    The article cites "two-way mixed-effects, absolute-agreement, single-measure"; in the
    mixed model the point formula is the same as ICC(A,1).
    data: n_subjects x k_ratings matrix (no missing values).
    95% CI: use pingouin.intraclass_corr or irr::icc in R (not implemented here).
    """
    X = np.asarray(data, float)
    n, k = X.shape
    gm = X.mean()
    ss_r = k * ((X.mean(axis=1) - gm) ** 2).sum()
    ss_c = n * ((X.mean(axis=0) - gm) ** 2).sum()
    ss_t = ((X - gm) ** 2).sum()
    ss_e = ss_t - ss_r - ss_c
    msr = ss_r / (n - 1)
    msc = ss_c / (k - 1)
    mse = ss_e / ((n - 1) * (k - 1))
    icc = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    icc_c = (msr - mse) / (msr + (k - 1) * mse)   # ICC(C,1), consistency
    return {"icc_a1": float(icc), "icc_c1": float(icc_c), "n": int(n), "k": int(k)}
