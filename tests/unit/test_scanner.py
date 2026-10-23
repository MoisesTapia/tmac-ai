"""
Unit tests for Scanner — SRP orchestrator module.

Validates: Requirements 1.1, 9.2, 9.3, 9.4
"""
import textwrap
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from tmac.models.finding import ScanResult
from tmac.scanner import ScanError, Scanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_tf(directory: Path, name: str, content: str) -> Path:
    """Write a .tf file into directory and return its path."""
    f = directory / name
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


CLEAN_TF = """\
    resource "aws_s3_bucket" "private_bucket" {
      acl = "private"
    }
"""

PUBLIC_TF = """\
    resource "aws_s3_bucket" "public_bucket" {
      acl = "public-read"
    }
"""


# ---------------------------------------------------------------------------
# Basic contract tests
# ---------------------------------------------------------------------------

class TestScannerContract:
    def test_returns_scan_result(self, tmp_path):
        """run_scan returns a ScanResult instance."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert isinstance(result, ScanResult)

    def test_empty_directory_returns_zero_files(self, tmp_path):
        """Empty directory yields files_scanned == 0."""
        result = Scanner().run_scan(str(tmp_path))
        assert result.files_scanned == 0

    def test_files_scanned_matches_tf_count(self, tmp_path):
        """files_scanned equals the number of .tf files in the directory."""
        _write_tf(tmp_path, "a.tf", CLEAN_TF)
        _write_tf(tmp_path, "b.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert result.files_scanned == 2

    def test_non_tf_files_not_counted(self, tmp_path):
        """Non-.tf files are not counted in files_scanned."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        (tmp_path / "readme.txt").write_text("hello")
        result = Scanner().run_scan(str(tmp_path))
        assert result.files_scanned == 1

    def test_rules_loaded_is_positive(self, tmp_path):
        """rules_loaded reflects the number of built-in rules loaded."""
        result = Scanner().run_scan(str(tmp_path))
        assert result.rules_loaded > 0

    def test_findings_list_present(self, tmp_path):
        """ScanResult always has a findings list."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert isinstance(result.findings, list)

    def test_metadata_directory_matches(self, tmp_path):
        """ScanResult.metadata.scanned_directory matches the input directory."""
        result = Scanner().run_scan(str(tmp_path))
        assert result.metadata.scanned_directory == str(tmp_path)

    def test_statistics_total_resources_non_negative(self, tmp_path):
        """statistics.total_resources is non-negative."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert result.statistics.total_resources >= 0


# ---------------------------------------------------------------------------
# ScanError tests
# ---------------------------------------------------------------------------

class TestScanError:
    def test_raises_scan_error_for_nonexistent_directory(self):
        """ScanError is raised when the directory does not exist."""
        with pytest.raises(ScanError):
            Scanner().run_scan("/nonexistent/path/xyz_tmac_test")

    def test_raises_scan_error_for_file_path(self, tmp_path):
        """ScanError is raised when a file path is given instead of a directory."""
        f = tmp_path / "not_a_dir.tf"
        f.write_text("resource \"aws_s3_bucket\" \"x\" {}")
        with pytest.raises(ScanError):
            Scanner().run_scan(str(f))


# ---------------------------------------------------------------------------
# Exclude patterns
# ---------------------------------------------------------------------------

