"""
stats.py
--------
Scalar statistics computed on e-field value arrays.

All public functions accept a 1-D ``np.ndarray`` and return plain
``dict`` / ``float`` — no nibabel or nilearn dependency here.
"""

from __future__ import annotations

import numpy as np


def compute_stats(values: np.ndarray) -> dict[str, float | int]:
    """Descriptive statistics for a 1-D array of e-field values.

    NaN and non-finite values are silently ignored.

    Parameters
    ----------
    values : np.ndarray
        1-D array (e.g. voxel values inside an ROI).

    Returns
    -------
    dict
        Keys: ``mean``, ``median``, ``std``, ``min``, ``max``,
        ``p5``, ``p95``, ``n_voxels``.
    """
    v = np.asarray(values, dtype=np.float64).ravel()
    v = v[np.isfinite(v)]

    if v.size == 0:
        return {
            "mean": np.nan,
            "median": np.nan,
            "std": np.nan,
            "min": np.nan,
            "max": np.nan,
            "p5": np.nan,
            "p95": np.nan,
            "n_voxels": 0,
        }

    return {
        "mean": float(np.mean(v)),
        "median": float(np.median(v)),
        "std": float(np.std(v)),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "p5": float(np.percentile(v, 5)),
        "p95": float(np.percentile(v, 95)),
        "n_voxels": int(v.size),
    }


def compute_ratio(
    intra_values: np.ndarray,
    extra_values: np.ndarray,
    method: str = "mean",
) -> float:
    """Compute the intra-ROI / extra-ROI e-field ratio.

    Parameters
    ----------
    intra_values, extra_values : np.ndarray
        1-D arrays of e-field values inside and outside the ROI.
    method : {"mean", "median"}
        Summary statistic used for numerator and denominator.

    Returns
    -------
    float
        Ratio.  Returns ``np.nan`` if *method* is unsupported or
        the denominator is near zero.
    """
    intra = np.asarray(intra_values, dtype=np.float64).ravel()
    extra = np.asarray(extra_values, dtype=np.float64).ravel()
    intra = intra[np.isfinite(intra)]
    extra = extra[np.isfinite(extra)]

    _agg = {"mean": np.mean, "median": np.median}
    fn = _agg.get(method)
    if fn is None:
        return np.nan

    num = float(fn(intra)) if intra.size > 0 else 0.0
    den = float(fn(extra)) if extra.size > 0 else 0.0

    if abs(den) < 1e-10:
        den = 1e-10
    return num / den
