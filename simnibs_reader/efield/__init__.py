"""E-field loading, ROI extraction, post-processing, and statistics."""

from .accessor import EFieldAccessor
from .roi import ROIExtractor, ROIResult
from .postprocess import remove_outliers
from .stats import compute_stats

__all__ = [
    "EFieldAccessor",
    "ROIExtractor",
    "ROIResult",
    "remove_outliers",
    "compute_stats",
]
