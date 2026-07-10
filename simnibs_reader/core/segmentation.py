"""
segmentation.py
---------------
Reader for a SimNIBS **head-model** folder (``m2m_<subID>``).

Expected layout (see ``simnibs-tree/tree-simnibs-charm.txt``)::

    m2m_<subID>/
    ├── <subID>.msh
    ├── T1.nii.gz
    ├── final_tissues.nii.gz
    ├── segmentation/
    │   ├── T1_bias_corrected.nii.gz
    │   └── …
    ├── label_prep/
    │   └── tissue_labeling_upsampled.nii.gz
    ├── surfaces/
    │   ├── lh.central.gii
    │   └── …
    └── toMNI/
        ├── Conform2MNI_nonl.nii.gz
        ├── MNI2Conform_nonl.nii.gz
        └── final_tissues_MNI.nii.gz
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from ._base import SimNIBSResult


class SegmentationResult(SimNIBSResult):
    """Lazy reader for a SimNIBS head-model folder (charm / headreco output)."""

    _kind = "Segmentation folder (m2m_*)"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        # A valid m2m folder has at least a T1 and a tissue segmentation
        has_t1 = (self.path / "T1.nii.gz").exists()
        has_tissues = (self.path / "final_tissues.nii.gz").exists()
        if not has_t1 and not has_tissues:
            raise ValueError(
                f"{self.path} does not look like an m2m folder "
                "(missing T1.nii.gz and final_tissues.nii.gz)."
            )

    # ------------------------------------------------------------------
    # Identifiers
    # ------------------------------------------------------------------

    @cached_property
    def subject_id(self) -> str:
        """Extract subject ID from folder name (e.g. ``m2m_sub01`` → ``sub01``)."""
        return self.path.name.removeprefix("m2m_")

    # ------------------------------------------------------------------
    # Anatomical images
    # ------------------------------------------------------------------

    @cached_property
    def t1(self) -> Path:
        """Conformed T1 NIfTI (defines the subject coordinate space)."""
        return self._find_one("T1.nii.gz")

    @cached_property
    def t1_bias_corrected(self) -> Path:
        """Bias-corrected T1 inside ``segmentation/``."""
        return self._find_one("segmentation/T1_bias_corrected.nii.gz")

    @cached_property
    def t2(self) -> Path | None:
        """Registered T2 NIfTI, or ``None`` if absent."""
        try:
            return self._find_one("T2_reg.nii.gz")
        except FileNotFoundError:
            return None

    # ------------------------------------------------------------------
    # Tissue segmentation
    # ------------------------------------------------------------------

    @cached_property
    def final_tissues(self) -> Path:
        """Final tissue label volume (``final_tissues.nii.gz``)."""
        return self._find_one("final_tissues.nii.gz")

    @cached_property
    def tissue_labeling_upsampled(self) -> Path:
        """Upsampled tissue labeling in ``label_prep/``."""
        return self._find_one("label_prep/tissue_labeling_upsampled.nii.gz")

    @cached_property
    def final_tissues_mni(self) -> Path:
        """Tissue segmentation warped to MNI space."""
        return self._find_one("toMNI/final_tissues_MNI.nii.gz")

    # ------------------------------------------------------------------
    # Surfaces
    # ------------------------------------------------------------------

    @cached_property
    def surfaces(self) -> dict[str, Path]:
        """Cortical surface files (GIfTI), keyed by stem name.

        e.g. ``{"lh.central": Path(…), "rh.central": Path(…)}``
        """
        return {p.stem: p for p in self._find("surfaces/*.gii")}

    # ------------------------------------------------------------------
    # MNI warp fields
    # ------------------------------------------------------------------

    @cached_property
    def warp_conform_to_mni(self) -> Path:
        """Non-linear warp field: subject → MNI."""
        return self._find_one("toMNI/Conform2MNI_nonl.nii.gz")

    @cached_property
    def warp_mni_to_conform(self) -> Path:
        """Non-linear warp field: MNI → subject."""
        return self._find_one("toMNI/MNI2Conform_nonl.nii.gz")

    # ------------------------------------------------------------------
    # EEG positions
    # ------------------------------------------------------------------

    @cached_property
    def eeg_positions(self) -> dict[str, Path]:
        """EEG electrode position files, keyed by stem name."""
        return {p.stem: p for p in self._find("eeg_positions/*.csv")}

    # ------------------------------------------------------------------
    # DTI (optional) --> 
    # ------------------------------------------------------------------

    @cached_property
    def has_dti(self) -> bool:
        """Whether diffusion data was processed (``dMRI_prep/`` exists)."""
        return (self.path / "dMRI_prep").is_dir()

    @cached_property
    def dti_fa(self) -> Path | None:
        """Fractional anisotropy coregistered to T1, or ``None``."""
        try:
            return self._find_one("dMRI_prep/dti_results_T1space/DTI_coregT1_FA.nii.gz")
        except FileNotFoundError:
            return None

     # ------------------------------------------------------------------
    # Lesions 
    # ------------------------------------------------------------------

    @cached_property
    def lesion_native(self) -> Path | None:
        """Masque de lésion en espace sujet (dans m2m_*/_lesions/)."""
        try:
            return self._find_one("_lesions/*brain_lesion.nii.gz")  # à adapter au vrai nom
        except FileNotFoundError:
            return None

    @cached_property
    def lesion_mni(self) -> Path | None:
        try:
            return self._find_one("_lesions/*brain_lesion_mni.nii.gz")
        except FileNotFoundError:
            return None
    
    ## add coherency between eeg files and nifti files  
    def read_electrodes(
        self,
        cap: str | None = None,
        types: tuple[str, ...] = ("Electrode",),
    ) -> list[dict]:
        """Parse un cap EEG SimNIBS → liste de dicts {label, x, y, z}.

        Format CSV SimNIBS (sans header) : Type,x,y,z,label
        ex. : Electrode,35.1,-81.5,43.3,P2
                Fiducial,1.4,84.8,-36.5,Nz

        Parameters
        ----------
        cap : str or None
            Stem du fichier CSV (sans extension) ; ex. ``"EEG10-10_Neuroelectrics"``.
            Si None : préférence Neuroelectrics > Jurak_2007 > premier trouvé.
        types : tuple of str
            Types de lignes à inclure. Par défaut ``("Electrode",)`` — exclut
            les fiducials. Passe ``("Electrode", "Fiducial")`` pour tout garder.

        Returns
        -------
        list of dict
            Chaque dict : ``{"label": str, "x": float, "y": float, "z": float}``.
            Coordonnées en mm, espace sujet (même repère que T1/magnE_native).
        """
        import csv

        caps = self.eeg_positions
        if not caps:
            raise FileNotFoundError(
                f"Aucun eeg_positions/*.csv dans {self.path}"
            )

        if cap is not None:
            if cap not in caps:
                raise FileNotFoundError(
                    f"Cap '{cap}' introuvable dans {self.path / 'eeg_positions'}. "
                    f"Disponibles : {sorted(caps)}"
                )
            target = caps[cap]
        else:
            for preference in ("EEG10-10_Neuroelectrics", "EEG10-10_UI_Jurak_2007"):
                if preference in caps:
                    target = caps[preference]
                    break
            else:
                target = next(iter(caps.values()))

        electrodes = []
        with open(str(target), newline="") as fh:
            for row in csv.reader(fh):
                if not row or len(row) < 5:
                    continue
                row_type = row[0].strip()
                if row_type not in types:
                    continue
                try:
                    x, y, z = float(row[1]), float(row[2]), float(row[3])
                except ValueError:
                    continue
                electrodes.append({
                    "label": row[4].strip(),
                    "x": x,
                    "y": y,
                    "z": z,
                })
        return electrodes
