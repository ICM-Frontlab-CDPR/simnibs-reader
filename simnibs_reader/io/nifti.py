"""
nifti.py
--------
Thin wrappers around nibabel for loading and saving NIfTI files.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def load_nifti(path: str | Path) -> tuple[np.ndarray, nib.Nifti1Image]:
    """Load a NIfTI file and return ``(data, img)``.

    Parameters
    ----------
    path : str or Path
        Path to a ``.nii`` or ``.nii.gz`` file.

    Returns
    -------
    data : np.ndarray
        Volume data (float64 by default via nibabel).
    img : nib.Nifti1Image
        Full nibabel image object.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {path}")
    img = nib.load(str(path))
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
