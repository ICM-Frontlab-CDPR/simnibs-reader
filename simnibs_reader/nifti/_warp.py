"""
MNI ↔ subject-space warping.

SimNIBS ships a non-linear deformation field per subject
(``m2m_<sub>/toMNI/Conform2MNI_nonl.nii.gz``). It is defined on the *subject*
voxel grid, and each voxel stores the MNI coordinate that voxel maps to.

That layout makes subject → MNI a direct lookup, and MNI → subject a nearest
neighbour search in the stored coordinates. Both directions are needed: the
first to warp a mask built in MNI space onto the subject grid, the second to
place a target given in MNI coordinates.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import map_coordinates

__all__ = [
    "load_warp",
    "mni_to_native_coords",
    "warp_mni_mask_to_native",
]


@lru_cache(maxsize=8)
def _load_warp_cached(path_str: str) -> tuple[nib.Nifti1Image, np.ndarray]:
    warp_img = nib.load(path_str)
    warp_coords = np.squeeze(warp_img.get_fdata()).reshape(-1, 3)
    return warp_img, warp_coords


def load_warp(warp_path: str | Path) -> tuple[nib.Nifti1Image, np.ndarray]:
    """Load a SimNIBS deformation field.

    Parameters
    ----------
    warp_path : str or Path
        Path to ``Conform2MNI_nonl.nii.gz``.

    Returns
    -------
    warp_img : nib.Nifti1Image
        The deformation field, on the subject voxel grid.
    warp_coords : np.ndarray
        Shape ``(N, 3)``: the MNI coordinate of every subject voxel, flattened.

    Notes
    -----
    Results are cached per path — the field is large and a cohort run touches
    the same subject many times.
    """
    return _load_warp_cached(str(warp_path))


def mni_to_native_coords(
    mni_xyz: list[float] | np.ndarray,
    warp_img: nib.Nifti1Image,
    warp_coords: np.ndarray,
) -> list[float]:
    """Nearest subject-space point (in mm) to an MNI target.

    Parameters
    ----------
    mni_xyz : sequence of 3 floats
        Target in MNI world coordinates.
    warp_img, warp_coords
        As returned by :func:`load_warp`.

    Returns
    -------
    list of 3 floats
        The subject-space world coordinate closest to *mni_xyz*.
    """
    dist = np.sum((warp_coords - np.asarray(mni_xyz, dtype=float)) ** 2, axis=1)
    closest_vox = np.unravel_index(int(np.argmin(dist)), warp_img.shape[:3])
    return list(nib.affines.apply_affine(warp_img.affine, closest_vox).round(1))


def warp_mni_mask_to_native(
    mask_mni: nib.Nifti1Image,
    warp_img: nib.Nifti1Image,
    warp_coords: np.ndarray,
) -> nib.Nifti1Image:
    """Resample a binary mask defined in MNI space onto the subject grid.

    Parameters
    ----------
    mask_mni : nib.Nifti1Image
        Binary mask in MNI space.
    warp_img, warp_coords
        As returned by :func:`load_warp`.

    Returns
    -------
    nib.Nifti1Image
        The mask on the subject voxel grid.

    Notes
    -----
    Nearest-neighbour interpolation (``order=0``) — the mask is binary and must
    stay binary.
    """
    inv_aff = np.linalg.inv(mask_mni.affine)
    vox = nib.affines.apply_affine(inv_aff, warp_coords).T  # (3, N) MNI voxel idx
    warped = map_coordinates(mask_mni.get_fdata(), vox, order=0, cval=0)
    data = warped.reshape(warp_img.shape[:3]).astype(np.uint8)
    return nib.Nifti1Image(data, warp_img.affine)
