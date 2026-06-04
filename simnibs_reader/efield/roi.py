"""
roi.py
------
ROI mask creation and e-field value extraction.

Supports three methods for defining an ROI:

1. **From an existing NIfTI mask** — just provide a path.
2. **From MNI/subject coordinates** — builds a sphere on the fly.
3. **From an atlas parcel** — fetches the atlas via nilearn and
   builds a binary mask (Phase 2 — raises ``NotImplementedError`` for now).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import nibabel as nib
import numpy as np
from nilearn import masking, image
from nilearn.image import new_img_like

if TYPE_CHECKING:
    from .accessor import EFieldAccessor

from .stats import compute_stats


# ─────────────────────────────────────────────────────────────────────────
# ROIResult — the object the user manipulates after extraction
# ─────────────────────────────────────────────────────────────────────────


class ROIResult:
    """E-field values extracted within a region of interest.

    Attributes
    ----------
    values : np.ndarray
        1-D array of e-field values inside the ROI.
    mask_img : nib.Nifti1Image
        Binary mask used for extraction.
    efield : EFieldAccessor
        Back-reference to the source e-field.
    """

    def __init__(
        self,
        values: np.ndarray,
        mask_img: nib.Nifti1Image,
        efield: "EFieldAccessor",
    ) -> None:
        self.values = values
        self.mask_img = mask_img
        self.efield = efield

    # -- convenience shortcuts --------------------------------------------

    def stats(self) -> dict[str, float | int]:
        """Descriptive statistics on the extracted values."""
        return compute_stats(self.values)

    def postprocess(
        self,
        smooth_fwhm: float | None = 2.0,
        outlier_method: str = "iqr",
        portion: float | None = None,
    ) -> "CleanedResult":  # noqa: F821
        """Smooth and/or remove outliers.

        Returns
        -------
        CleanedResult
            Object with ``.values``, ``.stats()``, ``.save()``.
        """
        from .postprocess import Preprocessor

        return Preprocessor(
            smooth_fwhm=smooth_fwhm,
            outlier_method=outlier_method,
            portion=portion,
        ).run(self)

    def save(
        self,
        path: str | Path,
        metrics: list[str] | None = None,
        format: str = "tsv",
    ) -> Path:
        """Export statistics to disk.

        Parameters
        ----------
        path : str or Path
            Output file path (extension is added automatically if missing).
        metrics : list of str, optional
            Subset of stat keys to export (default: all).
        format : {"tsv", "csv"}
            Delimiter format.
        """
        from ..io.export import save_results

        return save_results(self.stats(), path, metrics=metrics, format=format)

    @property
    def n_voxels(self) -> int:
        return int(self.values.size)

    def __repr__(self) -> str:
        return (
            f"ROIResult(n_voxels={self.n_voxels}, "
            f"mean={np.nanmean(self.values):.4f})"
        )


# ─────────────────────────────────────────────────────────────────────────
# ROIExtractor — builds the mask then extracts values
# ─────────────────────────────────────────────────────────────────────────


class ROIExtractor:
    """Build an ROI mask and extract e-field values through it.

    Typically not instantiated directly — use
    ``EFieldAccessor.get_roi(...)`` instead.
    """

    def __init__(self, efield: "EFieldAccessor") -> None:
        self._efield = efield

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def extract(
        self,
        mask: str | Path | None = None,
        coords: list[float] | None = None,
        radius: float = 10.0,
        atlas: str | None = None,
        region: str | None = None,
    ) -> ROIResult:
        """Create or load a mask, apply it, return an ``ROIResult``.

        Exactly one of {*mask*, *coords*, *atlas*} must be provided.
        """
        if mask is not None:
            mask_img = self._from_mask(mask)
        elif coords is not None:
            mask_img = self._from_sphere(coords, radius)
        elif atlas is not None and region is not None:
            mask_img = self._from_atlas(atlas, region)
        else:
            raise ValueError(
                "Provide exactly one of: mask=, coords=, or atlas=+region="
            )

        # Resample mask to e-field grid if needed
        if mask_img.shape[:3] != self._efield.shape[:3] or not np.allclose(
            mask_img.affine, self._efield.affine
        ):
            mask_img = image.resample_to_img(
                mask_img, self._efield.img, interpolation="nearest"
            )

        values = masking.apply_mask(self._efield.img, mask_img)
        return ROIResult(values, mask_img, self._efield)

    # ------------------------------------------------------------------
    # Private mask builders
    # ------------------------------------------------------------------

    @staticmethod
    def _from_mask(mask_path: str | Path) -> nib.Nifti1Image:
        """Load an existing binary NIfTI mask."""
        mask_path = Path(mask_path)
        if not mask_path.exists():
            raise FileNotFoundError(f"ROI mask not found: {mask_path}")
        return nib.load(str(mask_path))

    def _from_sphere(
        self, coords: list[float], radius_mm: float
    ) -> nib.Nifti1Image:
        """Build a binary spherical mask centred on world coordinates.

        Parameters
        ----------
        coords : list of 3 floats
            Centre in world (MNI or subject) coordinates [x, y, z].
        radius_mm : float
            Sphere radius in millimetres.
        """
        ref_img = self._efield.img
        affine = ref_img.affine
        shape = ref_img.shape[:3]

        # world → voxel
        mni_h = np.append(coords, 1.0)
        vox_centre = (np.linalg.inv(affine) @ mni_h)[:3]

        # voxel-space radius (isotropic approximation)
        voxel_size = float(np.abs(np.diag(affine)[:3]).mean())
        radius_vox = radius_mm / voxel_size

        ii, jj, kk = np.ogrid[: shape[0], : shape[1], : shape[2]]
        dist_sq = (
            (ii - vox_centre[0]) ** 2
            + (jj - vox_centre[1]) ** 2
            + (kk - vox_centre[2]) ** 2
        )
        data = (dist_sq <= radius_vox**2).astype(np.uint8)
        return new_img_like(ref_img, data, affine=affine)

    @staticmethod
    def _from_atlas(atlas: str, region: str) -> nib.Nifti1Image:
        """Build a mask from an atlas parcel (Phase 2).

        Will support ``'harvard-oxford'``, ``'aal'``, ``'destrieux'``.
        """
        raise NotImplementedError(
            f"Atlas-based ROI ({atlas}/{region}) is not implemented yet — "
            "coming in Phase 2.  Use mask= or coords= for now."
        )

    @staticmethod
    def build_extra_mask(
        inner_mask_path: str | Path,
        outer_mask_path: str | Path,
    ) -> nib.Nifti1Image:
        """Return the extra-ROI mask defined as outer minus inner mask.

        Computes the voxels that belong to the outer mask (e.g. brain mask)
        but *not* to the inner mask (e.g. lesion mask).  Useful for computing
        intra/extra-ROI e-field ratios.

        Parameters
        ----------
        inner_mask_path : str or Path
            Path to the inner binary NIfTI mask (e.g. lesion).
        outer_mask_path : str or Path
            Path to the outer binary NIfTI mask (e.g. whole-brain mask).

        Returns
        -------
        nib.Nifti1Image
            Binary mask representing ``outer_mask - inner_mask``.
        """
        from nilearn.image import math_img

        inner_mask_path = Path(inner_mask_path)
        outer_mask_path = Path(outer_mask_path)

        if not inner_mask_path.exists():
            raise FileNotFoundError(
                f"Inner ROI mask not found: {inner_mask_path}"
            )
        if not outer_mask_path.exists():
            raise FileNotFoundError(
                f"Outer ROI mask not found: {outer_mask_path}"
            )

        inner_img = nib.load(str(inner_mask_path))
        outer_img = nib.load(str(outer_mask_path))

        # Resample inner mask to outer mask space if grids differ
        if inner_img.shape[:3] != outer_img.shape[:3] or not np.allclose(
            inner_img.affine, outer_img.affine
        ):
            inner_img = image.resample_to_img(
                inner_img, outer_img, interpolation="nearest"
            )

        return math_img(
            "np.clip(outer - inner, 0, 1).astype(np.uint8)",
            outer=outer_img,
            inner=inner_img,
        )
