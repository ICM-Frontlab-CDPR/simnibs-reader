"""Tests for MNI ↔ native warping and the coords_space contract.

Background: EField._from_sphere maps world coordinates through inv(affine),
so it silently assumed coords were already in the volume's own space. Passing
MNI coordinates to a native-space volume therefore placed the sphere outside
the head and produced an empty mask, surfacing only as a downstream nilearn
error ("The mask is invalid as it is empty").
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from simnibs_reader.nifti._warp import (
    load_warp,
    mni_to_native_coords,
    warp_mni_mask_to_native,
)
from simnibs_reader.nifti.efield import EField

# ---------------------------------------------------------------------------
# Fixtures: a toy subject whose space is MNI shifted by a known offset
# ---------------------------------------------------------------------------

OFFSET = np.array([10.0, -5.0, 3.0])


@pytest.fixture
def warp_path(tmp_path: Path) -> Path:
    """Deformation field on a 12³ subject grid storing MNI = native + OFFSET."""
    shape = (12, 12, 12)
    affine = np.eye(4)
    ii, jj, kk = np.indices(shape)
    native_mm = np.stack([ii, jj, kk], axis=-1).astype(float)  # affine is identity
    mni_mm = native_mm + OFFSET
    img = nib.Nifti1Image(mni_mm.astype(np.float32), affine)
    p = tmp_path / "Conform2MNI_nonl.nii.gz"
    nib.save(img, p)
    return p


@pytest.fixture
def native_efield(tmp_path: Path) -> Path:
    img = nib.Nifti1Image(np.ones((12, 12, 12), dtype=np.float32), np.eye(4))
    p = tmp_path / "sub_magnE.nii.gz"
    nib.save(img, p)
    return p


class TestLoadWarp:
    def test_shapes(self, warp_path: Path) -> None:
        warp_img, warp_coords = load_warp(warp_path)
        assert warp_img.shape[:3] == (12, 12, 12)
        assert warp_coords.shape == (12 * 12 * 12, 3)

    def test_is_cached(self, warp_path: Path) -> None:
        a, _ = load_warp(warp_path)
        b, _ = load_warp(warp_path)
        assert a is b


class TestMniToNativeCoords:
    def test_recovers_the_offset(self, warp_path: Path) -> None:
        warp_img, warp_coords = load_warp(warp_path)
        target_native = np.array([4.0, 6.0, 5.0])
        mni = target_native + OFFSET
        got = mni_to_native_coords(list(mni), warp_img, warp_coords)
        assert np.allclose(got, target_native, atol=1.0)

    def test_returns_three_floats(self, warp_path: Path) -> None:
        warp_img, warp_coords = load_warp(warp_path)
        got = mni_to_native_coords([10.0, 0.0, 5.0], warp_img, warp_coords)
        assert len(got) == 3


class TestWarpMask:
    def test_mask_lands_on_subject_grid(self, warp_path: Path) -> None:
        warp_img, warp_coords = load_warp(warp_path)
        mni_mask = nib.Nifti1Image(np.ones((20, 20, 20), dtype=np.uint8), np.eye(4))
        out = warp_mni_mask_to_native(mni_mask, warp_img, warp_coords)
        assert out.shape == (12, 12, 12)

    def test_stays_binary(self, warp_path: Path) -> None:
        warp_img, warp_coords = load_warp(warp_path)
        data = np.zeros((20, 20, 20), dtype=np.uint8)
        data[8:14, 8:14, 8:14] = 1
        out = warp_mni_mask_to_native(
            nib.Nifti1Image(data, np.eye(4)), warp_img, warp_coords
        )
        assert set(np.unique(out.get_fdata())) <= {0.0, 1.0}


class TestCoordsSpaceContract:
    def test_space_is_recorded(self, native_efield: Path) -> None:
        assert EField(native_efield).space == "native"
        assert EField(native_efield, space="mni").space == "mni"

    def test_invalid_space_rejected(self, native_efield: Path) -> None:
        with pytest.raises(ValueError, match="space must be"):
            EField(native_efield, space="talairach")

    def test_invalid_coords_space_rejected(self, native_efield: Path) -> None:
        with pytest.raises(ValueError, match="coords_space must be"):
            EField(native_efield).get_roi(coords=[0, 0, 0], coords_space="talairach")

    def test_mni_coords_without_segmentation_explains_why(
        self, native_efield: Path
    ) -> None:
        """The old failure was an opaque empty-mask error further downstream."""
        acc = EField(native_efield)
        with pytest.raises(ValueError, match="set_segmentation"):
            acc.get_roi(coords=[5.0, 5.0, 5.0], coords_space="mni")

    def test_native_coords_need_no_segmentation(self, native_efield: Path) -> None:
        acc = EField(native_efield)
        roi = acc.get_roi(coords=[6.0, 6.0, 6.0], radius=3.0)
        assert roi.values.size > 0

    def test_default_is_the_volumes_own_space(self, native_efield: Path) -> None:
        """No coords_space given must not trigger warping (backward compatible)."""
        acc = EField(native_efield)
        roi = acc.get_roi(coords=[6.0, 6.0, 6.0], radius=3.0)
        assert roi.values.size > 0
