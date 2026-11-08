"""Quality-control figures (slice overlay and candidate montage)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .io import Volume  # noqa: E402
from .metrics import EXCL_HIGH, EXCL_LOW, FAT  # noqa: E402

WINDOW = (-160, 240)  # W400 / L40 (soft tissue)


def display_2d(arr2d: np.ndarray, vol: Volume, slice_ax: int) -> np.ndarray:
    """Orient the slice in radiological convention: patient right on the left of the
    screen, anterior on top. Uses the affine; also works on the reoriented grid."""
    A = vol.axis_vectors()
    a, b = [i for i in range(3) if i != slice_ax]
    va, vb = A[:, a], A[:, b]
    # horizontal axis = the one most aligned with x (R); vertical = the other
    if abs(va[0]) >= abs(vb[0]):
        img = arr2d.T                     # rows = b, columns = a
        h_vec, v_vec = va, vb
    else:
        img = arr2d                       # rows = a, columns = b
        h_vec, v_vec = vb, va
    if h_vec[0] > 0:                      # increasing column goes to R -> flip
        img = img[:, ::-1]
    if v_vec[1] > 0:                      # increasing row goes to A -> flip (A on top)
        img = img[::-1, :]
    return img


def overlay_png(ct: Volume, mask2d: np.ndarray, slice_ax: int, idx: int, metrics: dict,
                out_path: str, title: str = "", excl2d: np.ndarray | None = None):
    ct2d = np.take(ct.data, idx, axis=slice_ax)
    m = mask2d.astype(bool)
    fat = m & (ct2d >= FAT[0]) & (ct2d < FAT[1])
    exc = m & ((ct2d > EXCL_HIGH) | (ct2d < EXCL_LOW))
    if excl2d is not None:
        exc |= m & excl2d

    D = lambda a: display_2d(a, ct, slice_ax)  # noqa: E731
    img, md, fd, ed = D(ct2d), D(m), D(fat), D(exc)

    fig, axs = plt.subplots(1, 3, figsize=(15, 5.4), gridspec_kw={"width_ratios": [1, 1, 0.9]})
    for ax in axs[:2]:
        ax.imshow(img, cmap="gray", vmin=WINDOW[0], vmax=WINDOW[1], interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.01, 0.5, "R", transform=ax.transAxes, color="w", fontsize=11, va="center")
    axs[0].set_title("CT (W400/L40)")
    axs[1].contour(md, levels=[0.5], colors="red", linewidths=0.8)
    rgba = np.zeros(md.shape + (4,))
    rgba[fd] = (1, 0.9, 0, 0.9)       # fat: yellow
    rgba[ed] = (0, 0.9, 1, 0.9)       # excluded: cyan
    axs[1].imshow(rgba, interpolation="nearest")
    axs[1].set_title("ROI (red) | fat -190..-30 (yellow) | excluded (cyan)", fontsize=9)

    # zoom on the ROI
    ys, xs = np.nonzero(md)
    if len(ys):
        pad = 25
        for ax in axs[1:2]:
            ax.set_xlim(max(xs.min() - pad, 0), min(xs.max() + pad, md.shape[1] - 1))
            ax.set_ylim(min(ys.max() + pad, md.shape[0] - 1), max(ys.min() - pad, 0))

    vals = ct2d[m & ~exc]
    axs[2].hist(vals, bins=np.arange(-200, 205, 5), color="0.3")
    for lo, hi, c in [(-190, -30, "gold"), (-29, 29, "orange"), (30, 150, "salmon")]:
        axs[2].axvspan(lo, hi, color=c, alpha=0.18)
    axs[2].axvline(metrics.get("hu_mean", np.nan), color="red", lw=1)
    axs[2].set_xlabel("HU"); axs[2].set_ylabel("pixels")
    axs[2].set_title("HU histogram of the cleaned ROI")

    txt = (f"slice {idx} | CSA {metrics.get('csa_mm2', np.nan):.0f} mm2 | "
           f"mean HU {metrics.get('hu_mean', np.nan):.1f} | "
           f"fat {metrics.get('pct_fat_imat', np.nan):.1f}% | "
           f"LAMA {metrics.get('pct_low_attenuation_lama', np.nan):.1f}%")
    if "dfdi" in metrics and metrics["dfdi"] is not None:
        txt += f" | DFDI {metrics['dfdi']:+.2f} ({metrics.get('dfdi_reference', '')})"
    flags = metrics.get("flags", [])
    fig.suptitle((title + "\n" if title else "") + txt + ("\nFLAGS: " + ", ".join(flags) if flags else ""),
                 fontsize=10, color="darkred" if flags else "black")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def candidates_png(ct: Volume, deltoid: np.ndarray, humerus: np.ndarray, slice_ax: int,
                   cranial_sign: int, center: int, out_path: str, half: int = 3,
                   profile: list[float] | None = None, title: str = ""):
    """Montage of the candidate slices (cranial to caudal) for the surgeon to choose from."""
    n = ct.shape[slice_ax]
    ks = [center + cranial_sign * d for d in range(half, -half - 1, -1)]   # cranial -> caudal
    ks = [k for k in ks if 0 <= k < n]
    fig, axs = plt.subplots(1, len(ks), figsize=(2.6 * len(ks), 3.2))
    axs = np.atleast_1d(axs)
    D = lambda a: display_2d(a, ct, slice_ax)  # noqa: E731
    # common crop around humerus+deltoid on the central slice
    u = D((np.take(deltoid, center, axis=slice_ax) > 0) | (np.take(humerus, center, axis=slice_ax) > 0))
    ys, xs = np.nonzero(u)
    for ax, k in zip(axs, ks):
        ax.imshow(D(np.take(ct.data, k, axis=slice_ax)), cmap="gray", vmin=-160, vmax=1000)
        ax.contour(D(np.take(humerus, k, axis=slice_ax) > 0), levels=[0.5], colors="lime", linewidths=0.7)
        ax.contour(D(np.take(deltoid, k, axis=slice_ax) > 0), levels=[0.5], colors="red", linewidths=0.7)
        lab = f"k={k}" + (" (suggested)" if k == center else "")
        if profile is not None:
            lab += f"\nA humerus {profile[k]:.0f} mm2"
        ax.set_title(lab, fontsize=8, color="blue" if k == center else "black")
        if len(ys):
            ax.set_xlim(xs.min() - 15, xs.max() + 15)
            ax.set_ylim(ys.max() + 15, ys.min() - 15)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(title or "Reference slice candidates (cranial -> caudal). CONFIRM visually.",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
