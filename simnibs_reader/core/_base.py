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

    def tree(self, max_depth: int = 3) -> str:
        """Return a pretty-printed directory tree (for debug / exploration).

        Parameters
        ----------
        max_depth : int
            Maximum recursion depth (default 3).
        """

        def _walk(directory: Path, prefix: str, depth: int) -> list[str]:
            if depth >= max_depth:
                return []
            try:
                entries = sorted(directory.iterdir())
            except PermissionError:
                return []

            dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
            files = [e for e in entries if e.is_file() and not e.name.startswith(".")]
            items = dirs + files
            lines: list[str] = []

            for i, entry in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    lines.extend(_walk(entry, prefix + extension, depth + 1))

            return lines

        header = [self.path.name]
        header.extend(_walk(self.path, "", 0))
        return "\n".join(header)

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self.path}')"
