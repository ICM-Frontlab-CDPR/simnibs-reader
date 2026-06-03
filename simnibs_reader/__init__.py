"""
simnibs-reader
==============

Lightweight reader for SimNIBS output directories.

Quick start
-----------
>>> import simnibs_reader as snr
>>> sim = snr.simulation("path/to/simulation_folder")
>>> sim.magnE.data  # lazy-loaded NIfTI array
"""

from __future__ import annotations

from .core.simulation import SimulationResult
from .core.segmentation import SegmentationResult
from .core.optimization import OptimizationResult

__version__ = "0.1.0"


# ── Public factory functions ──────────────────────────────────────────────


def simulation(path: str) -> SimulationResult:
    """Load a SimNIBS simulation output folder.

    Parameters
    ----------
    path : str or Path
        Path to the simulation directory (contains ``mni_volumes/``,
        ``subject_volumes/``, ``fields_summary.txt``, etc.).
    """
    return SimulationResult(path)


def segmentation(path: str) -> SegmentationResult:
    """Load a SimNIBS head-model folder (``m2m_<subID>``).

    Parameters
    ----------
    path : str or Path
        Path to the ``m2m_*`` directory produced by ``charm`` / ``headreco``.
    """
    return SegmentationResult(path)


def optimization(path: str) -> OptimizationResult:
    """Load a SimNIBS optimization / leadfield folder.

    Parameters
    ----------
    path : str or Path
        Path to the optimization output directory.
    """
    return OptimizationResult(path)
