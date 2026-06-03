"""Core result classes for SimNIBS output directories."""

from .simulation import SimulationResult
from .segmentation import SegmentationResult
from .optimization import OptimizationResult

__all__ = ["SimulationResult", "SegmentationResult", "OptimizationResult"]
