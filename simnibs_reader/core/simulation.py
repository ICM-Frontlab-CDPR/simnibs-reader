"""
simulation.py
-------------
Reader for a SimNIBS **simulation** output folder.

Expected layout (see ``simnibs-tree/tree-simnibs-simu.txt``)::

    <simID>/
    ├── <simID>_scalar.msh
    ├── fields_summary.txt
    ├── mni_volumes/
    │   ├── *_scalar_MNI_magnE.nii.gz
    │   ├── *_scalar_MNI_magnJ.nii.gz
    │   ├── *_scalar_MNI_E.nii.gz
    │   └── *_scalar_MNI_J.nii.gz
    ├── subject_volumes/
    │   ├── *_scalar_magnE.nii.gz
    │   └── …
    └── subject_overlays/
        └── …
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from ._base import SimNIBSResult
from ..efield.efield import EField
from .segmentation import SegmentationResult


class SimulationResult(SimNIBSResult):
    """Lazy reader for a SimNIBS simulation output folder."""

    _kind = "Simulation folder"

    def __init__(self, path: str | Path) -> None:
        self.segmentation: SegmentationResult | None = None
        super().__init__(path)

    # ------------------------------------------------------------------
    # Segmentation back-reference
    # ------------------------------------------------------------------

    def set_segmentation(self, seg: SegmentationResult) -> None:
        """Attach a :class:`SegmentationResult` to this simulation.

        Once set, downstream methods such as
        :meth:`~simnibs_reader.efield.roi.ROI.filter_tissue` can
        resolve tissue labels automatically without explicit arguments.

        Parameters
        ----------
        seg : SegmentationResult
            The head-model (``m2m_*``) associated with this simulation.
        """
        self.segmentation: SegmentationResult | None = seg
        # Invalidate cached accessors so they are rebuilt with simulation=self
        for attr in ("magnE", "magnJ", "E", "J",
                     "magnE_native", "magnJ_native", "E_native", "J_native"):
            self.__dict__.pop(attr, None)

    def _validate(self) -> None:
        has_mni = bool(self._find("mni_volumes/*.nii.gz"))
        has_subj = bool(self._find("subject_volumes/*.nii.gz"))
        if not has_mni and not has_subj:
            raise ValueError(
                f"{self.path} does not look like a simulation folder "
                "(no NIfTI volumes found in mni_volumes/ or subject_volumes/)."
            )

    # ------------------------------------------------------------------
    # Identifiers
    # ------------------------------------------------------------------

    @cached_property
    def sim_id(self) -> str:
        """Infer simulation ID from the scalar mesh filename.

        e.g. ``0001_TDCS_1_scalar.msh`` → ``0001_TDCS_1``
        Falls back to the folder name if no ``.msh`` is present.
        """
        try:
            fn = self._find_one("*_scalar.msh")
            return fn.stem.removesuffix("_scalar")
        except FileNotFoundError:
            return self.path.name

    # ------------------------------------------------------------------
    # E-field accessors  (MNI space)
    # ------------------------------------------------------------------

    @cached_property
    def magnE(self) -> EField:
        """E-field magnitude in MNI space (``*_MNI_magnE.nii.gz``)."""
        return EField(
            self._find_one("mni_volumes/*_MNI_magnE.nii.gz"),
            simulation=self,
        )

    @cached_property
    def magnJ(self) -> EField:
        """Current-density magnitude in MNI space (``*_MNI_magnJ.nii.gz``)."""
        return EField(
            self._find_one("mni_volumes/*_MNI_magnJ.nii.gz"),
            simulation=self,
        )

    @cached_property
    def E(self) -> EField:
        """E-field vector in MNI space (``*_MNI_E.nii.gz``)."""
        return EField(
            self._find_one("mni_volumes/*_MNI_E.nii.gz"),
            simulation=self,
        )

    @cached_property
    def J(self) -> EField:
        """Current-density vector in MNI space (``*_MNI_J.nii.gz``)."""
        return EField(
            self._find_one("mni_volumes/*_MNI_J.nii.gz"),
            simulation=self,
        )

    # ------------------------------------------------------------------
    # E-field accessors  (native / subject space)
    # ------------------------------------------------------------------

    @cached_property
    def magnE_native(self) -> EField:
        """E-field magnitude in subject space (``*_magnE.nii.gz``)."""
        return EField(
            self._find_one("subject_volumes/*_magnE.nii.gz"),
            simulation=self,
        )

    @cached_property
    def magnJ_native(self) -> EField:
        """Current-density magnitude in subject space."""
        return EField(
            self._find_one("subject_volumes/*_magnJ.nii.gz"),
            simulation=self,
        )

    @cached_property
    def E_native(self) -> EField:
        """E-field vector in subject space."""
        return EField(
            self._find_one("subject_volumes/*_E.nii.gz"),
            simulation=self,
        )

    @cached_property
    def J_native(self) -> EField:
        """Current-density vector in subject space."""
        return EField(
            self._find_one("subject_volumes/*_J.nii.gz"),
            simulation=self,
        )

    # ------------------------------------------------------------------
    # Metadata & discovery
    # ------------------------------------------------------------------

    @cached_property
    def fields_summary(self) -> dict[str, str]:
        """Parsed ``fields_summary.txt`` (key: value pairs).

        Returns an empty dict if the file is absent.
        """
        fn = self.path / "fields_summary.txt"
        if not fn.exists():
            return {}
        result: dict[str, str] = {}
        for line in fn.read_text().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result

    @cached_property
    def available_fields(self) -> dict[str, list[Path]]:
        """All available NIfTI field files, grouped by space.

        Returns
        -------
        dict
            ``{"mni": [Path, …], "native": [Path, …]}``
        """
        return {
            "mni": self._find("mni_volumes/*.nii.gz"),
            "native": self._find("subject_volumes/*.nii.gz"),
        }

    @cached_property
    def surface_overlays(self) -> dict[str, Path]:
        """Cortical surface overlays, keyed by stem name."""
        overlay_dir = self.path / "subject_overlays"
        if not overlay_dir.exists():
            return {}
        return {p.stem: p for p in sorted(overlay_dir.iterdir()) if p.is_file()}
