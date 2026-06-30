"""
nifti.py
--------
Thin wrappers around nibabel for loading and saving NIfTI files.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def load_nifti(
    path: str | Path,
    ref: str | Path | nib.Nifti1Image | None = None,
    interpolation: str = "continuous",
) -> tuple[np.ndarray, nib.Nifti1Image]:
    """Load a NIfTI file and return ``(data, img)``.
    Parameters
    ----------
    path : str or Path
        Path to a ``.nii`` or ``.nii.gz`` file.
    ref : str, Path, nib.Nifti1Image, or None
        Optional reference image. When provided the loaded image is
        resampled onto the reference voxel grid via :func:`resample_to_ref`
        before the data array is extracted.
    interpolation : str
        Interpolation strategy forwarded to :func:`resample_to_ref` when
        ``ref`` is not ``None``. Use ``"nearest"`` for label / binary images
        and ``"continuous"`` (default) for scalar fields.
    Returns
    -------
    data : np.ndarray
        Volume data (float64 by default via nibabel).
    img : nib.Nifti1Image
        Full nibabel image object (resampled when ``ref`` is given).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {path}")
    img = nib.load(str(path))
    if ref is not None:
        img = resample_to_ref(img, ref, interpolation=interpolation)
    data = img.get_fdata()
    return data, img


def save_nifti(
    img: nib.Nifti1Image,
    path: str | Path,
    makedirs: bool = True,
) -> Path:
    """Save a nibabel image to disk.

    Parameters
    ----------
    img : nib.Nifti1Image
        Image to write.
    path : str or Path
        Destination file path.
    makedirs : bool
        Create parent directories if needed (default ``True``).

    Returns
    -------
    Path
        The written file path.
    """
    path = Path(path)
    if makedirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    img.to_filename(str(path))
    return path
