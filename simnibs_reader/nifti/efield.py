from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import nibabel as nib
import numpy as np
from nilearn.image import resample_to_img, new_img_like

if TYPE_CHECKING:
    from ..core.simulation import SimulationResult


class EField:
    """E-field NIfTI image with simulation-aware extra methods.

    Wraps a ``nib.Nifti1Image`` — pass ``efield.img`` or
    ``str(efield.path)`` to any nibabel / nilearn function.
    """

    def __init__(
        self,
        path: str | Path,
        simulation: "SimulationResult | None" = None,
    ) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"NIfTI file not found: {self.path}")
        self.simulation = simulation
        self._img: nib.Nifti1Image = nib.load(str(self.path))  # memmap → pas chargé en RAM

    # ── Accès au Nifti1Image sous-jacent ─────────────────────────

    @property
    def img(self) -> nib.Nifti1Image:
        """Le vrai ``Nifti1Image`` — à passer à nilearn/nibabel."""
        return self._img

    # ── Délégation des attributs courants ────────────────────────

    @property
    def affine(self) -> np.ndarray:
        return self._img.affine

    @property
    def header(self):
        return self._img.header

    @property
    def shape(self):
        return self._img.shape

    @property
    def data(self) -> np.ndarray:
        """Volume data as ``float32`` array (lu paresseusement par nibabel)."""
        return self._img.get_fdata(dtype=np.float32)

    def get_fdata(self, **kwargs) -> np.ndarray:
        return self._img.get_fdata(**kwargs)

    def __repr__(self) -> str:
        return f"EField('{self.path.name}')"

    # ------------------------------------------------------------------
    # ROI extraction
    # ------------------------------------------------------------------

    def get_roi(
        self,
        *,
        mask: str | Path | None = None,
        coords: list[float] | None = None,
        radius: float = 10.0,
        atlas: str | None = None,
        region: str | list[str] | None = None,
    ) -> "ROI":  # noqa: F821 — forward ref résolu à l'exécution
        """Extract e-field values within a region of interest.

        Exactly one source must be given:
          - ``mask=``             : path to a binary NIfTI mask
          - ``coords=`` (+radius) : spherical ROI in the e-field's own space
          - ``atlas=`` (+region)  : atlas-based parcel
        """
        from .roi import ROI
        from nilearn import masking

        sources = [mask is not None, coords is not None, atlas is not None]
        if sum(sources) != 1:
            raise ValueError(
                "Provide exactly one ROI source: `mask=`, `coords=` (+radius), "
                f"or `atlas=` (+region). Got {sum(sources)}."
            )

        if mask is not None:
            mask_img = self._from_mask(mask)
        elif coords is not None:
            mask_img = self._from_sphere(coords, radius)        # radius → radius_mm (positionnel)
        else:
            if region is None:
                raise ValueError("`atlas=` requires `region=`.")
            mask_img = self._from_atlas(atlas, region)

        # cible = niimg, pas EField
        mask_img = resample_to_img(mask_img, self.img, interpolation="nearest")

        # extraction 1-D → ROI « modèle B » (values, mask_img, efield)
        # squeeze : apply_mask sur un volume (X,Y,Z,1) renvoie (1, N) → (N,)
        values = np.squeeze(masking.apply_mask(self.img, mask_img)).astype(np.float64)
        return ROI(values=values, mask_img=mask_img, efield=self)

    # ------------------------------------------------------------------
    # Private mask builders
    # ------------------------------------------------------------------

    @staticmethod
    def _from_mask(mask_path: str | Path) -> nib.Nifti1Image:
        """Load an existing binary NIfTI mask."""
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
        ref_img = self.img
        affine = ref_img.affine
        shape = ref_img.shape[:3]

        # world → voxel
        centre_h = np.append(coords, 1.0)
        vox_centre = (np.linalg.inv(affine) @ centre_h)[:3]

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
        region: str | list[str],
    ) -> nib.Nifti1Image:
        """Build a binary mask from one or more atlas parcels.

        The mask is returned in the native atlas space; ``get_roi`` then
        resamples it to the e-field grid via ``resample_to_img``.

        Parameters
        ----------
        atlas : str
            One of ``'harvard-oxford'``, ``'aal'``, ``'destrieux'``.
        region : str or list of str
            One or more parcel labels whose union forms the mask.
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
                f"Atlas '{atlas}' not supported. Available: {list(_FETCHERS)}"
            )

        # Disable SSL verification for atlas downloads (self-signed / macOS cert issue)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _orig_send = HTTPAdapter.send
        HTTPAdapter.send = lambda self, *a, **kw: _orig_send(
            self, *a, **{**kw, "verify": False}
        )
        try:
            atlas_data = _FETCHERS[atlas]()
        finally:
            HTTPAdapter.send = _orig_send

        maps = atlas_data.maps
        atlas_img = maps if isinstance(maps, nib.Nifti1Image) else nib.load(maps)
        atlas_array = atlas_img.get_fdata()
        raw_labels = list(atlas_data.labels)

        # AAL fournit une liste `indices` séparée ; les autres atlas utilisent l'indice positionnel
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
                matches = [k for k in label_map if k.lower() == region_name.lower()]
                if not matches:
                    raise ValueError(
                        f"Region '{region_name}' not found in atlas '{atlas}'. "
                        f"First available labels: {list(label_map)[:10]}"
                    )
                region_name = matches[0]
            mask_data[np.round(atlas_array).astype(int) == label_map[region_name]] = 1

        return nib.Nifti1Image(mask_data, atlas_img.affine)