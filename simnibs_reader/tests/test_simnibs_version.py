"""Version detection for the SimNIBS folders being read.

The reader navigates SimNIBS output by layout, so a user needs to know which
SimNIBS versions that layout was checked against — and to be told when their
data comes from something else.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from pathlib import Path

import pytest

from simnibs_reader._simnibs_version import (
    SUPPORTED_VERSIONS,
    detect_version,
    warn_if_unsupported,
)


@contextmanager
def no_warning():
    """Any warning raised inside becomes a test failure."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


def _m2m(tmp_path: Path, filename: str = "settings.ini", text: str = "") -> Path:
    d = tmp_path / "m2m_0001"
    d.mkdir(exist_ok=True)
    (d / filename).write_text(text)
    return d


class TestDetectVersion:
    def test_from_settings_ini(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "[general]\nsimnibs_version = 4.6.0\n")
        assert detect_version(d) == "4.6.0"

    def test_from_charm_log(self, tmp_path: Path) -> None:
        d = tmp_path / "m2m_0002"
        d.mkdir()
        (d / "charm_log.html").write_text("<h1>SimNIBS 4.5.1 charm report</h1>")
        assert detect_version(d) == "4.5.1"

    def test_two_digit_version(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "SimNIBS version 4.6")
        assert detect_version(d) == "4.6"

    def test_case_insensitive(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "SIMNIBS_VERSION = 4.6.0")
        assert detect_version(d) == "4.6.0"

    def test_none_when_absent(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "[general]\nnothing here\n")
        assert detect_version(d) is None

    def test_none_on_empty_folder(self, tmp_path: Path) -> None:
        d = tmp_path / "m2m_empty"
        d.mkdir()
        assert detect_version(d) is None

    def test_missing_folder_is_not_an_error(self, tmp_path: Path) -> None:
        assert detect_version(tmp_path / "nope") is None


class TestWarnIfUnsupported:
    @pytest.mark.parametrize("version", ["4.5.0", "4.6.0", "4.6"])
    def test_supported_versions_are_silent(
        self, tmp_path: Path, version: str
    ) -> None:
        d = _m2m(tmp_path, "settings.ini", f"simnibs_version = {version}")
        with no_warning():
            assert warn_if_unsupported(d) == version

    def test_unknown_version_warns_but_returns(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "simnibs_version = 5.0.0")
        with pytest.warns(UserWarning, match="checked against"):
            assert warn_if_unsupported(d) == "5.0.0"

    def test_older_major_warns(self, tmp_path: Path) -> None:
        d = _m2m(tmp_path, "settings.ini", "simnibs_version = 3.2.6")
        with pytest.warns(UserWarning):
            warn_if_unsupported(d)

    def test_undetected_version_does_not_warn(self, tmp_path: Path) -> None:
        """Absence of a version is not evidence of an unsupported one."""
        d = _m2m(tmp_path, "settings.ini", "nothing")
        with no_warning():
            assert warn_if_unsupported(d) is None


class TestSupportedVersionsDeclared:
    def test_46_is_supported(self) -> None:
        assert "4.6" in SUPPORTED_VERSIONS

    def test_reference_tree_exists_for_each(self) -> None:
        """Documentation only — not packaged, so skip outside a checkout."""
        trees = Path(__file__).resolve().parents[1] / "_simnibs-tree"
        if not trees.is_dir():
            pytest.skip("reference trees are not shipped in the distribution")
        for v in SUPPORTED_VERSIONS:
            assert (trees / v).is_dir(), f"no reference tree for {v}"
