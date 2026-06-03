"""
export.py
---------
Export statistics dictionaries and DataFrames to TSV / CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# Mapping of stat keys available in compute_stats()
_ALL_METRICS = ["mean", "median", "std", "min", "max", "p5", "p95", "n_voxels"]


def save_results(
    stats: dict,
    path: str | Path,
    metrics: list[str] | None = None,
    format: str = "tsv",
    extra_cols: dict | None = None,
) -> Path:
    """Export a statistics dict to a TSV or CSV file.

    Parameters
    ----------
    stats : dict
        Output of ``compute_stats()`` (or any flat dict of scalar values).
    path : str or Path
        Destination file path.  The correct extension (``.tsv`` / ``.csv``)
        is appended automatically if the path has no suffix.
    metrics : list of str, optional
        Subset of keys to include (default: all keys in *stats*).
    format : {"tsv", "csv"}
        Field delimiter.  ``"tsv"`` uses ``\\t``, ``"csv"`` uses ``,``.
    extra_cols : dict, optional
        Additional columns prepended to the output
        (e.g. ``{"subject": "sub-01", "condition": "fef"}``).

    Returns
    -------
    Path
        The written file path.
    """
    path = Path(path)

    # Auto-add extension
    sep_char = "\t" if format == "tsv" else ","
    ext = ".tsv" if format == "tsv" else ".csv"
    if path.suffix not in {".tsv", ".csv"}:
        path = path.with_suffix(ext)

    # Filter requested metrics
    row = dict(extra_cols or {})
    keys = metrics if metrics is not None else list(stats.keys())
    for k in keys:
        if k in stats:
            row[k] = stats[k]

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(path, sep=sep_char, index=False)
    return path


def save_dataframe(
    df: pd.DataFrame,
    path: str | Path,
    format: str = "tsv",
) -> Path:
    """Save a DataFrame to TSV or CSV.

    Parameters
    ----------
    df : pd.DataFrame
    path : str or Path
    format : {"tsv", "csv"}
    """
    path = Path(path)
    sep_char = "\t" if format == "tsv" else ","
    ext = ".tsv" if format == "tsv" else ".csv"
    if path.suffix not in {".tsv", ".csv"}:
        path = path.with_suffix(ext)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=sep_char, index=False)
    return path
