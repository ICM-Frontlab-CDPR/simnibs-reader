"""E-field loading, ROI extraction, post-processing, and statistics."""

from .efield import EField
from .roi import ROI
# from .postprocess import remove_outliers
# from .stats import compute_stats

__all__ = [
    "EField",
    "ROI",
    # "remove_outliers",
    # "compute_stats",
]


#le module est à renommer "nifti" et nom "efield"