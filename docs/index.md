---
hide:
  - navigation
---
# simnibs-reader

**Load, extract, clean and analyze SimNIBS e-field NIfTI outputs — in one line.**

`simnibs-reader` is a lightweight Python library that turns SimNIBS simulation
results into analysis-ready ROI data with built-in outlier removal, smoothing,
statistics and export.

---

## Quick Example

```python
from simnibs_reader import SimNIBSResults

results = SimNIBSResults("/path/to/simnibs/output")
efield = results.efield()

# Extract ROI, clean, get stats — 3 lines
roi = efield.get_roi(mask="my_roi.nii.gz")
cleaned = roi.postprocess(smooth_fwhm=2.0, outlier_method="iqr")
cleaned.stats()
# {'mean': 0.142, 'median': 0.138, 'std': 0.031, 'max': 0.241, ...}
```

---

## Installation

```bash
pip install simnibs-reader
```

[:material-download: Getting Started](getting-started.md){ .md-button .md-button--primary }
[:material-notebook: Tutorials](tutorials.md){ .md-button }
[:material-api: API Reference](api/index.md){ .md-button }

```

---

```markdown docs/tutorials.md
# Tutorials

Download the Jupyter notebooks and follow along with your own SimNIBS data.

---

## :material-notebook: Available Notebooks

### 1. BIDS Integration Tutorial

How to use `simnibs-reader` with BIDS-formatted datasets.

[:material-download: Download simnibs-bids-tutorial.ipynb](example/simnibs-bids-tutorial.ipynb){ .md-button .md-button--primary download }

---

### 2. SNR Optimization Tutorial

Optimize signal-to-noise ratio in your e-field analysis pipeline.

[:material-download: Download snr-optimization-tutorial.ipynb](example/snr-optimization-tutorial.ipynb){ .md-button .md-button--primary download }

---

### 3. SNR Simulation Tutorial

Simulate and evaluate SNR across stimulation configurations.

[:material-download: Download snr-simulation-tutorial.ipynb](example/snr-simulation-tutorial.ipynb){ .md-button .md-button--primary download }

---

!!! tip "Running the notebooks"
    ```bash
    pip install simnibs-reader jupyterlab nibabel nilearn
    jupyter lab
    ```
```

---

```markdown
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

```

---

```markdown docs/api/index.md
# API Reference

## Core Classes

| Class | Description |
|---|---|
| [`EFieldAccessor`](accessor.md) | Load and navigate SimNIBS e-field volumes |
| [`ROIResult`](roi.md) | Region-of-interest extraction, cleaning, stats, export |

## Functions

| Function | Description |
|---|---|
| [`remove_outliers`](postprocess.md) | IQR / Z-score outlier removal |
| [`compute_stats`](stats.md) | Descriptive statistics on 1-D arrays |
```

---

```markdown
# EFieldAccessor

::: simnibs_reader.efield.accessor.EFieldAccessor
    options:
      members:
        - __init__
        - get_roi
        - list_fields
      show_source: true
```

```markdown
# ROIResult

::: simnibs_reader.efield.roi.ROIResult
    options:
      members:
        - __init__
        - stats
        - postprocess
        - save
        - save_nifti
        - n_voxels
      show_source: true
```

```markdown
# Postprocessing

::: simnibs_reader.efield.postprocess.remove_outliers
    options:
      show_source: true
```

```markdown
# Statistics

::: simnibs_reader.efield.stats.compute_stats
    options:
      show_source: true
```

---

## 🔗 Ecosystem

<div class="grid cards" markdown>

- :brain:{ .lg .middle } **SimNIBS**

  ---

  The core simulation platform for non-invasive brain stimulation.

  [:octicons-arrow-right-24: simnibs.github.io](https://simnibs.github.io/simnibs/build/html/index.html)
- 📦{ .lg .middle } **simnibs-modular**

  ---

  Modular pipeline components for SimNIBS workflows.

  [:octicons-arrow-right-24: GitHub Pages](https://ICM-Frontlab-CDPR.github.io/simnibs-modular/)
  · [:octicons-mark-github-16: Repo](https://github.com/ICM-Frontlab-CDPR/simnibs-modular)
- 📊{ .lg .middle } **simnibs-analyze**

  ---

  Statistical analysis tools for SimNIBS outputs.

  [:octicons-arrow-right-24: GitHub Pages](https://ICM-Frontlab-CDPR.github.io/simnibs-analyze/)
  · [:octicons-mark-github-16: Repo](https://github.com/ICM-Frontlab-CDPR/simnibs-analyze)

</div>

---

## ⚡️ Automated Stroke Pipeline

![Stroke tDCS Pipeline](assets/pipeline-stroke.svg){ width="100%" }

*End-to-end automated pipeline for stroke lesion-aware tDCS simulation and analysis.*
