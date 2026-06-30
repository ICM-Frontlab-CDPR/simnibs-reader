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
from typing import TYPE_CHECKING, List

import nibabel as nib
import numpy as np
from nilearn import image, masking


if TYPE_CHECKING:
    from .efield import EField

from ._labels import parse_lut, resolve_tissue_value, _SIMNIBS_LUT
from .stats import compute_stats


# ─────────────────────────────────────────────────────────────────────────
# ROI — the object the user manipulates after extraction
# ─────────────────────────────────────────────────────────────────────────


class ROI:  ## nilearn a un objet ROI aussi !
    """E-field values extracted within a region of interest.
    ...
    """

    def __init__(
        self,
        values: np.ndarray,
        mask_img: nib.Nifti1Image,
        efield: "EField",
        *,
        masked_img: nib.Nifti1Image | None = None,
        cleaned_img: nib.Nifti1Image | None = None,
        is_cleaned: bool = False,
    ) -> None:
        self.values     = values
        self.mask_img   = mask_img
        self.efield     = efield
        self.masked_img = masked_img
        self.cleaned_img = cleaned_img
        self.is_cleaned = is_cleaned

    # -- dunders ----------------------------------------------------------

    def __repr__(self) -> str:
        status = "cleaned" if self.is_cleaned else "raw"
        return f"ROI(n_voxels={self.n_voxels}, status={status})"

    def __len__(self):
        return self.n_voxels

    def __array__(self, dtype=None):
        return self.values.astype(dtype) if dtype else self.values

    def __bool__(self):
        return self.n_voxels > 0

    def __eq__(self, other):
        return np.array_equal(self.values, other.values)

    def __add__(self, other):
        return np.concatenate([self.values, other.values])

    # -- properties -------------------------------------------------------

    @property
    def n_voxels(self) -> int:
        return int(self.values.size)

    @property
    def volume_mm3(self) -> float:
        """Volume of the ROI mask in mm³."""
        voxel_vol = float(np.prod(self.mask_img.header.get_zooms()[:3]))
        return float(self.mask_img.get_fdata().sum() * voxel_vol)

    # -- statistics -------------------------------------------------------

    def stats(self) -> dict[str, float | int]:
        """Descriptive statistics on the extracted values (NaN-aware)."""
        return {
            **compute_stats(self.values),
            "volume_mm3": self.volume_mm3,
            "n_voxels":   self.n_voxels,
        }
    
 

  
    # -- post-processing (private helpers) --------------------------------

    def _smooth(self, fwhm: float) -> nib.Nifti1Image:
        """Return a smoothed copy of the source e-field image."""
        return image.smooth_img(self.efield, fwhm=fwhm)

    def _extract(self, efield_img: nib.Nifti1Image) -> tuple[np.ndarray, nib.Nifti1Image]:
        """Mask an e-field image → (1-D values, volumetric masked image)."""
        values     = masking.apply_mask(efield_img, self.mask_img).astype(np.float64)
        masked_img = masking.unmask(values, self.mask_img)
        return values, masked_img

    def _clean(
        self,
        values: np.ndarray,
        method: str,
        portion: float | None,
    ) -> tuple[np.ndarray, nib.Nifti1Image]:
        """Remove outliers on non-zero voxels → (filtered values, cleaned image)."""

        filtered = values.copy()
        nonzero  = values > 0
        if nonzero.any():
            cleaned_nonzero, _ = self.remove_outliers(
                values[nonzero],
                method=method,
                portion=portion,
            )
            filtered[nonzero] = cleaned_nonzero

        cleaned_img = masking.unmask(filtered, self.mask_img)
        return filtered, cleaned_img

    # -- post-processing (public) -----------------------------------------

    def postprocess(self,smooth_fwhm: float | None = 2.0,
        outlier_method: str = "iqr", portion: float | None = None,) -> "ROI":
        """
        mooth and/or remove outliers.
        Returns a **new** ``ROI`` — the original is never mutated.

        Parameters
        ----------
        smooth_fwhm : float or None. FWHM (mm) for Gaussian smoothing before masking. ``None`` to skip.
        outlier_method : {"iqr", "z"}. Outlier removal strategy.
        portion : float or None. Central portion to keep (e.g. ``0.95``). ``None`` to skip.
        """
        efield_img = (
            self._smooth(smooth_fwhm)
            if smooth_fwhm and smooth_fwhm > 0
            else self.efield
        )
        values, masked_img      = self._extract(efield_img)
        filtered, cleaned_img   = self._clean(values, outlier_method, portion)

        return ROI(
            values=filtered,
            mask_img=self.mask_img,
            efield=self.efield,
            masked_img=masked_img,
            cleaned_img=cleaned_img,
            is_cleaned=True,
        )

    @staticmethod
    def remove_outliers(values, method="iqr", z_thresh=3.5, iqr_factor=1.5,
                        portion=None)-> tuple[np.ndarray, np.ndarray]:

        """Filter outliers on a 1-D vector.

        Parameters
        ----------
        values : np.ndarray
            Input values.
        method : {"iqr", "z"}
            ``"iqr"`` — keep values within ``[Q1 - factor·IQR, Q3 + factor·IQR]``.
            ``"z"``   — keep values with robust |z-score| ≤ *z_thresh*.
        z_thresh : float
            Threshold for the robust z-score method (default 3.5).
        iqr_factor : float
            Multiplier for IQR fences (default 1.5).
        portion : float or None
            If set, additionally trim to the central *portion*
            (e.g. ``0.95`` keeps the 2.5 %–97.5 % range).

        Returns
        -------
        filtered : np.ndarray
            Copy of *values* with outliers set to ``NaN``.
        keep : np.ndarray
            Boolean mask of retained values.
        """
        vals = np.asarray(values, dtype=np.float64)
        keep = np.ones(vals.shape, dtype=bool)

        # Central portion trim
        if portion is not None:
            if not (0.0 < portion <= 1.0):
                raise ValueError("portion must be in (0, 1]")
            lo_q = (1.0 - portion) / 2.0
            hi_q = 1.0 - lo_q
            lo, hi = np.quantile(vals, [lo_q, hi_q])
            keep &= (vals >= lo) & (vals <= hi)

        # IQR or robust z-score
        if method.lower() == "iqr":
            q1, q3 = np.quantile(vals, [0.25, 0.75])
            iqr = q3 - q1
            keep &= (vals >= q1 - iqr_factor * iqr) & (vals <= q3 + iqr_factor * iqr)
        elif method.lower() == "z":
            med = np.median(vals)
            mad = np.median(np.abs(vals - med))
            if mad == 0:
                keep &= np.isfinite(vals)
            else:
                robust_z = 0.6745 * (vals - med) / mad
                keep &= np.abs(robust_z) <= z_thresh
        else:
            raise ValueError(f"method must be 'iqr' or 'z', got '{method}'")

        filtered = vals.copy()
        filtered[~keep] = np.nan
        return filtered, keep

    # -- export  USE LES IO !!! -----------------------------------------------------------

    def save(
        self,
        path: str | Path,
        metrics: list[str] | None = None,
        format: str = "tsv",
    ) -> Path:
        """Export statistics to disk (tsv or csv)."""
        from ..io.export import save_results
        return save_results(self.stats(), path, metrics=metrics, format=format)

    def save_nifti(self, path: str | Path) -> Path:
        """Write ``cleaned_img`` (or ``masked_img``) to a NIfTI file."""
        from ..io.nifti import save_nifti
        img = self.cleaned_img or self.masked_img
        if img is None:
            raise ValueError(
                "No volumetric image to save. Call .postprocess() first, "
                "or use .save() to export stats only."
            )
        return save_nifti(img, path)




  