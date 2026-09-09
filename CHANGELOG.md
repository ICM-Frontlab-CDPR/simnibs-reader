# Changelog

All notable changes to **simnibs-reader** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-07-20

First consolidated release of the three-layer reader (`core/` → `nifti/` → `io/`)
after the debugging and hardening pass on ROI extraction.

### Fixed
- **`EField.get_roi` ↔ `ROI` contract.** `get_roi` now extracts 1-D values with
  `masking.apply_mask` and returns `ROI(values=, mask_img=, efield=)` with the
  correct argument order (previously raised `TypeError` from an inverted contract).
- **niimg vs `EField` type mismatches.** All nilearn calls
  (`resample_to_img`, `smooth_img`, `apply_mask`) now receive `EField.img`
  (a `Nifti1Image`) instead of the `EField` wrapper.
- **4-D singleton volumes.** SimNIBS NIfTIs often carry a trailing
  `(X, Y, Z, 1)` axis; a shared `ROI._fdata_3d` helper (`np.squeeze` + 3-D
  assert) makes every boolean mask operation broadcast-safe, and `apply_mask`
  outputs are squeezed to 1-D.
- **ROI methods placement.** `filter_tissue`, `complement`,
  `_resolve_brain_mask`, `_build_tissue_mask`, `_intersect_masks` now live on
  `ROI` (they operate on ROI state), not on `EField`.
- **`remove_outliers`** is a `@staticmethod` (was implicitly binding `self`).

### Changed
- **`EField.get_roi` signature** is keyword-only and unified across callers:
  `get_roi(*, mask=None, coords=None, radius=10.0, atlas=None, region=None)`.
- **Statistics are NaN-aware** end-to-end (`compute_stats`, `ROI.stats`), so
  outlier removal that sets values to `NaN` no longer skews summaries.

### Added
- **`EField.data`** property returning `get_fdata(dtype=float32)`.
- **`ROI.save` / `ROI.save_nifti`** thin wrappers over `io.export.save_results`
  and `io.nifti.save_nifti`.
- **`SimulationResult.available_fields`** grouping NIfTI fields by space
  (`{"mni": [...], "native": [...]}`).

### Notes
- No SimNIBS runtime dependency: the reader remains pure NIfTI/file-system.
- `h5py` stays an optional extra (`pip install simnibs-reader[opti]`).

## [0.1.0]

- Initial three-layer reader: `SimulationResult`, `SegmentationResult`,
  `OptimizationResult`; `EField` / `ROI` in `nifti/`; TSV/CSV export in `io/`.