class TestExcludePatterns:
    def test_exclude_pattern_reduces_files_scanned(self, tmp_path):
        """Files matching an exclude pattern are not counted in files_scanned."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        _write_tf(tmp_path, "skip.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path), exclude_patterns=["skip.tf"])
        assert result.files_scanned == 1

    def test_exclude_all_tf_yields_zero_files(self, tmp_path):
        """Excluding *.tf results in files_scanned == 0."""
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path), exclude_patterns=["*.tf"])
        assert result.files_scanned == 0

    def test_exclude_subdirectory(self, tmp_path):
        """Files inside an excluded subdirectory are not scanned."""
        sub = tmp_path / ".terraform"
        sub.mkdir()
        _write_tf(sub, "hidden.tf", CLEAN_TF)
        _write_tf(tmp_path, "main.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path), exclude_patterns=[".terraform"])
        assert result.files_scanned == 1


# ---------------------------------------------------------------------------
# files_scanned / rules_loaded accuracy
# ---------------------------------------------------------------------------

class TestStatisticsAccuracy:
    def test_files_scanned_with_subdirectory(self, tmp_path):
        """files_scanned counts .tf files recursively."""
        sub = tmp_path / "modules"
        sub.mkdir()
        _write_tf(tmp_path, "root.tf", CLEAN_TF)
        _write_tf(sub, "module.tf", CLEAN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert result.files_scanned == 2

    def test_rules_loaded_consistent_across_calls(self, tmp_path):
        """rules_loaded is the same across multiple calls to the same directory."""
        r1 = Scanner().run_scan(str(tmp_path))
        r2 = Scanner().run_scan(str(tmp_path))
        assert r1.rules_loaded == r2.rules_loaded

    def test_findings_count_matches_statistics(self, tmp_path):
        """statistics.total_findings matches len(findings)."""
        _write_tf(tmp_path, "main.tf", PUBLIC_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert result.statistics.total_findings == len(result.findings)


# ---------------------------------------------------------------------------
# Property 1: run_scan returns a valid ScanResult for any directory
# Validates: Requirements 1.1, 9.2, 9.3, 9.4
# ---------------------------------------------------------------------------

@settings(max_examples=30)
@given(n_files=st.integers(min_value=0, max_value=5))
def test_property_1_run_scan_valid_scan_result(n_files):
    """
    **Property 1: run_scan returns a valid ScanResult for any directory**

    For any valid directory with .tf files, Scanner.run_scan() must return a
    ScanResult where:
    - files_scanned == number of .tf files found
    - rules_loaded == number of rules loaded (> 0 for built-in rules)
    - statistics.total_findings == len(findings)

    **Validates: Requirements 1.1, 9.2, 9.3, 9.4**
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for i in range(n_files):
            _write_tf(tmp_path, f"file_{i}.tf", CLEAN_TF)

        result = Scanner().run_scan(str(tmp_path))

        assert isinstance(result, ScanResult)
        assert result.files_scanned == n_files
        assert result.rules_loaded > 0
        assert result.statistics.total_findings == len(result.findings)
        assert result.statistics.total_resources >= 0


# ---------------------------------------------------------------------------
# tmac:ignore is bound to the exact resource (file + type + name)
# ---------------------------------------------------------------------------

IGNORED_PUBLIC_BUCKET_TF = """\
    # tmac:ignore
    resource "aws_s3_bucket" "main" {
      acl = "public-read"
    }

    resource "aws_security_group" "main" {
      ingress {
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
      }
    }
"""

UNIGNORED_PUBLIC_BUCKET_TF = """\
    resource "aws_s3_bucket" "main" {
      acl = "public-read"
    }
"""


class TestIgnoreScope:
    def test_ignore_does_not_leak_to_other_type_with_same_name(self, tmp_path):
        """Ignoring aws_s3_bucket.main must not silence aws_security_group.main."""
        _write_tf(tmp_path, "main.tf", IGNORED_PUBLIC_BUCKET_TF)
        result = Scanner().run_scan(str(tmp_path))
        types = {f.resource_type for f in result.findings}
        assert "aws_security_group" in types
        assert "aws_s3_bucket" not in types

    def test_ignore_does_not_leak_to_other_file_with_same_name(self, tmp_path):
        """Ignoring aws_s3_bucket.main in a.tf must not silence aws_s3_bucket.main in b.tf."""
        _write_tf(tmp_path, "a.tf", IGNORED_PUBLIC_BUCKET_TF)
        _write_tf(tmp_path, "b.tf", UNIGNORED_PUBLIC_BUCKET_TF)
        result = Scanner().run_scan(str(tmp_path))
        s3_files = {Path(f.file_path).name for f in result.findings if f.resource_type == "aws_s3_bucket"}
        assert s3_files == {"b.tf"}
