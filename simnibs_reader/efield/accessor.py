from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import nibabel as nib
import numpy as np

if TYPE_CHECKING:
    from ..core.simulation import SimulationResult


class EField(nib.Nifti1Image):
    """E-field NIfTI image with simulation-aware extra methods.

    Inherits fully from ``nib.Nifti1Image`` — compatible with nibabel,
    nilearn, and any NiftiLike duck-typing check out of the box.
    """

    def __init__(
        self,
        path: str | Path,
        simulation: "SimulationResult | None" = None,
    ) -> None:
        if not Path(path).exists():
            raise FileNotFoundError(f"NIfTI file not found: {path}")

        self.path = Path(path)
        self.simulation = simulation

        _img = nib.load(str(self.path))          # memmap → pas chargé en RAM
        super().__init__(_img.dataobj, _img.affine, _img.header)

    # affine, shape, header, get_fdata() → tous hérités ✅
    # Pas besoin de img, data, ni de propriétés déléguées

    def get_roi(
        self,
        mask: str | Path | None = None,
        coords: list[float] | None = None,
        radius: float = 10.0,
        atlas: str | None = None,
        region: str | list[str] | None = None,
    ) -> "ROI":  # noqa: F821
        from .roi import ROIExtractor
        return ROIExtractor(self).extract(
            mask=mask, coords=coords, radius=radius,
            atlas=atlas, region=region,
        )

    def __repr__(self) -> str:
        return f"EField('{self.path.name}')"
    
    
    
      def extract(
        self,
        mask: str | Path | None = None,
        coords: list[float] | None = None,
        radius: float = 10.0,
        atlas: str | None = None,
        region: str | list[str] | None = None,
    ) -> ROI:
        """Create or load a mask, apply it, return an ``ROI``.

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
        mask_img = resample_to_ref(mask_img, self._efield, interpolation="nearest")

        values = masking.apply_mask(self._efield, mask_img)
        return ROI(values, mask_img, self._efield)

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
        ref_img = self._efield
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

    
    
  # -- extra-ROI (complement) -------------------------------------------

    def complement(
        self,
        brain_mask: str | Path | None = None,
    ) -> "ROI":
        """E-field values *outside* this ROI but *inside* the brain.

        Returns a **new** ``ROI`` — the original is never mutated.

        Parameters
        ----------
        brain_mask : str, Path, or None
            Path to a binary brain mask NIfTI.  When ``None``, resolved
            automatically from the attached segmentation's
            ``final_tissues`` (any tissue > 0 = brain).

        Raises
        ------
        ValueError
            If *brain_mask* is ``None`` and no segmentation is attached.
        """
        brain_img = self._resolve_brain_mask(brain_mask)
        brain_img = resample_to_ref(brain_img, self.mask_img, interpolation="nearest")

        extra_data = (
            brain_img.get_fdata().astype(bool)
            & ~self.mask_img.get_fdata().astype(bool)
        ).astype(np.uint8)
        extra_mask = nib.Nifti1Image(extra_data, self.mask_img.affine)

        values = masking.apply_mask(self.efield, extra_mask)
        return ROI(values=values, mask_img=extra_mask, efield=self.efield)

    def _resolve_brain_mask(
        self, brain_mask: str | Path | None
    ) -> nib.Nifti1Image:
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
            data = (tissues_nii.get_fdata() > 0).astype(np.uint8)
            return nib.Nifti1Image(data, tissues_nii.affine)

        raise ValueError(
            "brain_mask is required when no SegmentationResult is attached.\n"
            "Either pass brain_mask= explicitly, or call "
            "sim.set_segmentation(seg) beforehand."
        )



   # -- tissue filtering -------------------------------------------------
    def filter_tissue(self,tissue: str,label_img: str | Path | None = None,
        lut: str | Path | None = None,) -> "ROI":
        """Restrict the ROI to a specific tissue type.

        Returns a **new** ``ROI`` — the original is never mutated.

        ``label_img`` can be omitted when a
        :class:`~simnibs_reader.core.segmentation.SegmentationResult` has been
        attached to the parent simulation via
        :meth:`~simnibs_reader.core.simulation.SimulationResult.set_segmentation`;
        the path is then resolved automatically from
        ``simulation.segmentation.tissue_labeling_upsampled``.

        Parameters
        ----------
        tissue : str
            Tissue name (e.g. ``"Gray-Matter"``, ``"White-Matter"``).
            Case-insensitive.
        label_img : str, Path, or None
            Path to the SimNIBS tissue labeling NIfTI.  When ``None``, the
            path is resolved automatically from the attached segmentation.
        lut : str, Path, or None
            Path to ``*_LUT.txt``. If omitted, the standard SimNIBS
            mapping is used.

        Raises
        ------
        ValueError
            If *label_img* is ``None`` and no segmentation is attached to the
            parent simulation.
        """
        resolved_label_img = self._resolve_label_img(label_img)
        tissue_mask = self._build_tissue_mask(resolved_label_img, tissue, lut)
        new_mask = self._intersect_masks(self.mask_img, tissue_mask)

        values = masking.apply_mask(self.efield, new_mask)

        return ROI(
            values=values,
            mask_img=new_mask,
            efield=self.efield,
        )

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
        label_array = np.round(label_nii.get_fdata()).astype(int)

        effective_lut = parse_lut(lut_path) if lut_path else _SIMNIBS_LUT
        tissue_val = resolve_tissue_value(tissue, effective_lut)

        data = (label_array == tissue_val).astype(np.uint8)
        return nib.Nifti1Image(data, label_nii.affine)

    @staticmethod
    def _intersect_masks(
        mask_a: nib.Nifti1Image,
        mask_b: nib.Nifti1Image,
    ) -> nib.Nifti1Image:
        """Binary intersection of two masks (resampled to same grid)."""
        mask_b = resample_to_ref(mask_b, mask_a, interpolation="nearest")
        combined = (
            mask_a.get_fdata().astype(bool)
            & mask_b.get_fdata().astype(bool)
        ).astype(np.uint8)
        return nib.Nifti1Image(combined, mask_a.affine)

    
    
    # pour les autres types de fichiers aussi ?