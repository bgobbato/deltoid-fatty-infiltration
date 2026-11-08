"""NIfTI reading, geometry checks and grid utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage


@dataclass
class Volume:
    data: np.ndarray          # 3D array (float32 for CT, int for mask)
    affine: np.ndarray        # 4x4 voxel -> world (mm, NIfTI RAS)
    path: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def shape(self):
        return self.data.shape

    def axis_vectors(self) -> np.ndarray:
        """Affine columns (vector in mm of each voxel axis)."""
        return self.affine[:3, :3]

    def spacing(self) -> np.ndarray:
        return np.linalg.norm(self.affine[:3, :3], axis=0)

    def voxel_volume_mm3(self) -> float:
        return float(abs(np.linalg.det(self.affine[:3, :3])))


def load_nifti(path: str | Path, dtype=np.float32) -> Volume:
    img = nib.load(str(path))
    # get_fdata applies scl_slope/scl_inter automatically
    data = np.asarray(img.get_fdata(dtype=np.float32))
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[..., 0]
    if data.ndim != 3:
        raise ValueError(f"{path}: expected 3D volume, got shape {data.shape}")
    vol = Volume(data=data.astype(dtype, copy=False), affine=img.affine.copy(), path=str(path))
    vol.meta = read_sidecar(path)
    return vol


def read_sidecar(path: str | Path) -> dict:
    """Read the dcm2niix JSON sidecar (same name, .json extension), if it exists.

    The NIfTI loses almost the whole DICOM header; the dcm2niix JSON usually carries
    manufacturer, model, thickness and kernel. Only the fields that exist are copied.
    """
    p = Path(path)
    stem = p.name
    for ext in (".nii.gz", ".nii"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
    js = p.with_name(stem + ".json")
    if not js.exists():
        return {}
    try:
        meta = json.loads(js.read_text())
    except Exception:
        return {}
    keep = ["Manufacturer", "ManufacturersModelName", "KVP", "ConvolutionKernel",
            "SliceThickness", "XRayTubeCurrent", "Modality", "BodyPartExamined",
            "ContrastBolusAgent"]
    return {k: meta[k] for k in keep if k in meta}


def same_grid(a: Volume, b: Volume, atol: float = 1e-3) -> tuple[bool, str]:
    if a.shape != b.shape:
        return False, f"shape mismatch: {a.shape} vs {b.shape}"
    if not np.allclose(a.affine, b.affine, atol=atol):
        return False, "affine mismatch (origin/orientation/spacing)"
    return True, "ok"


def resample_to(moving: Volume, reference: Volume, order: int = 0) -> Volume:
    """Resample `moving` onto the grid of `reference` using world coordinates.

    order=0 (nearest neighbor) for masks; order=1 for intensity.
    """
    M = np.linalg.inv(moving.affine) @ reference.affine
    out = ndimage.affine_transform(
        moving.data, M[:3, :3], offset=M[:3, 3], output_shape=reference.shape,
        order=order, mode="constant", cval=0.0,
    )
    return Volume(data=out.astype(moving.data.dtype), affine=reference.affine.copy(),
                  path=moving.path + " (resampled)", meta=moving.meta)


def slice_axis(vol: Volume) -> tuple[int, int]:
    """Voxel axis most aligned with the world S (craniocaudal) axis.

    Returns (axis, sign): sign=+1 if increasing index goes cranially.
    """
    A = vol.axis_vectors()
    comp = A[2, :] / np.linalg.norm(A, axis=0)   # S component of each axis
    ax = int(np.argmax(np.abs(comp)))
    return ax, int(np.sign(comp[ax]) or 1)


def obliquity_deg(vol: Volume) -> float:
    """Angle (degrees) between the slice axis and the world S axis."""
    ax, _ = slice_axis(vol)
    v = vol.axis_vectors()[:, ax]
    c = abs(v[2]) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def take_slice(arr: np.ndarray, axis: int, idx: int) -> np.ndarray:
    return np.take(arr, idx, axis=axis)


def pixel_area_mm2(vol: Volume, axis: int) -> float:
    """Area of one pixel in the slice plane = |a x b| of the two other axes."""
    A = vol.axis_vectors()
    others = [i for i in range(3) if i != axis]
    return float(np.linalg.norm(np.cross(A[:, others[0]], A[:, others[1]])))


def save_nifti(data: np.ndarray, affine: np.ndarray, path: str | Path, dtype=None):
    arr = data if dtype is None else data.astype(dtype)
    nib.save(nib.Nifti1Image(arr, affine), str(path))
