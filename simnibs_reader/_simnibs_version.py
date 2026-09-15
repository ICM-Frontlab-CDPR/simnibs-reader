"""
SimNIBS version support.

This reader navigates SimNIBS output folders by their layout, not by calling
SimNIBS itself. That layout is stable across 4.5 and 4.6 — the 4.6 changes are
internal to charm (new probabilistic atlas, AI-based surface reconstruction,
numpy 2) and do not move or rename any output file.

Reference trees for each supported version live in ``_simnibs-tree/``.

One 4.6 change does affect interpretation rather than location: interfaces to
internal air cavities now get their own tissue number in ``final_tissues``.
Anything treating "label > 0" as brain will include those voxels. See
:data:`AIR_CAVITY_INTERFACE_NOTE`.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

__all__ = [
    "SUPPORTED_VERSIONS",
    "detect_version",
    "warn_if_unsupported",
]

#: Layouts this reader has been checked against. Versions sharing a layout are
#: listed together — a folder produced by any of them reads identically.
SUPPORTED_VERSIONS: tuple[str, ...] = ("4.5", "4.6")

AIR_CAVITY_INTERFACE_NOTE = (
    "SimNIBS 4.6 gives interfaces to internal air cavities their own tissue "
    "number in final_tissues. Masks built as 'any label > 0' therefore cover "
    "slightly more than in 4.5."
)

# "SimNIBS 4.6.0", "simnibs version 4.5.1", "SIMNIBS_VERSION = 4.6.0", ...
_VERSION_RE = re.compile(r"simnibs[^0-9]{0,20}(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)

# Cheapest first; charm writes its banner into the log, settings.ini is smaller
# but does not always carry a version.
_VERSION_SOURCES: tuple[str, ...] = (
    "settings.ini",
    "charm_log.html",
    "charm_report.html",
)


def detect_version(m2m_dir: str | Path) -> str | None:
    """Read the SimNIBS version that produced an ``m2m_<sub>/`` folder.

    Parameters
    ----------
    m2m_dir : str or Path
        Path to the segmentation folder.

    Returns
    -------
    str or None
        Version as written by SimNIBS (e.g. ``"4.6.0"``), or ``None`` when no
        source in the folder records it. ``None`` is not an error: older or
        hand-assembled folders simply may not say.

    Notes
    -----
    Only the files SimNIBS itself writes are consulted; nothing is executed and
    SimNIBS does not need to be installed.
    """
    m2m_dir = Path(m2m_dir)
    for name in _VERSION_SOURCES:
        f = m2m_dir / name
        if not f.is_file():
            continue
        try:
            text = f.read_text(errors="ignore")
        except OSError:  # pragma: no cover — unreadable file, try the next
            continue
        m = _VERSION_RE.search(text)
        if m:
            return m.group(1)
    return None


def warn_if_unsupported(m2m_dir: str | Path) -> str | None:
    """Detect the version and warn when it is outside :data:`SUPPORTED_VERSIONS`.

    Parameters
    ----------
    m2m_dir : str or Path
        Path to the segmentation folder.

    Returns
    -------
    str or None
        The detected version, as :func:`detect_version` returns it.

    Notes
    -----
    Warns rather than raises. An unknown version usually still reads correctly —
    the layout has been stable across 4.x — so blocking would be worse than
    saying so once.
    """
    version = detect_version(m2m_dir)
    if version is None:
        return None
    if not version.startswith(SUPPORTED_VERSIONS):
        warnings.warn(
            f"This folder was produced by SimNIBS {version}; simnibs-reader "
            f"has been checked against {', '.join(SUPPORTED_VERSIONS)}. "
            "Reading will be attempted anyway — the output layout has been "
            "stable across 4.x. Please report any mismatch.",
            UserWarning,
            stacklevel=3,
        )
    return version
