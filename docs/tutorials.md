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


---
---
---

## Folder Types

| Folder             | Contents                                   |
| ------------------ | ------------------------------------------ |
| `m2m_<subject>/` | Head model, segmentation labels, MRI preps |
| `simulation/`    | Per-condition e-field NIfTI outputs        |
| `optimization/`  | Optimized field maps and electrode configs |

> **Note — SimNIBS-BIDS structure** *(under consideration)*
> A BIDS-inspired naming convention for multi-subject / multi-condition experiments
> is being evaluated. The hierarchy `electrodes → currents → conductivities` follows
> SimNIBS data structures and will be formalized in a future release.

