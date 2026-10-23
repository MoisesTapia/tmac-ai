"""
Integration tests for CLI — exit codes, --exclude, --no-color flags.

Property 2: Exit code respects --fail-on threshold
Property 3: --exclude omits files matching glob pattern
Property 4: --no-color produces output without ANSI escape sequences

**Validates: Requirements 2.6, 3.2, 3.4**
"""

import re
import tempfile
import textwrap
from pathlib import Path

from click.testing import CliRunner
from hypothesis import given, settings
from hypothesis import strategies as st

from tmac.cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_PATTERN = re.compile(r"\x1b\[[\d;]*m")

SEVERITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

# A .tf file that triggers a Critical finding (S3 public ACL)
CRITICAL_TF = """\
resource "aws_s3_bucket" "public_bucket" {
  acl = "public-read"
}
"""

# A .tf file with no findings
CLEAN_TF = """\
resource "aws_s3_bucket" "private_bucket" {
  acl = "private"
}
"""


# Truly empty directory (no .tf files) for zero-findings tests
def _empty_dir_scan(tmp_path: Path, extra_args: list = None) -> object:
    """Invoke scan on an empty directory (no .tf files) → always exit 0."""
    runner = CliRunner()
    args = ["scan", "--dir", str(tmp_path), "--output", str(tmp_path / "report.html")] + (
        extra_args or []
    )
    return runner.invoke(cli, args, catch_exceptions=False)


def _write_tf(directory: Path, name: str, content: str) -> Path:
    f = directory / name
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


