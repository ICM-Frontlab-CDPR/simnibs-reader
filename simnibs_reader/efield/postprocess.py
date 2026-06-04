"""
postprocess.py
--------------
Smoothing and outlier removal on ROI-extracted e-field values.

Re-uses the proven logic from the original pipeline ``_1_preprocessing.py``
but wrapped in a cleaner, stateless API that operates on ``ROIResult``
objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import nibabel as nib
import numpy as np
from nilearn import image, masking

from .stats import compute_stats

if TYPE_CHECKING:
    from .roi import ROIResult


# ─────────────────────────────────────────────────────────────────────────
# CleanedResult — output of post-processing
# ─────────────────────────────────────────────────────────────────────────


class CleanedResult:
    """E-field values after smoothing and/or outlier removal.

    Attributes
    ----------
    values : np.ndarray
        1-D array with outliers replaced by ``NaN``.
    cleaned_img : nib.Nifti1Image
        Volumetric image (values unmasked back into 3-D).
    source : ROIResult
        The ``ROIResult`` this was derived from.
    """

    def __init__(
        self,
        values: np.ndarray,
        cleaned_img: nib.Nifti1Image,
        source: "ROIResult",
    ) -> None:
        self.values = values
        self.cleaned_img = cleaned_img
        self.source = source

    def stats(self) -> dict[str, float | int]:
        """Descriptive statistics (NaN-aware)."""
        return compute_stats(self.values)

    def save(
        self,
        path: str | Path,
        metrics: list[str] | None = None,
        format: str = "tsv",
    ) -> Path:
        """Export statistics to disk.

        See :func:`simnibs_reader.io.export.save_results` for details.
        """
        from ..io.export import save_results

        return save_results(self.stats(), path, metrics=metrics, format=format)

    def save_nifti(self, path: str | Path) -> Path:
        """Write the cleaned volume to a NIfTI file."""
        from ..io.nifti import save_nifti

        return save_nifti(self.cleaned_img, path)

    def __repr__(self) -> str:
        finite = self.values[np.isfinite(self.values)]
        return (
            f"CleanedResult(n_kept={finite.size}, "
            f"mean={np.mean(finite):.4f})"
        )


# ─────────────────────────────────────────────────────────────────────────
# Preprocessor
# ─────────────────────────────────────────────────────────────────────────


class Preprocessor:
    """Smooth and remove outliers from ROI-extracted e-field values.

    Parameters
    ----------
    smooth_fwhm : float or None
        FWHM (mm) for Gaussian smoothing applied *before* masking.
        ``None`` or ``0`` to skip.
    outlier_method : {"iqr", "z"}
        ``"iqr"`` — keep values within ``[Q1 - 1.5·IQR, Q3 + 1.5·IQR]``.
        ``"z"``   — keep values with robust |z-score| ≤ 3.5.
    portion : float or None
        If set, additionally trim to the central *portion*
        (e.g. ``0.95`` keeps the 2.5 %–97.5 % range).
    """

    def __init__(
        self,
        smooth_fwhm: float | None = 2.0,
        outlier_method: str = "iqr",
        portion: float | None = None,
    ) -> None:
        self.smooth_fwhm = smooth_fwhm
        self.outlier_method = outlier_method
        self.portion = portion

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, roi_result: "ROIResult") -> CleanedResult:
        """Run the full preprocessing chain.

        Parameters
        ----------
        roi_result : ROIResult
            Output of ``EFieldAccessor.get_roi(…)`` (or ``ROIExtractor.extract``).

        Returns
        -------
        CleanedResult
        """
        efield_img = roi_result.efield.img
        mask_img = roi_result.mask_img

        # Optional smoothing (applied to the full volume before masking)
        if self.smooth_fwhm and self.smooth_fwhm > 0:
            efield_img = image.smooth_img(efield_img, fwhm=self.smooth_fwhm)

        # Re-extract values after smoothing
        roi_values = masking.apply_mask(efield_img, mask_img).astype(np.float64)

        # Outlier removal (only on non-zero voxels to avoid background bias)
        filtered = roi_values.copy()
        nonzero = roi_values > 0
        if nonzero.any():
            cleaned, _ = self._remove_outliers(
                roi_values[nonzero],
                method=self.outlier_method,
                portion=self.portion,
            )
            filtered[nonzero] = cleaned

        cleaned_img = masking.unmask(filtered, mask_img)
        return CleanedResult(filtered, cleaned_img, source=roi_result, masked_img=masked_img)

    # ------------------------------------------------------------------
    # Outlier removal (static, reusable)
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_outliers(
        values: np.ndarray,
        method: str = "iqr",
        z_thresh: float = 3.5,
        iqr_factor: float = 1.5,
        portion: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Filter outliers on a 1-D vector.

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
