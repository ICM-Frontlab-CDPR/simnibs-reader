"""
labels.py
---------
Tissue label resolution for SimNIBS segmentations.

Provides:
- ``_SIMNIBS_LUT``  : default tissue name → label value mapping.
- ``parse_lut()``   : parse a SimNIBS ``*_LUT.txt`` into the same dict format.
- ``resolve_tissue_value()`` : look up a tissue name (case-insensitive) and
  return its integer label value.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Default SimNIBS tissue LUT
# Label values follow the SimNIBS/charm convention:
#   https://simnibs.github.io/simnibs/build/html/documentation/output_files.html
# ---------------------------------------------------------------------------

_SIMNIBS_LUT: dict[str, int] = {
    "White-Matter":           1,
    "Gray-Matter":            2,
    "CSF":                    3,
    "Bone":                   4,
    "Skin":                   5,
    "Eye":                    6,
    "Compact-Bone":           7,
    "Spongy-Bone":            8,
    "Blood":                  9,
    "Muscle":                10,
}


# ---------------------------------------------------------------------------
# LUT file parser
# ---------------------------------------------------------------------------


def parse_lut(lut_path: str | Path) -> dict[str, int]:
    """Parse a SimNIBS ``*_LUT.txt`` file into a ``{name: value}`` dict.

    The file is expected to contain lines like::

        1  White-Matter  255  255  255  0
        2  Gray-Matter   205  62   78   0
        …

    Lines that are blank or start with ``#`` are ignored.
    The first column is the integer label value, the second is the name.
    Extra columns (RGB, alpha) are silently ignored.

    Parameters
    ----------
    lut_path : str or Path
        Path to the lookup-table text file.

    Returns
    -------
    dict[str, int]
        Mapping from tissue name to integer label value.

    Raises
    ------
    FileNotFoundError
        If *lut_path* does not exist.
    ValueError
        If a line cannot be parsed (wrong number of columns or bad int).
    """
    lut_path = Path(lut_path)
    if not lut_path.exists():
        raise FileNotFoundError(f"LUT file not found: {lut_path}")

    result: dict[str, int] = {}
    for lineno, raw in enumerate(lut_path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:  # noqa: PLR2004
            raise ValueError(
                f"LUT parse error at line {lineno}: expected at least "
                f"2 columns (value name …), got: {raw!r}"
            )
        try:
            value = int(parts[0])
        except ValueError:
            raise ValueError(
                f"LUT parse error at line {lineno}: first column is not an "
                f"integer: {parts[0]!r}"
            )
        name = parts[1]
        result[name] = value

    return result


# ---------------------------------------------------------------------------
# Resolution helper
# ---------------------------------------------------------------------------


def resolve_tissue_value(
    tissue: str,
    lut: dict[str, int] | None = None,
) -> int:
    """Return the integer label value for *tissue* (case-insensitive look-up).

    Parameters
    ----------
    tissue : str
        Tissue name, e.g. ``"Gray-Matter"`` or ``"gray-matter"``.
    lut : dict[str, int] or None
        Custom LUT.  Falls back to ``_SIMNIBS_LUT`` when ``None``.

    Returns
    -------
    int
        Integer voxel value in the label image.

    Raises
    ------
    ValueError
        If *tissue* is not present in the LUT.
    """
    effective_lut = lut if lut is not None else _SIMNIBS_LUT
    tissue_lower = tissue.lower()

    for name, val in effective_lut.items():
        if name.lower() == tissue_lower:
            return val

    raise ValueError(
        f"Tissue '{tissue}' not found in LUT. "
        f"Available tissues: {list(effective_lut.keys())}"
    )
