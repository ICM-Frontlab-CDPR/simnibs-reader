"""Tests for SegmentationResult."""

from __future__ import annotations

from pathlib import Path

import pytest

from simnibs_reader.core.segmentation import SegmentationResult


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidate:
    def test_ok(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.path == m2m_dir

    def test_missing_folder_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            SegmentationResult(tmp_path / "does_not_exist")

    def test_empty_folder_raises(self, tmp_path: Path) -> None:
        """Folder exists but has neither T1 nor final_tissues."""
        empty = tmp_path / "m2m_empty"
        empty.mkdir()
        with pytest.raises(ValueError, match="does not look like an m2m folder"):
            SegmentationResult(empty)

    def test_file_instead_of_dir_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "not_a_dir.txt"
        f.touch()
        with pytest.raises(NotADirectoryError):
            SegmentationResult(f)


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


class TestSubjectId:
    def test_strips_m2m_prefix(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.subject_id == "sub01"

    def test_no_prefix(self, tmp_path: Path) -> None:
        """Folder named without 'm2m_' prefix — subject_id equals folder name."""
        import nibabel as nib, numpy as np

        root = tmp_path / "rawname"
        root.mkdir()
        affine = np.eye(4)
        nib.save(nib.Nifti1Image(np.zeros((2, 2, 2)), affine), str(root / "T1.nii.gz"))
        nib.save(nib.Nifti1Image(np.zeros((2, 2, 2)), affine), str(root / "final_tissues.nii.gz"))
        seg = SegmentationResult(root)
        assert seg.subject_id == "rawname"


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------


class TestPaths:
    def test_t1_exists(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.t1.exists()

    def test_final_tissues_exists(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.final_tissues.exists()

    def test_tissue_labeling_upsampled_exists(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.tissue_labeling_upsampled.exists()

    def test_t2_is_none_when_absent(self, m2m_dir: Path) -> None:
        """T2 is optional — should return None rather than raise."""
        seg = SegmentationResult(m2m_dir)
        assert seg.t2 is None

    def test_surfaces_empty_when_absent(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.surfaces == {}

    def test_surfaces_populated(self, m2m_dir: Path) -> None:
        surf_dir = m2m_dir / "surfaces"
        surf_dir.mkdir()
        (surf_dir / "lh.central.gii").touch()
        (surf_dir / "rh.central.gii").touch()
        seg = SegmentationResult(m2m_dir)
        assert "lh.central" in seg.surfaces
        assert "rh.central" in seg.surfaces


# ---------------------------------------------------------------------------
# Optional DTI
# ---------------------------------------------------------------------------


class TestDTI:
    def test_has_dti_false_by_default(self, m2m_dir: Path) -> None:
        seg = SegmentationResult(m2m_dir)
        assert seg.has_dti is False

    def test_has_dti_true_when_dir_exists(self, m2m_dir: Path) -> None:
        (m2m_dir / "dMRI_prep").mkdir()
        seg = SegmentationResult(m2m_dir)
        assert seg.has_dti is True
