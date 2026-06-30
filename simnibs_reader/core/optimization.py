"""
optimization.py
---------------
Reader for a SimNIBS **optimization / leadfield** folder.

Expected layout::

    <optiID>/
    ├── *.hdf5                              # leadfield matrix
    ├── simulation_with_optimal_montage/
    │   ├── mni_volumes/
    │   │   ├── *_MNI_magnE.nii.gz
    │   │   └── …
    │   └── subject_volumes/
    │       └── …
    └── *.msh                               # optimized field results
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from ._base import SimNIBSResult
from ..efield.efield import EField


class OptimizationResult(SimNIBSResult):
    """Lazy reader for a SimNIBS optimization / leadfield folder."""

    _kind = "Optimization folder"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        has_hdf5 = bool(self._find("*.hdf5"))
        has_optimal = (self.path / "simulation_with_optimal_montage").is_dir()
        if not has_hdf5 and not has_optimal:
            raise ValueError(
                f"{self.path} does not look like an optimization folder "
                "(no .hdf5 file and no simulation_with_optimal_montage/ directory)."
            )

    # ------------------------------------------------------------------
    # Leadfield (requires optional h5py dependency)
    # ------------------------------------------------------------------

    @cached_property
    def leadfield_path(self) -> Path:
        """Path to the leadfield HDF5 file."""
        return self._find_one("*.hdf5")

    def open_leadfield(self):
        """Open the leadfield HDF5 file (read-only).

        Returns an ``h5py.File`` object.  Caller is responsible for closing.

        Raises
        ------
        ImportError
            If ``h5py`` is not installed.  Install with
            ``pip install simnibs-reader[opti]``.
        """
        try:
            import h5py
        except ImportError as exc:
            raise ImportError(
                "h5py is required to read leadfield files. "
                "Install it with:  pip install simnibs-reader[opti]"
            ) from exc
        return h5py.File(self.leadfield_path, "r")

    # ------------------------------------------------------------------
    # Optimal-montage E-field accessors
    # ------------------------------------------------------------------

    def _opt_dir(self) -> Path:
        d = self.path / "simulation_with_optimal_montage"
        if not d.exists():
            raise FileNotFoundError(
                f"No optimal-montage simulation found in {self.path}"
            )
        return d

    def _find_opt(self, pattern: str) -> Path:
        results = sorted(self._opt_dir().glob(pattern))
        if not results:
            raise FileNotFoundError(
                f"No file matching '{pattern}' in {self._opt_dir()}"
            )
        return results[0]

    @cached_property
    def magnE(self) -> EField:
        """E-field magnitude from optimal montage (MNI space)."""
        return EField(self._find_opt("mni_volumes/*_MNI_magnE.nii.gz"))

    @cached_property
    def magnE_native(self) -> EField:
        """E-field magnitude from optimal montage (subject space)."""
        return EField(self._find_opt("subject_volumes/*_magnE.nii.gz"))

    @cached_property
    def available_fields(self) -> dict[str, list[Path]]:
        """All NIfTI field files from the optimal montage, grouped by space."""
        try:
            opt = self._opt_dir()
        except FileNotFoundError:
            return {"mni": [], "native": []}
        return {
            "mni": sorted((opt / "mni_volumes").glob("*.nii.gz"))
            if (opt / "mni_volumes").exists()
            else [],
            "native": sorted((opt / "subject_volumes").glob("*.nii.gz"))
            if (opt / "subject_volumes").exists()
            else [],
        }
