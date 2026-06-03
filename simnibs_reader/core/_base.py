"""
_base.py
--------
Abstract base class shared by all SimNIBS folder readers.

Design principles
~~~~~~~~~~~~~~~~~
* **No SimNIBS dependency** — works with plain file-system operations.
* **Fail-fast** — ``__init__`` calls ``_validate()`` immediately so the user
  gets an actionable error before any heavy I/O.
* **Lazy everything else** — actual NIfTI/mesh loading happens via
  ``@cached_property`` in subclasses.
"""

from __future__ import annotations

from pathlib import Path


class SimNIBSResult:
    """Abstract base for all SimNIBS folder types."""

    # Subclasses should set a human-readable label for error messages.
    _kind: str = "SimNIBS folder"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"{self._kind} not found: {self.path}")
        if not self.path.is_dir():
            raise NotADirectoryError(f"Expected a directory, got a file: {self.path}")
        self._validate()

    # ------------------------------------------------------------------
    # Validation (subclass hook)
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Check that the folder has the expected structure.

        Subclasses **must** override this and raise ``ValueError`` with a
        clear message if the folder layout is wrong.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # File-discovery helpers
    # ------------------------------------------------------------------

    def _find(self, pattern: str) -> list[Path]:
        """Glob for files matching *pattern* under ``self.path`` (sorted)."""
        return sorted(self.path.glob(pattern))

    def _find_one(self, pattern: str) -> Path:
        """Return the first match or raise ``FileNotFoundError``."""
        results = self._find(pattern)
        if not results:
            raise FileNotFoundError(
                f"No file matching '{pattern}' in {self.path}"
            )
        return results[0]

    # ------------------------------------------------------------------
    # Debug / exploration
    # ------------------------------------------------------------------

    def tree(self, max_depth: int = 3, _prefix: str = "", _depth: int = 0) -> str:
        """Return a pretty-printed directory tree (for debug / exploration).

        Parameters
        ----------
        max_depth : int
            Maximum recursion depth (default 3).
        """
        lines: list[str] = []
        if _depth == 0:
            lines.append(str(self.path))

        if _depth >= max_depth:
            return "\n".join(lines)

        try:
            entries = sorted(self.path.iterdir()) if _depth == 0 else sorted(Path(_prefix).iterdir()) if _prefix else []
        except PermissionError:
            return "\n".join(lines)

        # For recursive calls we need the actual directory
        target = self.path if _depth == 0 else Path(_prefix)
        try:
            entries = sorted(target.iterdir())
        except PermissionError:
            return "\n".join(lines)

        dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file() and not e.name.startswith(".")]
        all_entries = dirs + files

        for i, entry in enumerate(all_entries):
            connector = "└── " if i == len(all_entries) - 1 else "├── "
            indent = "│   " * _depth
            lines.append(f"{indent}{connector}{entry.name}")
            if entry.is_dir() and _depth < max_depth - 1:
                subtree = self.tree(
                    max_depth=max_depth, _prefix=str(entry), _depth=_depth + 1
                )
                if subtree:
                    lines.append(subtree)

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self.path}')"
