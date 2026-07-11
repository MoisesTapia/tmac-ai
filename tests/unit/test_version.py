"""
Unit tests for version reporting.

Validates: Requirements 8.2, 8.6, 8.7
"""
import tomllib
from pathlib import Path

from click.testing import CliRunner

from tmac.cli import cli

# Path to the project root (two levels up from this file: tests/unit/ -> tests/ -> project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

EXPECTED_VERSION = "1.6.0"


def test_cli_version_flag_exit_code_and_output() -> None:
    """tmac --version exits 0 and prints the expected version string (R8.6)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
    assert EXPECTED_VERSION in result.output, (
        f"Expected '{EXPECTED_VERSION}' in version output, got: {result.output!r}"
    )


def test_pyproject_version_and_console_script() -> None:
    """pyproject.toml declares version 1.6.0 and the tmac console script entry (R8.7, R8.2)."""
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)

    # R8.7 — package version must be 1.6.0
    version = data["tool"]["poetry"]["version"]
    assert version == EXPECTED_VERSION, (
        f"pyproject.toml version should be '{EXPECTED_VERSION}', got '{version}'"
    )

    # R8.2 — the tmac console script entry must be present and point to tmac.cli:cli
    scripts = data["tool"]["poetry"]["scripts"]
    assert "tmac" in scripts, f"'tmac' console script not found in [tool.poetry.scripts]: {scripts}"
    assert scripts["tmac"] == "tmac.cli:cli", (
        f"Expected script entry 'tmac.cli:cli', got '{scripts['tmac']}'"
    )
