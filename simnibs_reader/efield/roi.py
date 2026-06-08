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
from nilearn.image import new_img_like

if TYPE_CHECKING:
    from .accessor import EFieldAccessor

from ..io.nifti import load_nifti, resample_to_ref
from .stats import compute_stats


# ─────────────────────────────────────────────────────────────────────────
# ROIResult — the object the user manipulates after extraction
# ─────────────────────────────────────────────────────────────────────────


class ROIResult:
    """E-field values extracted within a region of interest.
    ...
    """

    def __init__(
        self,
        values: np.ndarray,
        mask_img: nib.Nifti1Image,
        efield: "EFieldAccessor",
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
        return f"ROIResult(n_voxels={self.n_voxels}, status={status})"

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
        return image.smooth_img(self.efield.img, fwhm=fwhm)

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
        from .postprocess import remove_outliers

        filtered = values.copy()
        nonzero  = values > 0
        if nonzero.any():
            cleaned_nonzero, _ = remove_outliers(
                values[nonzero],
                method=method,
                portion=portion,
            )
            filtered[nonzero] = cleaned_nonzero

        cleaned_img = masking.unmask(filtered, self.mask_img)
        return filtered, cleaned_img

    # -- post-processing (public) -----------------------------------------

    def postprocess(
        self,
        smooth_fwhm: float | None = 2.0,
        outlier_method: str = "iqr",
        portion: float | None = None,
    ) -> "ROIResult":
        """Smooth and/or remove outliers.

        Returns a **new** ``ROIResult`` — the original is never mutated.

        Parameters
        ----------
        smooth_fwhm : float or None
            FWHM (mm) for Gaussian smoothing before masking. ``None`` to skip.
        outlier_method : {"iqr", "z"}
            Outlier removal strategy.
        portion : float or None
            Central portion to keep (e.g. ``0.95``). ``None`` to skip.
        """
        efield_img = (
            self._smooth(smooth_fwhm)
            if smooth_fwhm and smooth_fwhm > 0
            else self.efield.img
        )
        values, masked_img      = self._extract(efield_img)
        filtered, cleaned_img   = self._clean(values, outlier_method, portion)

        return ROIResult(
            values=filtered,
            mask_img=self.mask_img,
            efield=self.efield,
            masked_img=masked_img,
            cleaned_img=cleaned_img,
            is_cleaned=True,
        )

    # -- export -----------------------------------------------------------

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
        region: str | list[str] | None = None,
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
        mask_img = resample_to_ref(mask_img, self._efield.img, interpolation="nearest")

        values = masking.apply_mask(self._efield.img, mask_img)
        return ROIResult(values, mask_img, self._efield)

    # ------------------------------------------------------------------
    # Private mask builders
    # ------------------------------------------------------------------

    @staticmethod
    def _from_mask(mask_path: str | Path) -> nib.Nifti1Image:
        """Load an existing binary NIfTI mask."""
        _, img = load_nifti(mask_path)
        return img

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
    def _from_atlas(
        atlas: str,
        region: str | List[str],
    ) -> nib.Nifti1Image:
        """Build a binary mask from one or more atlas parcels.

        The mask is returned in the native atlas space; ``extract()`` then
        resamples it to the e-field grid via ``resample_to_ref``.

        Parameters
        ----------
        atlas : str
            One of ``'harvard-oxford'``, ``'aal'``, ``'destrieux'``.
        region : str or list of str
            One or more parcel labels whose union forms the mask.

        Returns
        -------
        nib.Nifti1Image
            Binary mask in atlas voxel space.
        """
        import urllib3
        from requests.adapters import HTTPAdapter
        from nilearn import datasets as nl_datasets

        if isinstance(region, str):
            region = [region]

        _FETCHERS = {
            "harvard-oxford": lambda: nl_datasets.fetch_atlas_harvard_oxford(
                "cort-maxprob-thr25-1mm"
            ),
            "aal": lambda: nl_datasets.fetch_atlas_aal(),
            "destrieux": lambda: nl_datasets.fetch_atlas_destrieux_2009(),
        }
        if atlas not in _FETCHERS:
            raise ValueError(
                f"Atlas '{atlas}' not supported. "
                f"Available: {list(_FETCHERS)}"
            )

        # Disable SSL verification for atlas downloads (macOS cert issue)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _orig_send = HTTPAdapter.send
        HTTPAdapter.send = lambda self, *a, **kw: _orig_send(
            self, *a, **{**kw, "verify": False}
        )
        try:
            atlas_data = _FETCHERS[atlas]()
        finally:
            HTTPAdapter.send = _orig_send

        # Load atlas image
        maps = atlas_data.maps
        atlas_img = maps if isinstance(maps, nib.Nifti1Image) else nib.load(maps)
        atlas_array = atlas_img.get_fdata()
        raw_labels = list(atlas_data.labels)

        # AAL provides a separate `indices` list; other atlases use positional indices
        if hasattr(atlas_data, "indices"):
            label_map: dict[str, int] = {
                str(name): int(idx)
                for name, idx in zip(raw_labels, atlas_data.indices)
            }
        else:
            label_map = {str(name): i for i, name in enumerate(raw_labels)}

        mask_data = np.zeros(atlas_array.shape[:3], dtype=np.uint8)
        for region_name in region:
            if region_name not in label_map:
                # Case-insensitive fallback
                matches = [
                    k for k in label_map if k.lower() == region_name.lower()
                ]
                if not matches:
                    raise ValueError(
                        f"Region '{region_name}' not found in atlas '{atlas}'. "
                        f"First available labels: {list(label_map)[:10]}"
                    )
                region_name = matches[0]
            mask_data[
                np.round(atlas_array).astype(int) == label_map[region_name]
            ] = 1

        return nib.Nifti1Image(mask_data, atlas_img.affine)

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

        _, inner_img = load_nifti(inner_mask_path)
        _, outer_img = load_nifti(outer_mask_path)

        # Resample inner mask to outer mask space if grids differ
        inner_img = resample_to_ref(inner_img, outer_img, interpolation="nearest")

        return math_img(
            "np.clip(outer - inner, 0, 1).astype(np.uint8)",
            outer=outer_img,
            inner=inner_img,
        )