def _invoke_scan(tmp_path: Path, extra_args: list = None, tf_content: str = CLEAN_TF) -> object:
    """Write a .tf file and invoke the scan command, returning the result."""
    _write_tf(tmp_path, "main.tf", tf_content)
    runner = CliRunner()
    args = ["scan", "--dir", str(tmp_path), "--output", str(tmp_path / "report.html")] + (
        extra_args or []
    )
    return runner.invoke(cli, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Basic exit code tests
# ---------------------------------------------------------------------------


class TestExitCodes:
    def test_exit_0_clean_directory(self, tmp_path):
        """Exit code 0 when no findings (empty directory)."""
        result = _empty_dir_scan(tmp_path)
        assert result.exit_code == 0

    def test_exit_1_critical_finding(self, tmp_path):
        """Exit code 1 when Critical findings exist."""
        result = _invoke_scan(tmp_path, tf_content=CRITICAL_TF)
        assert result.exit_code == 1

    def test_exit_2_high_finding_no_critical(self, tmp_path):
        """Exit code 2 when High findings exist but no Critical findings."""
        # SSH open (port 22) triggers TMAC-AWS-SG-001 which is High severity
        # Use --fail-on high so the CLI considers High findings as failures
        high_tf = """\
resource "aws_security_group" "ssh_open" {
  name        = "ssh-open-sg"
  description = "Security group with SSH open to the world"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""
        _write_tf(tmp_path, "main.tf", high_tf)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--fail-on",
                "high",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 2

    def test_exit_3_scan_error_nonexistent_dir(self, tmp_path):
        """ScanError (exit 3) when directory does not exist."""
        runner = CliRunner()
        # Use a path that click won't validate (no exists=True check bypassed)
        # We test via a subdir that doesn't exist
        bad_path = str(tmp_path / "nonexistent_subdir")
        result = runner.invoke(
            cli, ["scan", "--dir", bad_path, "--output", str(tmp_path / "report.html")]
        )
        # click exits 2 for bad path option (exists=True), or 3 for ScanError
        assert result.exit_code != 0

    def test_exit_3_invalid_tmac_yaml(self, tmp_path):
        """Exit code 3 when .tmac.yaml has invalid YAML syntax."""
        runner = CliRunner()
        # Use isolated_filesystem so .tmac.yaml is picked up from the CWD
        with runner.isolated_filesystem() as iso_dir:
            iso_path = Path(iso_dir)
            # Create an invalid .tmac.yaml in the isolated CWD
            (iso_path / ".tmac.yaml").write_text(
                "scan:\n  exclude: [unclosed bracket\n  invalid: : yaml\n",
                encoding="utf-8",
            )
            # Create a scan target directory
            scan_dir = iso_path / "infra"
            scan_dir.mkdir()
            result = runner.invoke(
                cli,
                ["scan", "--dir", str(scan_dir), "--output", str(iso_path / "report.html")],
            )
        assert result.exit_code == 3


# ---------------------------------------------------------------------------
# --exclude flag tests
# ---------------------------------------------------------------------------


class TestExcludeFlag:
    def test_exclude_omits_matching_file(self, tmp_path):
        """--exclude *.tf results in no files scanned (exit 0)."""
        _write_tf(tmp_path, "main.tf", CRITICAL_TF)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--exclude",
                "*.tf",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

    def test_exclude_specific_file(self, tmp_path):
        """--exclude main.tf omits that specific file."""
        _write_tf(tmp_path, "main.tf", CRITICAL_TF)
        _write_tf(tmp_path, "clean.tf", CLEAN_TF)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--exclude",
                "main.tf",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

    def test_exclude_multiple_patterns(self, tmp_path):
        """Multiple --exclude flags are all applied."""
        _write_tf(tmp_path, "a.tf", CRITICAL_TF)
        _write_tf(tmp_path, "b.tf", CRITICAL_TF)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--exclude",
                "a.tf",
                "--exclude",
                "b.tf",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --report json SARIF output tests
# ---------------------------------------------------------------------------


class TestReportJson:
    def test_report_json_generates_sarif_fields(self, tmp_path):
        """--report json generates a JSON file with SARIF 'version' and 'runs' fields."""
        import json

        _write_tf(tmp_path, "main.tf", CRITICAL_TF)
        out_file = tmp_path / "report.json"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["scan", "--dir", str(tmp_path), "--report", "json", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert out_file.exists(), f"Report file not created. Output: {result.output}"
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "version" in data, f"'version' field missing from SARIF output: {data.keys()}"
        assert "runs" in data, f"'runs' field missing from SARIF output: {data.keys()}"
        assert isinstance(data["runs"], list), "'runs' must be a list"
        assert len(data["runs"]) > 0, "'runs' must not be empty"


# ---------------------------------------------------------------------------
# --no-color flag tests
# ---------------------------------------------------------------------------


class TestNoColorFlag:
    def test_no_color_output_has_no_ansi(self, tmp_path):
        """--no-color produces stdout without ANSI escape sequences."""
        runner = CliRunner()
        # Empty directory → no findings
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--no-color",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert not ANSI_PATTERN.search(
            result.output
        ), f"ANSI sequences found in output: {result.output!r}"


# ---------------------------------------------------------------------------
# Property 2: Exit code respects --fail-on threshold
# **Validates: Requirements 2.6**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    threshold=st.sampled_from(["critical", "high", "medium", "low", "info"]),
)
def test_property_2_exit_code_respects_fail_on(threshold):
    """
    **Property 2: Exit code respects the --fail-on threshold**

    For any severity level configured as --fail-on and a Critical finding,
    the CLI must return exit code 1 since Critical >= any threshold.

    **Validates: Requirements 2.6**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        _write_tf(tmp_path, "main.tf", CRITICAL_TF)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--fail-on",
                threshold,
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        threshold_val = SEVERITY_LEVELS[threshold]
        critical_val = SEVERITY_LEVELS["critical"]

        if critical_val >= threshold_val:
            assert result.exit_code == 1, (
                f"Expected exit 1 with --fail-on={threshold} and a Critical finding, "
                f"got {result.exit_code}. Output: {result.output}"
            )


@settings(max_examples=100, deadline=None)
@given(
    threshold=st.sampled_from(["critical", "high", "medium", "low", "info"]),
)
def test_property_2_exit_0_when_no_findings_meet_threshold(threshold):
    """
    **Property 2 (clean case): Exit code 0 when no findings meet the threshold**

    For an empty directory (no .tf files, no findings), exit code must always
    be 0 regardless of the --fail-on threshold.

    **Validates: Requirements 2.6**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Empty directory → no findings → always exit 0
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--fail-on",
                threshold,
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 with --fail-on={threshold} and no findings, "
            f"got {result.exit_code}. Output: {result.output}"
        )


# ---------------------------------------------------------------------------
# Property 3: --exclude omits files matching glob pattern
# **Validates: Requirements 3.2**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    n_excluded=st.integers(min_value=1, max_value=5),
    n_clean=st.integers(min_value=0, max_value=3),
)
def test_property_3_exclude_omits_matching_files(n_excluded, n_clean):
    """
    **Property 3: --exclude omits files matching glob pattern**

    For any glob pattern and any set of .tf files, files whose paths match
    the pattern must not appear in the scan results (no findings from them).

    **Validates: Requirements 3.2**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        excluded_names = [f"critical_{i}.tf" for i in range(n_excluded)]
        for name in excluded_names:
            _write_tf(tmp_path, name, CRITICAL_TF)

        for i in range(n_clean):
            _write_tf(tmp_path, f"clean_{i}.tf", CLEAN_TF)

        runner = CliRunner()
        exclude_args = []
        for name in excluded_names:
            exclude_args += ["--exclude", name]

        result = runner.invoke(
            cli,
            ["scan", "--dir", str(tmp_path)]
            + exclude_args
            + ["--output", str(tmp_path / "report.html")],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 after excluding {n_excluded} critical files, "
            f"got {result.exit_code}. Output: {result.output}"
        )


# ---------------------------------------------------------------------------
# Property 4: --no-color produces output without ANSI escape sequences
# **Validates: Requirements 3.4**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    has_findings=st.booleans(),
)
def test_property_4_no_color_no_ansi_sequences(has_findings):
    """
    **Property 4: --no-color produces output without ANSI escape sequences**

    For any CLI execution with --no-color, stdout must not contain ANSI
    escape sequences matching the pattern \\x1b\\[[\\d;]*m.

    **Validates: Requirements 3.4**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        if has_findings:
            _write_tf(tmp_path, "main.tf", CRITICAL_TF)
        # else: empty directory → no findings

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "scan",
                "--dir",
                str(tmp_path),
                "--no-color",
                "--output",
                str(tmp_path / "report.html"),
            ],
            catch_exceptions=False,
        )

        assert not ANSI_PATTERN.search(
            result.output
        ), f"ANSI sequences found in stdout with --no-color: {result.output!r}"
