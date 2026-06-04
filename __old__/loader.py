"""
loader.py
------------------
Folder reader classes for the three main SimNIBS output directories:
  - M2MFolder     : head model folder (m2m_<subID>/)
  - SimuFolder    : simulation results folder
  - OptiFolder    : optimization / leadfield folder

Design principles:
  - Lazy loading via @cached_property (no disk I/O at instantiation)
  - Fail-fast validation on __init__
  - Loaders return raw objects (Msh, Path, dict) — no analysis logic here
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

import simnibs


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class SimNIBSFolder:
    """Abstract base for all SimNIBS folder types."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Folder not found: {self.path}")
        self._validate()

    def _validate(self):
        """Subclasses must implement: check that the folder has the expected structure."""
        raise NotImplementedError

    # -- Internal helpers ----------------------------------------------------

    def _find(self, pattern: str) -> list[Path]:
        """Glob for files matching pattern under self.path (sorted)."""
        return sorted(self.path.glob(pattern))

    def _find_one(self, pattern: str) -> Path:
        """Return the first match or raise FileNotFoundError."""
        results = self._find(pattern)
        if not results:
            raise FileNotFoundError(f"No file matching '{pattern}' in {self.path}")
        return results[0]


# ---------------------------------------------------------------------------
# M2M folder  (m2m_<subID>/)
# ---------------------------------------------------------------------------

class M2MFolder(SimNIBSFolder):
    """
    Reader for a SimNIBS head model folder (output of charm/headreco).

    Expected layout:
        m2m_<subID>/
        ├── <subID>.msh
        ├── T1fs_conform.nii.gz
        └── surfaces/
            ├── lh.central.gii
            └── rh.central.gii
            └── ...
    """

    def _validate(self):
        if not self._find("*.msh"):
            raise ValueError(f"{self.path} does not look like a m2m folder (no .msh found)")

    @cached_property
    def subject_id(self) -> str:
        """Extract subject ID from folder name (e.g. 'm2m_sub01' -> 'sub01')."""
        return self.path.name.removeprefix("m2m_")

    @cached_property
    def mesh(self):
        """Main head mesh (.msh), used for FEM simulations."""
        fn = self._find_one(f"{self.subject_id}.msh")
        return simnibs.msh.read_msh(str(fn))

    @cached_property
    def t1(self) -> Path:
        """Conformed T1 NIfTI, defines the subject coordinate space."""
        return self._find_one("T1fs_conform.nii.gz")

    @cached_property
    def surfaces(self) -> dict[str, Path]:
        """
        Cortical surface files (GIFTI), keyed by stem name.
        e.g. {'lh.central': Path(...), 'rh.central': Path(...)}
        """
        return {p.stem: p for p in self._find("surfaces/*.gii")}


# ---------------------------------------------------------------------------
# Simulation results folder
# ---------------------------------------------------------------------------

class SimuFolder(SimNIBSFolder):
    """
    Reader for a SimNIBS simulation output folder.

    Expected layout:
        <simID>/
        ├── <simID>.msh               # volumetric mesh with E, J fields
        ├── <simID>_scalar.msh        # scalar fields (normE, normJ ...)
        ├── fields_summary.txt
        └── subject_overlays/
            └── *_central.msh         # fields mapped to cortical surface
    """

    def _validate(self):
        if not self._find("*.msh"):
            raise ValueError(f"{self.path} does not look like a simulation folder (no .msh found)")

    @cached_property
    def sim_id(self) -> str:
        """
        Infer simulation ID from the scalar mesh filename.
        e.g. 'sub01_TDCS_1_scalar.msh' -> 'sub01_TDCS_1'
        """
        fn = self._find_one("*_scalar.msh")
        return fn.stem.removesuffix("_scalar")

    @cached_property
    def mesh_volume(self):
        """
        Full volumetric mesh with vector fields (E, J) defined per element.
        Use this for tissue-specific extraction.
        """
        fn = self._find_one(f"{self.sim_id}.msh")
        return simnibs.msh.read_msh(str(fn))

    @cached_property
    def mesh_scalar(self):
        """
        Scalar mesh (normE, normJ ...) — lighter, sufficient for most analyses.
        """
        fn = self._find_one("*_scalar.msh")
        return simnibs.msh.read_msh(str(fn))

    @cached_property
    def surface_overlays(self) -> dict[str, Path]:
        """
        Cortical surface overlays in subject space, keyed by stem name.
        Fields are defined at nodes (not elements) in these files.
        """
        return {p.stem: p for p in self._find("subject_overlays/*.msh")}

    @cached_property
    def fields_summary(self) -> dict[str, str]:
        """
        Parsed fields_summary.txt (key: value pairs).
        Returns empty dict if the file is absent.
        """
        fn = self.path / "fields_summary.txt"
        if not fn.exists():
            return {}
        result = {}
        for line in fn.read_text().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result


# ---------------------------------------------------------------------------
# Optimization / leadfield folder
# ---------------------------------------------------------------------------

class OptiFolder(SimNIBSFolder):
    """
    Reader for a SimNIBS optimization or leadfield folder.

    Expected layout:
        <optiID>/
        ├── *.hdf5      # leadfield matrix (large dataset)
        └── *.msh       # optimized field result(s)
    """

    def _validate(self):
        if not self._find("*.hdf5"):
            raise ValueError(f"{self.path} does not look like an opti folder (no .hdf5 found)")

    @cached_property
    def leadfield(self):
        """
        Open the leadfield HDF5 file (read-only).
        Caller is responsible for closing: use as context manager if needed.
        """
        import h5py
        fn = self._find_one("*.hdf5")
        return h5py.File(fn, "r")

    @cached_property
    def opt_results(self) -> list[Path]:
        """Optimized field meshes (.msh), one per optimization result."""
        return self._find("*.msh")