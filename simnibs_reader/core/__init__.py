"""Core result classes for SimNIBS output directories."""

from .optimization import OptimizationResult
from .segmentation import SegmentationResult
from .simulation import SimulationResult

__all__ = ["OptimizationResult", "SegmentationResult", "SimulationResult"]
