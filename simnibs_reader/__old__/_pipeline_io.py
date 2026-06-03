"""
SimNIBS pipeline I/O module.
Centralises all input/output operations: file discovery, NIfTI image loading,
CSV and YAML configuration reading/writing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import nibabel as nib
import numpy as np
import pandas as pd

from ._config import PipelineConfig
from ._logging import get_logger





# ---------------------------------------------------------------------------
# Output naming context
# ---------------------------------------------------------------------------




def get_preps_root(paths_config) -> Path:
    """Retourne la racine des segmentations charm (m2m_*)."""
    if paths_config.simnibs_preps is not None:
        return Path(paths_config.simnibs_preps)
    return Path(paths_config.simnibs_output)


def get_simu_root(paths_config) -> Path:
    """Retourne la racine des simulations/optimisations."""
    if paths_config.simnibs_simu is not None:
        return Path(paths_config.simnibs_simu)
    return Path(paths_config.simnibs_output)


def get_subject_paths(simnibs_output_dir: Path, subject: str) -> Dict[str, Path]:
    """Return canonical subject-level paths used across the pipeline."""
    subject_dir = Path(simnibs_output_dir) / subject
    return {
        "subject_dir": subject_dir,
        "m2m_dir": subject_dir / f"m2m_{subject}",
        "subject_target_dir": subject_dir / "subject_target",
    }


def get_subject_paths_from_config(paths_config, subject: str) -> Dict[str, Path]:
    """
    Return canonical subject-level paths, handling split preps/simu directories.

    - ``subject_dir``        : simu root / subject  (simulations live here)
    - ``m2m_dir``            : preps root / subject / m2m_{subject}  (charm segmentation)
    - ``subject_target_dir`` : simu root / subject / subject_target
    """
    preps_root = get_preps_root(paths_config)
    simu_root = get_simu_root(paths_config)
    simu_subject_dir = simu_root / subject
    preps_subject_dir = preps_root / subject
    return {
        "subject_dir": simu_subject_dir,
        "m2m_dir": preps_subject_dir / f"m2m_{subject}",
        "subject_target_dir": simu_subject_dir / "subject_target",
    }


def get_analysis_dir(results_dir: Path, space: str) -> Path:
    """Return the shared analysis output directory."""
    return Path(results_dir) / "3-analysis"


def get_features_csv_path(results_dir: Path, space: str) -> Path:
    """Return the canonical features CSV path for a given space."""
    return get_analysis_dir(results_dir, space) / f"all_features_{space_tag(space)}.csv"


def get_inter_subject_summary_csv_path(results_dir: Path, space: str) -> Path:
    """Return the inter-subject summary CSV path for a given space."""
    return (
        get_analysis_dir(results_dir, space)
        / f"inter_subject_summary_{space_tag(space)}.csv"
    )


def get_intra_subject_diff_csv_path(
    results_dir: Path, space: str, condition: str
) -> Path:
    """Return the intra-subject diff CSV path for a condition and space."""
    return (
        get_analysis_dir(results_dir, space)
        / f"intra_subject_diff_{condition}_{space_tag(space)}.csv"
    )


def get_clusters_csv_path(results_dir: Path, space: str) -> Path:
    """Return the clustering CSV path for a given space."""
    return get_analysis_dir(results_dir, space) / f"clusters_{space_tag(space)}.csv"


def load_config(config_path: Path) -> PipelineConfig:
    """Load and validate the YAML configuration file via Pydantic models."""
    from _config import load_and_validate

    return load_and_validate(config_path)


def find_raw_efield(
    simnibs_output_dir: Path, subject: str, roi: str, mode: str
) -> Optional[Path]:
    """
    Find the raw (unprocessed) e-field file in the SimNIBS output directory.

    Parameters
    ----------
    simnibs_output_dir : Path
        SimNIBS output directory.
    subject : str
        Subject ID.
    roi : str
        ROI name.
    mode : str
        Mode (simulation or optimization).

    Returns
    -------
    Path or None
        Path to the file, or None if not found.
    """
    subject_dir = simnibs_output_dir / subject

    if not subject_dir.exists():
        return None

    if mode == "simulation":
        base_dir = subject_dir / "simulations"
    else:
        base_dir = subject_dir / "optimizations"

    if not base_dir.exists():
        return None

    pattern = f"{mode}_{mode}_{roi}_*"
    matching_dirs = list(base_dir.glob(pattern))

    if not matching_dirs:
        return None

    mode_dir = matching_dirs[0]

    if mode == "optimization":
        mni_volumes_dir = mode_dir / "simulation_with_optimal_montage" / "mni_volumes"
    else:
        mni_volumes_dir = mode_dir / "mni_volumes"

    if not mni_volumes_dir.exists():
        return None

    efield_files = list(mni_volumes_dir.glob("*_scalar_MNI_magnE.nii.gz"))
    return efield_files[0] if efield_files else None


def find_simulation_dirs(
    subject_dir: Path, condition: str, mode: str, folder_pattern: str | None = None
) -> List[Path]:
    """
    Find all simulation/optimization directories for a given condition.
    Handles hashes in folder names.

    Parameters
    ----------
    subject_dir : Path
        Subject directory (e.g. 001-CC).
    condition : str
        Stimulation condition (e.g. fef, ips-left).
        Used as the search fragment if *folder_pattern* is not provided.
    mode : str
        Mode (simulation or optimization).
    folder_pattern : str or None
        Glob fragment to use instead of the condition name when searching
        SimNIBS folders.  Useful when the ROI name differs from the folder name
        (e.g. ROI 'ips-left' but folders named '…ips_left…').

    Returns
    -------
    List[Path]
        List of matching directories.
    """
    fragment = folder_pattern if folder_pattern is not None else condition
    pattern = f"*{mode}_{fragment}*"

    if mode == "simulation":
        base_dir = subject_dir / "simulations"
    else:
        base_dir = subject_dir / "optimizations"

    if not base_dir.exists():
        logger.warning(f"{mode} directory not found: {base_dir}")
        return []

    found_dirs = list(base_dir.glob(pattern))

    if not found_dirs:
        logger.warning(f"No {mode} found for pattern: {pattern} in {base_dir}")

    return found_dirs


def find_efield_files(
    simulation_dir: Path, mode: str, space: str = SPACE_MNI
) -> List[Path]:
    """
    Find e-field files in a simulation/optimization directory.

    Parameters
    ----------
    simulation_dir : Path
        Simulation or optimization directory.
    mode : str
        Mode (simulation or optimization).
    space : str
        ``'mni'`` (default): ``*_scalar_MNI_magnE.nii.gz`` files in ``mni_volumes/``.
        ``'native'``: ``*_scalar_magnE.nii.gz`` files in ``subject_volumes/``.

    Returns
    -------
    List[Path]
        List of e-field files found.
    """
    space = normalize_space(space)

    if space == SPACE_NATIVE:
        if mode == "optimization":
            volumes_dir = (
                simulation_dir / "simulation_with_optimal_montage" / "subject_volumes"
            )
        else:
            volumes_dir = simulation_dir / "subject_volumes"
        glob_pattern = "*_scalar_magnE.nii.gz"
    else:
        if mode == "optimization":
            volumes_dir = (
                simulation_dir / "simulation_with_optimal_montage" / "mni_volumes"
            )
        else:
            volumes_dir = simulation_dir / "mni_volumes"
        glob_pattern = "*_scalar_MNI_magnE.nii.gz"

    if not volumes_dir.exists():
        logger.warning(f"{space}_volumes directory not found: {volumes_dir}")
        return []

    efield_files = list(volumes_dir.glob(glob_pattern))

    if not efield_files:
        logger.warning(f"No e-field files found in {volumes_dir}")

    return efield_files


def get_t1_conform(
    m2m_dir: Path,
    filename: str = "segmentation/T1_bias_corrected.nii.gz",
) -> Path:
    """
    Return the path to the T1 file inside ``m2m_dir``.

    Parameters
    ----------
    m2m_dir : Path
        ``m2m_<subject>`` directory produced by SimNIBS.
    filename : str
        Relative path to the T1 file (default: ``segmentation/T1_bias_corrected.nii.gz``).

    Raises
    ------
    FileNotFoundError
    """
    path = Path(m2m_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"T1 not found: {path}")
    return path


def get_brainmask(
    m2m_dir: Optional[Path] = None,
    filename: str = "label_prep/tissue_labeling_upsampled.nii.gz",
    space: str = SPACE_NATIVE,
    mni_mask_path: Optional[Path] = None,
) -> Path:
    """
    Return the path to the brain mask.

    Parameters
    ----------
    m2m_dir : Path or None
        ``m2m_<subject>`` directory produced by SimNIBS. Ignored when ``space='mni'``.
    filename : str
        Relative path to the mask file inside ``m2m_dir`` (subject space only).
    space : str
        ``'native'`` (default): mask inside ``m2m_dir``.
        ``'mni'``: MNI mask passed via ``mni_mask_path`` (read from config).
    mni_mask_path : Path or None
        MNI mask path, required when ``space='mni'``.
        Must come from ``config['paths']['mni_brain_mask']``.

    Raises
    ------
    FileNotFoundError, ValueError
    """
    space = normalize_space(space)

    if space == SPACE_MNI:
        if mni_mask_path is None:
            raise ValueError(
                "mni_mask_path is required when space='mni' (config['paths']['mni_brain_mask'])"
            )
        path = Path(mni_mask_path)
    else:
        if m2m_dir is None:
            raise ValueError("m2m_dir is required when space='native'")
        path = Path(m2m_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"Brain mask not found: {path}")
    return path


def get_mni_tissues(m2m_dir: Path) -> Path:
    """
    Return the path to the tissue segmentation in MNI space.

    Produced by SimNIBS at ``toMNI/final_tissues_MNI.nii.gz``.
    Labels: 1=WM, 2=GM, 3=CSF, 4=Bone, 5=Scalp …
    """
    path = Path(m2m_dir) / "toMNI" / "final_tissues_MNI.nii.gz"
    if not path.exists():
        raise FileNotFoundError(f"MNI tissues not found: {path}")
    return path


def get_roi_mask_path(
    simnibs_output_dir: Path,
    condition: str,
    space: str = SPACE_MNI,
    subject: Optional[str] = None,
) -> Path:
    """
    Return the ROI mask path for a given condition.

    Parameters
    ----------
    simnibs_output_dir : Path
        SimNIBS output directory.
    condition : str
        Stimulation condition.
    space : str
        ``'mni'`` (default): masks in ``mni_target/``.
        ``'native'``: subject masks in ``<subject>/subject_target/``.
    subject : str or None
        Subject ID, required when ``space='native'``.

    Returns
    -------
    Path
        ROI mask path.

    Raises
    ------
    FileNotFoundError
        If the requested mask does not exist.
    """
    space = normalize_space(space)

    if space == SPACE_NATIVE:
        if not subject:
            raise ValueError("subject is required when space='native'")
        mask_path = (
            simnibs_output_dir
            / subject
            / "subject_target"
            / f"{condition}_mask_{space_tag(space)}.nii.gz"
        )
    else:
        mask_path = (
            simnibs_output_dir
            / "mni_target"
            / f"{condition}_mask_{space_tag(space)}.nii.gz"
        )

    if not mask_path.exists():
        raise FileNotFoundError(f"ROI mask not found ({space} space): {mask_path}")

    return mask_path


def get_preproc_dir(sim_dir: Path, mode: str, space: str = SPACE_MNI) -> Path:
    """
    Return the preprocessing directory for a given simulation directory.

    Parameters
    ----------
    sim_dir : Path
        SimNIBS simulation directory.
    mode : str
        ``'simulation'`` or ``'optimization'``.
    space : str
        ``'mni'`` (default) or ``'native'``.
    """
    space = normalize_space(space)
    volumes_dir = "subject_volumes" if space == SPACE_NATIVE else "mni_volumes"
    if mode == "optimization":
        return sim_dir / "simulation_with_optimal_montage" / volumes_dir
    return sim_dir / volumes_dir


def get_preproc_paths(preproc_dir: Path, base_name: str, roi_name: str) -> dict:
    """
    Return the intra- and extra-ROI preprocessed file paths.

    Parameters
    ----------
    preproc_dir : Path
        Preprocessing output directory (e.g. mni_volumes/).
    base_name : str
        Base name of the e-field file (without extension).
    roi_name : str
        ROI name used (e.g. 'fef', 'ips_left').

    Returns
    -------
    dict with keys:
        ``intra_masked``, ``intra_cleaned``,
        ``extra_masked``,  ``extra_cleaned``
    """
    return {
        "intra_masked": preproc_dir / f"{base_name}_{roi_name}_masked.nii.gz",
        "intra_cleaned": preproc_dir / f"{base_name}_{roi_name}_cleaned.nii.gz",
        "extra_masked": preproc_dir / f"{base_name}_extra_{roi_name}_masked.nii.gz",
        "extra_cleaned": preproc_dir / f"{base_name}_extra_{roi_name}_cleaned.nii.gz",
    }


def load_nifti(path: Path) -> Tuple[np.ndarray, nib.Nifti1Image]:
    """
    Load a NIfTI file.

    Parameters
    ----------
    path : Path
        Path to the NIfTI file.

    Returns
    -------
    data : np.ndarray
        Volume data array.
    img : nib.Nifti1Image
        Full NIfTI image.
    """
    img = nib.load(str(path))
    data = img.get_fdata()
    return data, img


def load_img(
    path_or_img: Union[str, Path, nib.spatialimages.SpatialImage],
) -> nib.spatialimages.SpatialImage:
    """Load a NIfTI image from a path or return the image if already loaded."""
    if isinstance(path_or_img, (str, Path)):
        return nib.load(str(path_or_img))
    if isinstance(path_or_img, nib.spatialimages.SpatialImage):
        return path_or_img
    raise TypeError(f"Expected path or nibabel image, got {type(path_or_img)}")


def validate_binary(data: np.ndarray, name: str = "mask") -> None:
    """Raise ValueError if *data* contains values other than 0 and 1."""
    unique_values = np.unique(data)
    if not np.all(np.isin(unique_values, [0, 1])):
        raise ValueError(
            f"{name} must be binary (contain only 0 and 1), "
            f"but contains values: {unique_values}"
        )

