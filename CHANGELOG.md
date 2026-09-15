# Changelog

All notable changes to **simnibs-reader** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] — 2026-09-15

### Added
- **`SegmentationResult.simnibs_version`** — reads which SimNIBS version wrote
  an `m2m_<sub>/` folder, from charm's own log files. SimNIBS is never called
  and need not be installed. Returns `None` when the folder records no version,
  which is not an error.
- **`SUPPORTED_VERSIONS`** in `simnibs_reader._simnibs_version`, declaring the
  layouts the reader has been checked against: **4.5 and 4.6**. A folder from
  anything else warns once on access, rather than failing — the layout has been
  stable across 4.x, so refusing would be worse than saying so.
- Reference tree for **4.6** under `_simnibs-tree/`, plus a README explaining
  the per-version layout. A test enforces that every supported version has one.
- Documentation page on version compatibility.

### Notes
SimNIBS 4.6 moves and renames nothing: its changes are internal to charm (new
probabilistic atlas, AI-based cortical surface reconstruction, new affine
registration, numpy 2). The 4.5 and 4.6 reference trees are identical.

One 4.6 change alters interpretation rather than location: interfaces to
internal air cavities now carry their own tissue number in `final_tissues`, so
a mask built as *any label > 0* — what `ROI.complement()` uses — covers
slightly more than under 4.5. Focality ratios are therefore not strictly
comparable across a 4.5/4.6 boundary. This is documented, not worked around:
silently remapping labels would hide a real difference in the data.

## [0.3.0] — 2026-09-15

### Added
- **`EField.get_roi(coords_space=...)`** — state which space `coords=` or
  `atlas=` are expressed in. Set `coords_space="mni"` on a native-space volume
  and the target is warped onto the subject grid using the SimNIBS deformation
  field from `m2m_<sub>/toMNI/`. Requires an attached segmentation.
- **`EField.space`** — volumes now know whether they are native or MNI.
  `SimulationResult` sets it on all eight accessors.
- **`simnibs_reader.nifti._warp`** — `load_warp`, `mni_to_native_coords` and
  `warp_mni_mask_to_native`, with the deformation field cached per subject.

### Fixed
- **MNI coordinates on a native volume silently produced an empty ROI.**
  `_from_sphere` mapped world coordinates through `inv(affine)`, assuming they
  were already in the volume's own space, so an MNI target landed outside the
  head. The only symptom was a downstream nilearn error, *"The mask is invalid
  as it is empty: it masks all data"*, which pointed nowhere near the cause.
  Requesting a warp without an attached segmentation now fails immediately with
  a message naming `set_segmentation`.
- **`ROI.complement()` picked the wrong tissue map in MNI space.** It always
  read `final_tissues` (subject space); on an MNI e-field that mask is on the
  wrong grid. It now selects `final_tissues_mni` based on the e-field's space.
- **`scipy` was used but undeclared** — now a declared dependency.

### Changed
- Atlas-based ROIs on a native volume are warped automatically, since atlases
  are only defined in MNI space.

### Migration
`coords_space` defaults to the volume's own space, so existing calls behave
exactly as before. Native-space pipelines passing MNI coordinates were silently
broken and should now pass `coords_space="mni"`.

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
