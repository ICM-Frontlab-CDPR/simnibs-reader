"""
postprocess.py
--------------
Pure-function helpers for outlier removal on 1-D value arrays.

These are used internally by :meth:`ROIResult.postprocess` but can also
be called standalone on any numpy array.
"""

from __future__ import annotations

import numpy as np


def remove_outliers(
    values: np.ndarray,
    method: str = "iqr",
    z_thresh: float = 3.5,
    iqr_factor: float = 1.5,
    portion: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Filter outliers on a 1-D vector.

    Parameters
    ----------
    values : np.ndarray
        Input values.
    method : {"iqr", "z"}
        ``"iqr"`` — keep values within ``[Q1 - factor·IQR, Q3 + factor·IQR]``.
        ``"z"``   — keep values with robust |z-score| ≤ *z_thresh*.
    z_thresh : float
        Threshold for the robust z-score method (default 3.5).
    iqr_factor : float
        Multiplier for IQR fences (default 1.5).
    portion : float or None
        If set, additionally trim to the central *portion*
        (e.g. ``0.95`` keeps the 2.5 %–97.5 % range).

    Returns
    -------
    filtered : np.ndarray
        Copy of *values* with outliers set to ``NaN``.
    keep : np.ndarray
        Boolean mask of retained values.
    """
    vals = np.asarray(values, dtype=np.float64)
    keep = np.ones(vals.shape, dtype=bool)

    # Central portion trim
    if portion is not None:
        if not (0.0 < portion <= 1.0):
            raise ValueError("portion must be in (0, 1]")
        lo_q = (1.0 - portion) / 2.0
        hi_q = 1.0 - lo_q
        lo, hi = np.quantile(vals, [lo_q, hi_q])
        keep &= (vals >= lo) & (vals <= hi)

    # IQR or robust z-score
    if method.lower() == "iqr":
        q1, q3 = np.quantile(vals, [0.25, 0.75])
        iqr = q3 - q1
        keep &= (vals >= q1 - iqr_factor * iqr) & (vals <= q3 + iqr_factor * iqr)
    elif method.lower() == "z":
        med = np.median(vals)
        mad = np.median(np.abs(vals - med))
        if mad == 0:
            keep &= np.isfinite(vals)
        else:
            robust_z = 0.6745 * (vals - med) / mad
            keep &= np.abs(robust_z) <= z_thresh
    else:
        raise ValueError(f"method must be 'iqr' or 'z', got '{method}'")

    filtered = vals.copy()
    filtered[~keep] = np.nan
    return filtered, keep
