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


def resample_to_ref(
    img: str | Path | nib.Nifti1Image,
    ref: str | Path | nib.Nifti1Image,
    interpolation: str = "continuous",
) -> nib.Nifti1Image:
    """Resample any NIfTI image to match the voxel grid of a reference image.

    This is the general-purpose resampling function used to ensure that any
    loaded NIfTI (e-field maps, masks, anatomical volumes, etc.) lives on the
    same voxel grid as the SimNIBS reference image before any voxel-wise
    operation is performed.
    Parameters
    ----------
    img : str, Path, or nib.Nifti1Image
        Image to resample.
    ref : str, Path, or nib.Nifti1Image
        Reference image that defines the target voxel grid (e.g. a SimNIBS
        e-field volume or the T1 used during meshing).
    interpolation : str
        Interpolation strategy passed to :func:`nilearn.image.resample_to_img`.
        Use ``"nearest"`` for label / binary images and ``"continuous"``
        (default) for scalar fields such as e-field magnitudes.

    Returns
    -------
    nib.Nifti1Image
        Resampled image on the reference grid.

    Examples
    --------
    >>> from simnibs_reader.io.nifti import resample_to_ref
    >>> import simnibs_reader as snr
    >>> sim   = snr.simulation('simu/')
    >>> seg   = snr.segmentation('m2m_sub01/')
    >>> # align an e-field map coming from a different grid onto the T1 grid
    >>> efield_aligned = resample_to_ref(sim.magnE_native.img, seg.t1)
    >>> # align a binary mask onto the e-field grid
    >>> mask_aligned = resample_to_ref('M1_lh_fs.nii.gz', sim.magnE_native.img,
    ...                                interpolation='nearest')
    """
    from nilearn import image as nil_image

    def _load(src):
        if isinstance(src, nib.spatialimages.SpatialImage):
            return src
        p = Path(src)
        if not p.exists():
            raise FileNotFoundError(f"NIfTI file not found: {p}")
        return nib.load(str(p))

    src_img = _load(img)
    ref_img = _load(ref)

    # Already on the same grid — nothing to do
    if (
        src_img.shape[:3] == ref_img.shape[:3]
        and np.allclose(src_img.affine, ref_img.affine)
    ):
        return src_img

    return nil_image.resample_to_img(src_img, ref_img, interpolation=interpolation)




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
