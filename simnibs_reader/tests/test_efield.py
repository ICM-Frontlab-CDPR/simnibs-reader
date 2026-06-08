"""Tests for EFieldAccessor, ROIExtractor, ROIResult, stats, and labels."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from simnibs_reader.efield.accessor import EFieldAccessor
from simnibs_reader.efield.labels import _SIMNIBS_LUT, parse_lut, resolve_tissue_value
from simnibs_reader.efield.stats import compute_stats, compute_ratio


# ===========================================================================
# EFieldAccessor
# ===========================================================================


class TestEFieldAccessor:
    def test_path_stored(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert acc.path == efield_nii

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            EFieldAccessor(tmp_path / "ghost.nii.gz")

    def test_lazy_img_not_loaded_at_init(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert "img" not in acc.__dict__

    def test_img_cached_after_access(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        _ = acc.img
        assert "img" in acc.__dict__

    def test_img_is_nifti(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert isinstance(acc.img, nib.Nifti1Image)

    def test_data_dtype(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert acc.data.dtype == np.float32

    def test_shape_matches(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert acc.shape == (10, 10, 10)

    def test_affine_shape(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert acc.affine.shape == (4, 4)

    def test_simulation_default_none(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert acc.simulation is None

    def test_simulation_stored(self, efield_nii: Path) -> None:
        sentinel = object()
        acc = EFieldAccessor(efield_nii, simulation=sentinel)  # type: ignore[arg-type]
        assert acc.simulation is sentinel

    def test_repr(self, efield_nii: Path) -> None:
        acc = EFieldAccessor(efield_nii)
        assert "magnE" in repr(acc)


# ===========================================================================
# ROI extraction via EFieldAccessor.get_roi
# ===========================================================================


class TestGetROIFromMask:
    def test_returns_roi_result(self, efield_nii: Path, mask_nii: Path) -> None:
        from simnibs_reader.efield.roi import ROIResult

        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert isinstance(roi, ROIResult)

    def test_values_shape_1d(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert roi.values.ndim == 1

    def test_values_nonzero(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert roi.n_voxels > 0

    def test_values_all_equal_05(self, efield_nii: Path, mask_nii: Path) -> None:
        """Efield is uniform 0.5 — all extracted values must be 0.5."""
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        np.testing.assert_allclose(roi.values, 0.5, atol=1e-5)

    def test_no_source_raises(self, efield_nii: Path) -> None:
        with pytest.raises(ValueError, match="Provide exactly one"):
            EFieldAccessor(efield_nii).get_roi()


class TestGetROIFromSphere:
    def test_sphere_returns_values(self, efield_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(coords=[5.0, 5.0, 5.0], radius=3.0)
        assert roi.n_voxels > 0

    def test_sphere_values_close_to_05(self, efield_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(coords=[5.0, 5.0, 5.0], radius=3.0)
        np.testing.assert_allclose(roi.values, 0.5, atol=1e-5)

    def test_large_radius_covers_whole_volume(self, efield_nii: Path) -> None:
        roi_small = EFieldAccessor(efield_nii).get_roi(coords=[5.0, 5.0, 5.0], radius=1.0)
        roi_large = EFieldAccessor(efield_nii).get_roi(coords=[5.0, 5.0, 5.0], radius=50.0)
        assert roi_large.n_voxels > roi_small.n_voxels


# ===========================================================================
# ROIResult
# ===========================================================================


class TestROIResult:
    def test_len_equals_n_voxels(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert len(roi) == roi.n_voxels

    def test_bool_true_when_nonempty(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert bool(roi)

    def test_numpy_array_interface(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        arr = np.asarray(roi)
        assert arr.shape == roi.values.shape

    def test_add_concatenates(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        combined = roi + roi
        assert combined.size == roi.n_voxels * 2

    def test_volume_mm3_positive(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert roi.volume_mm3 > 0

    def test_stats_keys(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        stats = roi.stats()
        for key in ("mean", "median", "std", "min", "max", "p5", "p95", "n_voxels", "volume_mm3"):
            assert key in stats

    def test_repr_raw(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert "raw" in repr(roi)

    def test_postprocess_returns_new_roi(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        cleaned = roi.postprocess(smooth_fwhm=None)
        assert cleaned is not roi
        assert cleaned.is_cleaned

    def test_postprocess_repr_cleaned(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        assert "cleaned" in repr(roi.postprocess(smooth_fwhm=None))

    def test_original_not_mutated_after_postprocess(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        _ = roi.postprocess(smooth_fwhm=None)
        assert not roi.is_cleaned


# ===========================================================================
# filter_tissue
# ===========================================================================


class TestFilterTissue:
    def test_explicit_label_img(self, efield_nii: Path, mask_nii: Path, label_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("Gray-Matter", label_img=label_nii)
        assert gm_roi.n_voxels > 0

    def test_case_insensitive(self, efield_nii: Path, mask_nii: Path, label_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("gray-matter", label_img=label_nii)
        assert gm_roi.n_voxels > 0

    def test_returns_new_roi_result(self, efield_nii: Path, mask_nii: Path, label_nii: Path) -> None:
        from simnibs_reader.efield.roi import ROIResult

        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("Gray-Matter", label_img=label_nii)
        assert isinstance(gm_roi, ROIResult)
        assert gm_roi is not roi

    def test_fewer_voxels_than_original(self, efield_nii: Path, mask_nii: Path, label_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("Gray-Matter", label_img=label_nii)
        assert gm_roi.n_voxels <= roi.n_voxels

    def test_unknown_tissue_raises(self, efield_nii: Path, mask_nii: Path, label_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        with pytest.raises(ValueError, match="not found"):
            roi.filter_tissue("Unicorn-Tissue", label_img=label_nii)

    def test_missing_label_img_no_segmentation_raises(self, efield_nii: Path, mask_nii: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        with pytest.raises(ValueError, match="label_img is required"):
            roi.filter_tissue("Gray-Matter")

    def test_auto_resolve_from_segmentation(
        self, sim_dir: Path, m2m_dir: Path, mask_nii: Path
    ) -> None:
        """filter_tissue resolves label_img automatically via set_segmentation."""
        from simnibs_reader.core.simulation import SimulationResult
        from simnibs_reader.core.segmentation import SegmentationResult

        sim = SimulationResult(sim_dir)
        sim.set_segmentation(SegmentationResult(m2m_dir))
        roi = sim.magnE_native.get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("Gray-Matter")  # no label_img kwarg
        assert gm_roi.n_voxels > 0

    def test_custom_lut_file(self, efield_nii: Path, mask_nii: Path, label_nii: Path, lut_file: Path) -> None:
        roi = EFieldAccessor(efield_nii).get_roi(mask=mask_nii)
        gm_roi = roi.filter_tissue("Gray-Matter", label_img=label_nii, lut=lut_file)
        assert gm_roi.n_voxels > 0


# ===========================================================================
# labels
# ===========================================================================


class TestSimnibsLUT:
    def test_gray_matter_is_2(self) -> None:
        assert _SIMNIBS_LUT["Gray-Matter"] == 2

    def test_white_matter_is_1(self) -> None:
        assert _SIMNIBS_LUT["White-Matter"] == 1

    def test_has_10_entries(self) -> None:
        assert len(_SIMNIBS_LUT) == 10


class TestParseLut:
    def test_parses_correctly(self, lut_file: Path) -> None:
        lut = parse_lut(lut_file)
        assert lut["Gray-Matter"] == 2
        assert lut["White-Matter"] == 1
        assert lut["CSF"] == 3

    def test_ignores_comments(self, lut_file: Path) -> None:
        lut = parse_lut(lut_file)
        assert len(lut) == 3  # only the 3 data lines

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_lut(tmp_path / "ghost_LUT.txt")

    def test_bad_int_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad_LUT.txt"
        bad.write_text("NaN  Gray-Matter  0 0 0\n")
        with pytest.raises(ValueError, match="not an integer"):
            parse_lut(bad)


class TestResolveTissueValue:
    def test_exact_match(self) -> None:
        assert resolve_tissue_value("Gray-Matter") == 2

    def test_case_insensitive(self) -> None:
        assert resolve_tissue_value("gray-matter") == 2
        assert resolve_tissue_value("GRAY-MATTER") == 2

    def test_custom_lut(self) -> None:
        lut = {"RegionA": 42}
        assert resolve_tissue_value("regiona", lut=lut) == 42

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            resolve_tissue_value("Invisible-Tissue")


# ===========================================================================
# compute_stats
# ===========================================================================


class TestComputeStats:
    def test_keys_present(self) -> None:
        stats = compute_stats(np.array([1.0, 2.0, 3.0]))
        for key in ("mean", "median", "std", "min", "max", "p5", "p95", "n_voxels"):
            assert key in stats

    def test_mean_correct(self) -> None:
        stats = compute_stats(np.array([1.0, 2.0, 3.0]))
        assert stats["mean"] == pytest.approx(2.0)

    def test_empty_array_returns_nan(self) -> None:
        stats = compute_stats(np.array([]))
        assert np.isnan(stats["mean"])
        assert stats["n_voxels"] == 0

    def test_nan_values_ignored(self) -> None:
        stats = compute_stats(np.array([1.0, np.nan, 3.0]))
        assert stats["n_voxels"] == 2

    def test_inf_values_ignored(self) -> None:
        stats = compute_stats(np.array([1.0, np.inf, 2.0]))
        assert stats["n_voxels"] == 2


class TestComputeRatio:
    def test_mean_ratio(self) -> None:
        ratio = compute_ratio(np.array([2.0, 2.0]), np.array([1.0, 1.0]), method="mean")
        assert ratio == pytest.approx(2.0)

    def test_median_ratio(self) -> None:
        ratio = compute_ratio(np.array([3.0]), np.array([1.0]), method="median")
        assert ratio == pytest.approx(3.0)

    def test_unknown_method_returns_nan(self) -> None:
        assert np.isnan(compute_ratio(np.array([1.0]), np.array([1.0]), method="mode"))
