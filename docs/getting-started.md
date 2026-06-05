# Getting Started

## Installation

```bash
pip install simnibs-reader
```

## Basic Usage

```python
from simnibs_reader import SimNIBSResults

# Point to a SimNIBS output directory
results = SimNIBSResults("/path/to/simnibs/output")

# Access e-field data
efield = results.efield()

# Extract a region of interest
roi = efield.get_roi(mask="path/to/mask.nii.gz")
print(roi.stats())

# Clean and re-analyze
cleaned = roi.postprocess(smooth_fwhm=2.0, outlier_method="iqr")
print(cleaned.stats())

# Export
cleaned.save("results/", format="csv")
cleaned.save_nifti("results/cleaned_efield.nii.gz")
```