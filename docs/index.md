---
hide:
  - navigation
---
# simnibs-reader

!!! info "Documentation for version 0.4.0"
    See the
    [changelog](https://github.com/ICM-Frontlab-CDPR/simnibs-reader/blob/main/CHANGELOG.md).

**Load, extract, clean and analyze SimNIBS e-field NIfTI outputs — in one line.**

`simnibs-reader` is a lightweight Python library that turns SimNIBS simulation
results into analysis-ready ROI data with built-in outlier removal, smoothing,
statistics and export.

---

## Installation

```bash
pip install simnibs-reader
```


---

## Quick Example

```python
import simnibs_reader as snr

sim = snr.simulation("/path/to/simnibs/simulation")

# Extract ROI, clean, get stats — 3 lines
roi = sim.magnE.get_roi(mask="my_roi.nii.gz")
cleaned = roi.postprocess(smooth_fwhm=2.0, outlier_method="iqr")
cleaned.stats()
# {'mean': 0.142, 'median': 0.138, 'std': 0.031, 'max': 0.241, ...}
```

Targets given in MNI coordinates work on native-space volumes too — attach the
segmentation and the deformation field does the rest:

```python
sim.set_segmentation(snr.segmentation("/path/to/m2m_0001"))
roi = sim.magnE_native.get_roi(coords=[28, -8, 54], coords_space="mni")
```

---


## Ecosystem

<div class="grid cards" markdown>

-   :fontawesome-solid-brain:{ .lg .middle } **SimNIBS**

    ---

    The core simulation platform for non-invasive brain stimulation.

    [:octicons-arrow-right-24: Documentation ](https://simnibs.github.io/simnibs/build/html/index.html)

-   :material-package-variant:{ .lg .middle } **simnibs-modular**

    ---

    Modular pipeline components for SimNIBS workflows.

    [:octicons-arrow-right-24: GitHub Pages](https://ICM-Frontlab-CDPR.github.io/simnibs-modular/)
    · [:octicons-mark-github-16: Repo](https://github.com/ICM-Frontlab-CDPR/simnibs-modular)

-   :material-chart-bar:{ .lg .middle } **simnibs-analyze**

    ---

    Statistical analysis tools for SimNIBS outputs.

    [:octicons-arrow-right-24: GitHub Pages](https://ICM-Frontlab-CDPR.github.io/simnibs-analyze/)
    · [:octicons-mark-github-16: Repo](https://github.com/ICM-Frontlab-CDPR/simnibs-analyze)

-   :material-lightning-bolt:{ .lg .middle } **OptiStims**

    ---

    End-to-end automated stroke lesion-aware tDCS pipeline.

    [:octicons-arrow-right-24: GitHub Pages](https://ICM-Frontlab-CDPR.github.io/OptiStims/)
    · [:octicons-mark-github-16: Repo](https://github.com/ICM-Frontlab-CDPR/OptiStims)

</div>
<!-- ``` -->

