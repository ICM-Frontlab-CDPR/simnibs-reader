"""Tests for SimulationResult."""

from __future__ import annotations

from pathlib import Path

import pytest

from simnibs_reader.core.simulation import SimulationResult
from simnibs_reader.core.segmentation import SegmentationResult
from simnibs_reader.efield.accessor import EFieldAccessor


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidate:
    def test_ok(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.path == sim_dir

    def test_missing_folder_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            SimulationResult(tmp_path / "does_not_exist")

    def test_empty_folder_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_sim"
        empty.mkdir()
        with pytest.raises(ValueError, match="does not look like a simulation folder"):
            SimulationResult(empty)


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


class TestSimId:
    def test_from_msh_filename(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.sim_id == "0001_TDCS_1"

    def test_fallback_to_folder_name(self, tmp_path: Path) -> None:
        """No .msh present — sim_id falls back to folder name."""
        import nibabel as nib, numpy as np

        root = tmp_path / "my_sim"
        (root / "subject_volumes").mkdir(parents=True)
        affine = np.eye(4)
        nib.save(
            nib.Nifti1Image(np.zeros((2, 2, 2)), affine),
            str(root / "subject_volumes" / "x_magnE.nii.gz"),
        )
        sim = SimulationResult(root)
        assert sim.sim_id == "my_sim"


# ---------------------------------------------------------------------------
# E-field accessors
# ---------------------------------------------------------------------------


class TestEFieldAccessors:
    def test_magnE_is_accessor(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert isinstance(sim.magnE, EFieldAccessor)

    def test_magnE_native_is_accessor(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert isinstance(sim.magnE_native, EFieldAccessor)

    def test_accessor_carries_simulation_back_ref(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.magnE.simulation is sim

    def test_lazy_loading(self, sim_dir: Path) -> None:
        """img must NOT be loaded at accessor creation time."""
        sim = SimulationResult(sim_dir)
        acc = sim.magnE
        assert "img" not in acc.__dict__  # cached_property not yet resolved
        _ = acc.img                        # trigger load
        assert "img" in acc.__dict__

    def test_cached_property_returns_same_object(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.magnE is sim.magnE


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestFieldsSummary:
    def test_parsed_correctly(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.fields_summary["SimNIBS version"] == "4.0"
        assert sim.fields_summary["Subject"] == "sub01"

    def test_empty_when_file_absent(self, tmp_path: Path) -> None:
        import nibabel as nib, numpy as np

        root = tmp_path / "no_summary"
        (root / "subject_volumes").mkdir(parents=True)
        nib.save(
            nib.Nifti1Image(np.zeros((2, 2, 2)), np.eye(4)),
            str(root / "subject_volumes" / "x_magnE.nii.gz"),
        )
        sim = SimulationResult(root)
        assert sim.fields_summary == {}


class TestAvailableFields:
    def test_keys_present(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        fields = sim.available_fields
        assert "mni" in fields and "native" in fields

    def test_mni_contains_magnE(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        names = [p.name for p in sim.available_fields["mni"]]
        assert any("magnE" in n for n in names)


# ---------------------------------------------------------------------------
# set_segmentation
# ---------------------------------------------------------------------------


class TestSetSegmentation:
    def test_segmentation_starts_none(self, sim_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        assert sim.segmentation is None

    def test_set_segmentation_stores_ref(self, sim_dir: Path, m2m_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        seg = SegmentationResult(m2m_dir)
        sim.set_segmentation(seg)
        assert sim.segmentation is seg

    def test_set_segmentation_invalidates_cache(self, sim_dir: Path, m2m_dir: Path) -> None:
        """Cached accessor should be rebuilt after set_segmentation."""
        sim = SimulationResult(sim_dir)
        acc_before = sim.magnE          # populate cache
        sim.set_segmentation(SegmentationResult(m2m_dir))
        acc_after = sim.magnE           # must be a new object
        assert acc_before is not acc_after

    def test_accessor_carries_segmentation(self, sim_dir: Path, m2m_dir: Path) -> None:
        sim = SimulationResult(sim_dir)
        sim.set_segmentation(SegmentationResult(m2m_dir))
        assert sim.magnE.simulation.segmentation is not None
