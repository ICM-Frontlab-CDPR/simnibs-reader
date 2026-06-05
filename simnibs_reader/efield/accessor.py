"""
accessor.py
-----------
Lazy-loaded NIfTI e-field accessor.

The NIfTI file is **not** read at instantiation — only when ``.data`` or
``.img`` are first accessed.  This keeps object creation instant even when
pointing at large 4-D vector-field files.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

import nibabel as nib
import numpy as np


class EFieldAccessor:
    """Lazy wrapper around a NIfTI e-field image on disk.

    Parameters
    ----------
    path : str or Path
        Path to the ``.nii.gz`` file.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"NIfTI file not found: {self.path}")

    # ------------------------------------------------------------------
    # Lazy-loaded image
    # ------------------------------------------------------------------

    @cached_property
    def img(self) -> nib.Nifti1Image:
        """Full nibabel image (loaded once, then cached)."""
        return nib.load(str(self.path))

    @cached_property
    def data(self) -> np.ndarray:
        """Volume data as ``float32`` array."""
        return self.img.get_fdata(dtype=np.float32)

    @property
    def affine(self) -> np.ndarray:
        """4 x 4 affine matrix (voxel → world)."""
        return self.img.affine

    @property
    def shape(self) -> tuple[int, ...]:
        """Shape of the data array."""
        return self.img.shape

    # ------------------------------------------------------------------
    # ROI extraction shortcut
    # ------------------------------------------------------------------

    def get_roi(
        self,
        mask: str | Path | None = None,
        coords: list[float] | None = None,
        radius: float = 10.0,
        atlas: str | None = None,
        region: str | list[str] | None = None,
    ) -> "ROIResult":  # noqa: F821 — forward ref resolved at runtime
        """Extract e-field values within a region of interest.

        Three mutually-exclusive methods:

        1. **mask** — path to an existing binary NIfTI mask.
        2. **coords** + **radius** — spherical ROI in MNI/subject space.
        3. **atlas** + **region** — atlas-based parcel mask.

        Returns
        -------
        ROIResult
            Object holding the extracted 1-D values, the mask image,
            and convenience methods (``.stats()``, ``.postprocess()``,
            ``.save()``, ``.save_nifti()``).
        """
        from .roi import ROIExtractor

        return ROIExtractor(self).extract(
            mask=mask, coords=coords, radius=radius, atlas=atlas, region=region,
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"EFieldAccessor('{self.path.name}')"
