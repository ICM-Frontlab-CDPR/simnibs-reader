#### simnibs-reader — usage examples
# No simnibs dependency needed — pure NIfTI-based reader.

import sys
sys.path.insert(0, '/Users/hippolyte.dreyfus/Documents/simnibs-reader')
import simnibs_reader as snr


# ── A — Load a results directory ─────────────────────────────────────────

# Simulation folder  (contains mni_volumes/, subject_volumes/, ...)
results = snr.simulation('/Users/hippolyte.dreyfus/Documents/0-tmp-simnibs-output/simulation_simulation_fef_hemianotacs_5626899c')

# Optimization / leadfield folder
# results = snr.optimization('path/to/optimization_folder')

# Segmentation folder  (m2m_<subID>/)
# results = snr.segmentation('/Users/hippolyte.dreyfus/Documents/0-tmp-simnibs-output/m2m_0001')


# Quick exploration
print(results)                   # SimulationResult('...')
print(results.tree())            # pretty directory tree
print(results.sim_id)            # e.g. '0001_TDCS_1'
print(results.available_fields)  # {'mni': [...], 'native': [...]}


# ── B — Access an e-field NIfTI (lazy — not loaded until .data) ──────────

efield = results.magnE           # MNI space  (*_MNI_magnE.nii.gz)
efield = results.magnE_native    # subject space (*_magnE.nii.gz)
efield = results.magnJ           # current density magnitude (MNI)

print(efield)                    # EField('..._MNI_magnE.nii.gz')
print(efield.shape)              # (182, 218, 182)
print(efield.affine)             # 4x4 affine matrix
data = efield.data               # np.ndarray float32 — loaded here


# ── C — Extract an ROI ───────────────────────────────────────────────────

# Option 1 : existing binary NIfTI mask
roi = efield.get_roi(mask='path/to/roi_mask.nii.gz')

# Option 2 : sphere defined by MNI coordinates
roi = efield.get_roi(coords=[28, -8, 54], radius=10.0)

# Option 3 : atlas parcel (Phase 2 — not yet implemented)
# roi = efield.get_roi(atlas='harvard-oxford', region='Frontal Eye Fields')

print(roi)                       # ROI(n_voxels=523, mean=0.2341)
print(roi.stats())               # {'mean': ..., 'median': ..., 'std': ..., ...}


# ── D — Post-process ─────────────────────────────────────────────────────

cleaned = roi.postprocess(
    smooth_fwhm=2.0,             # Gaussian smoothing in mm (None to skip)
    outlier_method='iqr',        # 'iqr' or 'z'
    portion=None,                # e.g. 0.95 to trim to central 95%
)

print(cleaned)                   # CleanedResult(n_kept=501, mean=0.2289)
print(cleaned.stats())           # same keys as roi.stats()


# ── E — Save ─────────────────────────────────────────────────────────────

# Save stats to TSV
roi.save('results/sub01_fef_roi', metrics=['mean', 'median', 'std'], format='tsv')

# Save cleaned stats
cleaned.save(
    'results/sub01_fef_cleaned',
    metrics=['mean', 'median', 'std', 'n_voxels'],
    format='tsv',
)

# Save the cleaned NIfTI volume
cleaned.save_nifti('results/sub01_fef_cleaned.nii.gz')