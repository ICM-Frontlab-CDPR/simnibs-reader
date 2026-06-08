"""Shared pytest fixtures for simnibs-reader tests."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_nifti(
    path: Path,
    shape: tuple[int, ...] = (10, 10, 10),
    data: np.ndarray | None = None,
    voxel_size: float = 1.0,
) -> Path:
    """Write a minimal NIfTI file and return its path."""
    affine = np.diag([voxel_size, voxel_size, voxel_size, 1.0])
    arr = data if data is not None else np.random.rand(*shape).astype(np.float32)
    nib.save(nib.Nifti1Image(arr, affine), str(path))
    return path


# ---------------------------------------------------------------------------
# m2m (segmentation) fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def m2m_dir(tmp_path: Path) -> Path:
    """Minimal fake ``m2m_sub01`` folder tree.

    Structure created::

        m2m_sub01/
        ├── T1.nii.gz
        ├── final_tissues.nii.gz
        └── label_prep/
            └── tissue_labeling_upsampled.nii.gz
    """
    root = tmp_path / "m2m_sub01"
    root.mkdir()

    # T1 and final tissues (required by _validate)
    _make_nifti(root / "T1.nii.gz")
    _make_nifti(root / "final_tissues.nii.gz")

    # Upsampled label image: GM=2, rest=0
    label_prep = root / "label_prep"
    label_prep.mkdir()
    label_data = np.zeros((10, 10, 10), dtype=np.int16)
    label_data[3:7, 3:7, 3:7] = 2  # Gray-Matter
    label_data[0:2, 0:2, 0:2] = 1  # White-Matter
    _make_nifti(
        label_prep / "tissue_labeling_upsampled.nii.gz",
        data=label_data,
    )

    return root


# ---------------------------------------------------------------------------
# Simulation fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def sim_dir(tmp_path: Path) -> Path:
    """Minimal fake simulation folder tree.

    Structure created::

        sim_sub01/
        ├── 0001_TDCS_1_scalar.msh          (empty)
        ├── fields_summary.txt
        ├── mni_volumes/
        │   └── 0001_TDCS_1_scalar_MNI_magnE.nii.gz
        └── subject_volumes/
            └── 0001_TDCS_1_scalar_magnE.nii.gz
    """
    root = tmp_path / "sim_sub01"
    root.mkdir()

    # Fake mesh file (just needs to exist)
    (root / "0001_TDCS_1_scalar.msh").touch()

    # fields_summary.txt
    (root / "fields_summary.txt").write_text(
        "SimNIBS version: 4.0\nSubject: sub01\n"
    )

    # E-field NIfTI volumes with known values
    efield_data = np.full((10, 10, 10), 0.5, dtype=np.float32)

    mni_dir = root / "mni_volumes"
    mni_dir.mkdir()
    _make_nifti(
        mni_dir / "0001_TDCS_1_scalar_MNI_magnE.nii.gz",
        data=efield_data,
    )

    subj_dir = root / "subject_volumes"
    subj_dir.mkdir()
    _make_nifti(
        subj_dir / "0001_TDCS_1_scalar_magnE.nii.gz",
        data=efield_data,
    )

    return root


# ---------------------------------------------------------------------------
# Standalone NIfTI fixtures (no folder tree needed)
# ---------------------------------------------------------------------------


@pytest.fixture()
def efield_nii(tmp_path: Path) -> Path:
    """A 10³ NIfTI filled with ``0.5`` — plain e-field mock."""
    p = tmp_path / "magnE.nii.gz"
    _make_nifti(p, data=np.full((10, 10, 10), 0.5, dtype=np.float32))
    return p


@pytest.fixture()
def mask_nii(tmp_path: Path) -> Path:
    """A 10³ binary NIfTI mask (ones in the 3:7 cube)."""
    p = tmp_path / "mask.nii.gz"
    data = np.zeros((10, 10, 10), dtype=np.uint8)
    data[3:7, 3:7, 3:7] = 1
    _make_nifti(p, data=data)
    return p


@pytest.fixture()
def label_nii(tmp_path: Path) -> Path:
    """A 10³ tissue label NIfTI (GM=2 in the centre, WM=1 in corner)."""
    p = tmp_path / "tissue_labeling_upsampled.nii.gz"
    data = np.zeros((10, 10, 10), dtype=np.int16)
    data[3:7, 3:7, 3:7] = 2  # Gray-Matter
    data[0:2, 0:2, 0:2] = 1  # White-Matter
    _make_nifti(p, data=data)
    return p


@pytest.fixture()
def lut_file(tmp_path: Path) -> Path:
    """A minimal ``*_LUT.txt`` file with 3 tissues."""
    p = tmp_path / "tissues_LUT.txt"
    p.write_text(
        "# SimNIBS tissue LUT\n"
        "1  White-Matter  255 255 255 0\n"
        "2  Gray-Matter   205  62  78 0\n"
        "3  CSF             0 118 214 0\n"
    )
    return p
