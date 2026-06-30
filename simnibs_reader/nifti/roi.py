"""
roi.py
------
ROI value container, post-processing, tissue filtering and export.

An ``ROI`` is produced by :meth:`EField.get_roi` and holds the **already
extracted** 1-D e-field values together with the binary mask and a
back-reference to the source :class:`EField`.  Every transforming method
(``postprocess``, ``filter_tissue``, ``complement``) returns a **new** ``ROI``
— the original is never mutated.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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


class ROI:
    """E-field values extracted within a region of interest.

    Attributes
    ----------
    values : np.ndarray
        1-D array of e-field values inside the ROI (raw or cleaned).
    mask_img : nib.Nifti1Image
        Binary mask used for extraction (on the e-field grid).
    efield : EField
        Back-reference to the source e-field.
    masked_img : nib.Nifti1Image or None
        Volumetric image before outlier removal (set by ``postprocess()``).
    cleaned_img : nib.Nifti1Image or None
        Volumetric image after outlier removal (set by ``postprocess()``).
    is_cleaned : bool
        ``True`` if this ROI went through ``postprocess()``.
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
        self.values      = values
        self.mask_img    = mask_img
        self.efield      = efield
        self.masked_img  = masked_img
        self.cleaned_img = cleaned_img
        self.is_cleaned  = is_cleaned

    # -- dunders ----------------------------------------------------------

    def __repr__(self) -> str:
        status = "cleaned" if self.is_cleaned else "raw"
        return f"ROI(n_voxels={self.n_voxels}, status={status})"

    def __len__(self) -> int:
        return self.n_voxels

    def __array__(self, dtype=None) -> np.ndarray:
        return self.values.astype(dtype) if dtype else self.values

    def __bool__(self) -> bool:
        return self.n_voxels > 0

    def __eq__(self, other) -> bool:
        return isinstance(other, ROI) and np.array_equal(self.values, other.values)

    __hash__ = None  # ROI is mutable-ish / value-compared → not hashable

    def __add__(self, other: "ROI") -> np.ndarray:
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

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    # -- private helpers --------------------------------------------------

    @staticmethod
    def _fdata_3d(img: nib.Nifti1Image) -> np.ndarray:
        """Return ``img`` data squeezed to 3D.

        SimNIBS NIfTI volumes (e-field, ``final_tissues``, tissue labels …)
        often carry a trailing singleton 4th axis, e.g. ``(X, Y, Z, 1)``.
        Squeezing keeps boolean mask operations broadcast-safe.
        """
        data = np.squeeze(np.asarray(img.get_fdata()))
        if data.ndim != 3:
            raise ValueError(
                f"Expected a 3D volume after squeeze, got shape {img.shape}."
            )
        return data

    def _smooth(self, fwhm: float) -> nib.Nifti1Image:
        """Return a smoothed copy of the source e-field image."""
        return image.smooth_img(self.efield.img, fwhm=fwhm)   # .img, pas EField

    def _extract(self, efield_img: nib.Nifti1Image) -> tuple[np.ndarray, nib.Nifti1Image]:
        """Mask an e-field image → (1-D values, volumetric masked image)."""
        # apply_mask on a (X,Y,Z,1) image returns (1, N) → squeeze to (N,)
        values     = np.squeeze(masking.apply_mask(efield_img, self.mask_img)).astype(np.float64)
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
                values[nonzero], method=method, portion=portion,
            )
            filtered[nonzero] = cleaned_nonzero

        cleaned_img = masking.unmask(filtered, self.mask_img)
        return filtered, cleaned_img

    # -- public -----------------------------------------------------------

    def postprocess(
        self,
        smooth_fwhm: float | None = 2.0,
        outlier_method: str = "iqr",
        portion: float | None = None,
    ) -> "ROI":
        """Smooth and/or remove outliers.

        Returns a **new** ``ROI`` — the original is never mutated.

        Parameters
        ----------
        smooth_fwhm : float or None
            FWHM (mm) for Gaussian smoothing applied *before* masking.
            ``None`` or ``0`` to skip.
        outlier_method : {"iqr", "z"}
            Outlier removal strategy.
        portion : float or None
            Central portion to keep (e.g. ``0.95``). ``None`` to skip.
        """
        efield_img = (
            self._smooth(smooth_fwhm)
            if smooth_fwhm and smooth_fwhm > 0
            else self.efield.img                              # .img, pas EField
        )
        values, masked_img    = self._extract(efield_img)
        filtered, cleaned_img = self._clean(values, outlier_method, portion)

        return ROI(
            values=filtered,
            mask_img=self.mask_img,
            efield=self.efield,
            masked_img=masked_img,
            cleaned_img=cleaned_img,
            is_cleaned=True,
        )

    @staticmethod
    def remove_outliers(
        values: np.ndarray,
        method: str = "iqr",
        z_thresh: float = 3.5,
        iqr_factor: float = 1.5,
        portion: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
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

    # ------------------------------------------------------------------
    # Extra-ROI (complement)
    # ------------------------------------------------------------------

    def complement(self, brain_mask: str | Path | None = None) -> "ROI":
        """E-field values *outside* this ROI but *inside* the brain.

        Returns a **new** ``ROI`` — the original is never mutated.

        Parameters
        ----------
        brain_mask : str, Path, or None
            Path to a binary brain mask NIfTI.  When ``None``, resolved
            automatically from the attached segmentation's ``final_tissues``
            (any tissue > 0 = brain).

        Raises
        ------
        ValueError
            If *brain_mask* is ``None`` and no segmentation is attached.
        """
        brain_img = self._resolve_brain_mask(brain_mask)
        brain_img = image.resample_to_img(
            brain_img, self.mask_img, interpolation="nearest"
        )
        # squeeze both → 3D, sinon (X,Y,Z,1) & (X,Y,Z) ne broadcast pas
        extra_data = (
            self._fdata_3d(brain_img).astype(bool)
            & ~self._fdata_3d(self.mask_img).astype(bool)
        ).astype(np.uint8)
        extra_mask = nib.Nifti1Image(extra_data, self.mask_img.affine)

        values = np.squeeze(masking.apply_mask(self.efield.img, extra_mask))   # .img !
        return ROI(values=values, mask_img=extra_mask, efield=self.efield)

    def _resolve_brain_mask(self, brain_mask: str | Path | None) -> nib.Nifti1Image:
        """Return a binary brain mask image.

        Priority:
        1. Explicit *brain_mask* path.
        2. ``segmentation.final_tissues`` binarised (value > 0).
        """
        if brain_mask is not None:
            return nib.load(str(brain_mask))

        sim = getattr(self.efield, "simulation", None)
        seg = getattr(sim, "segmentation", None) if sim is not None else None
        if seg is not None:
            tissues_nii = nib.load(str(seg.final_tissues))
            data = (self._fdata_3d(tissues_nii) > 0).astype(np.uint8)   # squeeze → 3D
            return nib.Nifti1Image(data, tissues_nii.affine)

        raise ValueError(
            "brain_mask is required when no SegmentationResult is attached.\n"
            "Either pass brain_mask= explicitly, or call "
            "sim.set_segmentation(seg) beforehand."
        )

    # ------------------------------------------------------------------
    # Tissue filtering
    # ------------------------------------------------------------------

    def filter_tissue(
        self,
        tissue: str,
        label_img: str | Path | None = None,
        lut: str | Path | None = None,
    ) -> "ROI":
        """Restrict the ROI to a specific tissue type.

        Returns a **new** ``ROI`` — the original is never mutated.

        ``label_img`` can be omitted when a ``SegmentationResult`` has been
        attached to the parent simulation via ``set_segmentation``; the path is
        then resolved automatically from ``segmentation.tissue_labeling_upsampled``.

        Parameters
        ----------
        tissue : str
            Tissue name (e.g. ``"Gray-Matter"``). Case-insensitive.
        label_img : str, Path, or None
            Path to the SimNIBS tissue labeling NIfTI. ``None`` → auto-resolve.
        lut : str, Path, or None
            Path to ``*_LUT.txt``. If omitted, the standard SimNIBS mapping is used.
        """
        resolved_label_img = self._resolve_label_img(label_img)
        tissue_mask = self._build_tissue_mask(resolved_label_img, tissue, lut)
        new_mask    = self._intersect_masks(self.mask_img, tissue_mask)

        values = np.squeeze(masking.apply_mask(self.efield.img, new_mask))     # .img !
        return ROI(values=values, mask_img=new_mask, efield=self.efield)

    def _resolve_label_img(self, label_img: str | Path | None) -> Path:
        """Return a concrete path to the tissue labeling NIfTI.

        Priority:
        1. Explicit *label_img* argument.
        2. ``self.efield.simulation.segmentation.tissue_labeling_upsampled``.
        """
        if label_img is not None:
            return Path(label_img)

        sim = getattr(self.efield, "simulation", None)
        seg = getattr(sim, "segmentation", None) if sim is not None else None
        if seg is not None:
            return seg.tissue_labeling_upsampled

        raise ValueError(
            "label_img is required when no SegmentationResult is attached.\n"
            "Either pass label_img= explicitly, or call "
            "sim.set_segmentation(seg) beforehand."
        )

    def _build_tissue_mask(
        self,
        label_img_path: str | Path,
        tissue: str,
        lut_path: str | Path | None,
    ) -> nib.Nifti1Image:
        """Build a binary mask for a single tissue type."""
        label_nii   = nib.load(str(label_img_path))
        label_array = np.round(self._fdata_3d(label_nii)).astype(int)   # squeeze → 3D

        effective_lut = parse_lut(lut_path) if lut_path else _SIMNIBS_LUT
        tissue_val    = resolve_tissue_value(tissue, effective_lut)

        data = (label_array == tissue_val).astype(np.uint8)
        return nib.Nifti1Image(data, label_nii.affine)

    @staticmethod
    def _intersect_masks(
        mask_a: nib.Nifti1Image,
        mask_b: nib.Nifti1Image,
    ) -> nib.Nifti1Image:
        """Binary intersection of two masks (mask_b resampled onto mask_a)."""
        mask_b = image.resample_to_img(mask_b, mask_a, interpolation="nearest")
        combined = (
            ROI._fdata_3d(mask_a).astype(bool)
            & ROI._fdata_3d(mask_b).astype(bool)
        ).astype(np.uint8)
        return nib.Nifti1Image(combined, mask_a.affine)

    # ------------------------------------------------------------------
    # Export  (delegates to io/)
    # ------------------------------------------------------------------

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