"""
Integration tests for fail-closed behaviour (incomplete scans exit 3) and for
.tmac.yaml / --config / plan --source-dir / version handling.
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from tmac import __version__
from tmac.cli import cli
from tmac.delta.models import ChangeAction, PlannedChange
from tmac.delta.scanner import DeltaScanner
from tmac.models.rule import CheckCondition, ThreatRule
from tmac.scanner import Scanner

FIXTURES = Path(__file__).parent.parent / "fixtures"
CREATE_PLAN = FIXTURES / "plans" / "create_with_threat.json"

HIGH_ONLY_TF = """\
resource "aws_security_group" "ssh_open" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""

BROKEN_TF = 'resource "aws_s3_bucket" "broken" {\n  acl = \n'

INVALID_RULES_YAML = """\
version: "1.0"
rules:
  - id: TMAC-CUSTOM-BAD
    name: Typo in severity
    resource_type: aws_s3_bucket
    check: {attribute: acl, condition: equals, values: [public-read]}
    severity: Critcal
    stride: Tampering
    description: d
    mitigation: m
"""


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def _scan(runner, tmp_path, *args):
    out = tmp_path / "report.json"
    result = runner.invoke(cli, ["scan", "--report", "json", "--output", str(out), *args])
    return result, out


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# C — fail closed: unparseable files / invalid rules make the scan exit 3
# ---------------------------------------------------------------------------


class TestIncompleteScanFailsClosed:
    def test_unparseable_file_is_recorded_as_issue(self, tmp_path):
        _write(tmp_path / "broken.tf", BROKEN_TF)
        result = Scanner().run_scan(str(tmp_path))
        assert [i.kind for i in result.issues] == ["parse"]
        assert result.issues[0].file_path.endswith("broken.tf")

    def test_unparseable_file_exits_3_but_still_writes_report(self, runner, tmp_path):
        _write(tmp_path / "infra" / "broken.tf", BROKEN_TF)
        result, out = _scan(runner, tmp_path, "--dir", str(tmp_path / "infra"))
        assert result.exit_code == 3
        assert "incomplete" in result.output.lower()
        sarif = json.loads(out.read_text(encoding="utf-8"))
        invocation = sarif["runs"][0]["invocations"][0]
        assert invocation["executionSuccessful"] is False
        assert invocation["toolExecutionNotifications"][0]["descriptor"]["id"] == "tmac/parse-error"

    def test_lenient_restores_findings_based_exit_code(self, runner, tmp_path):
        _write(tmp_path / "infra" / "broken.tf", BROKEN_TF)
        result, _ = _scan(runner, tmp_path, "--dir", str(tmp_path / "infra"), "--lenient")
        assert result.exit_code == 0
        assert "incomplete" in result.output.lower()  # still warned on stderr

    def test_invalid_custom_rule_exits_3(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        rules_dir = tmp_path / "rules"
        _write(rules_dir / "custom.yaml", INVALID_RULES_YAML)
        result, _ = _scan(
            runner, tmp_path, "--dir", str(tmp_path / "infra"), "--rules-dir", str(rules_dir)
        )
        assert result.exit_code == 3
        assert "TMAC-CUSTOM-BAD" in result.output

    def test_plan_with_invalid_custom_rule_exits_3(self, runner, tmp_path):
        rules_dir = tmp_path / "rules"
        _write(rules_dir / "custom.yaml", INVALID_RULES_YAML)
        result = runner.invoke(
            cli,
            [
                "plan",
                "-p",
                str(CREATE_PLAN),
                "--rules-dir",
                str(rules_dir),
                "-r",
                "json",
                "-o",
                str(tmp_path / "d.json"),
            ],
        )
        assert result.exit_code == 3

    def test_complete_scan_reports_success(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        result, out = _scan(runner, tmp_path, "--dir", str(tmp_path / "infra"))
        assert result.exit_code == 0  # High finding, default --fail-on critical
        sarif = json.loads(out.read_text(encoding="utf-8"))
        assert sarif["runs"][0]["invocations"][0]["executionSuccessful"] is True

    @pytest.mark.parametrize("fmt", ["html", "md"])
    def test_human_reports_show_incomplete_banner(self, runner, tmp_path, fmt):
        _write(tmp_path / "infra" / "broken.tf", BROKEN_TF)
        out = tmp_path / f"report.{fmt}"
        runner.invoke(cli, ["scan", "--dir", str(tmp_path / "infra"), "-r", fmt, "-o", str(out)])
        assert "Incomplete scan" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# D — configuration is honoured
# ---------------------------------------------------------------------------


class TestConfigHandling:
    def test_nonexistent_dir_exits_3(self, runner, tmp_path):
        result, _ = _scan(runner, tmp_path, "--dir", str(tmp_path / "nope"))
        assert result.exit_code == 3

    def test_explicit_missing_config_exits_3(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        result, _ = _scan(
            runner,
            tmp_path,
            "--dir",
            str(tmp_path / "infra"),
            "--config",
            str(tmp_path / "missing.yaml"),
        )
        assert result.exit_code == 3
        assert "Config file not found" in result.output

    def test_config_report_fail_on_is_applied(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        cfg = _write(tmp_path / "custom.yaml", "report:\n  fail_on: high\n")
        result, _ = _scan(runner, tmp_path, "--dir", str(tmp_path / "infra"), "--config", str(cfg))
        assert result.exit_code == 2

    def test_cli_flag_overrides_config(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        cfg = _write(tmp_path / "custom.yaml", "report:\n  fail_on: high\n")
        result, _ = _scan(
            runner,
            tmp_path,
            "--dir",
            str(tmp_path / "infra"),
            "--config",
            str(cfg),
            "--fail-on",
            "critical",
        )
        assert result.exit_code == 0

    def test_config_report_format_and_severity_are_applied(self, runner, tmp_path):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        cfg = _write(tmp_path / "custom.yaml", "report:\n  format: json\n  severity: critical\n")
        out = tmp_path / "out.txt"
        runner.invoke(
            cli, ["scan", "--dir", str(tmp_path / "infra"), "--config", str(cfg), "-o", str(out)]
        )
        sarif = json.loads(out.read_text(encoding="utf-8"))  # json, not the html default
        assert sarif["runs"][0]["results"] == []  # High filtered out by severity: critical

    def test_config_scan_dir_used_when_no_dir_flag(self, runner, tmp_path, monkeypatch):
        _write(tmp_path / "infra" / "main.tf", HIGH_ONLY_TF)
        _write(tmp_path / ".tmac.yaml", "scan:\n  dir: infra\nreport:\n  fail_on: high\n")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["scan", "-r", "json", "-o", "r.json"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# D — tmac plan honours tmac:ignore from the .tf sources
# ---------------------------------------------------------------------------


class TestPlanIgnores:
    def _plan(self, runner, tmp_path, *args):
        out = tmp_path / "d.json"
        result = runner.invoke(
            cli, ["plan", "-p", str(CREATE_PLAN), "-r", "json", "-o", str(out), *args]
        )
        return result, {
            r["ruleId"] for r in json.loads(out.read_text(encoding="utf-8"))["runs"][0]["results"]
        }

    def test_without_source_dir_nothing_is_ignored(self, runner, tmp_path):
        result, rule_ids = self._plan(runner, tmp_path)
        assert "TMAC-AWS-S3-001" in rule_ids and result.exit_code == 1

    def test_global_ignore_from_source_dir(self, runner, tmp_path):
        src = tmp_path / "src"
        _write(
            src / "main.tf",
            '# tmac:ignore\nresource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n',
        )
        result, rule_ids = self._plan(runner, tmp_path, "--source-dir", str(src))
        assert rule_ids == set() and result.exit_code == 0

    def test_per_rule_ignore_from_source_dir(self, runner, tmp_path):
        src = tmp_path / "src"
        _write(
            src / "main.tf",
            '# tmac:ignore[TMAC-AWS-S3-001]\nresource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n',
        )
        _, rule_ids = self._plan(runner, tmp_path, "--source-dir", str(src))
        assert "TMAC-AWS-S3-001" not in rule_ids
        assert "TMAC-AWS-S3-002" in rule_ids

    def test_ignore_for_other_type_with_same_name_does_not_apply(self, runner, tmp_path):
        src = tmp_path / "src"
        _write(src / "main.tf", '# tmac:ignore\nresource "aws_db_instance" "data" {\n}\n')
        _, rule_ids = self._plan(runner, tmp_path, "--source-dir", str(src))
        assert "TMAC-AWS-S3-001" in rule_ids


# ---------------------------------------------------------------------------
# D — delta values for nested attributes / version
# ---------------------------------------------------------------------------


def test_delta_finding_resolves_nested_attribute_values():
    rule = ThreatRule(
        id="TMAC-TEST-NESTED",
        name="Versioning disabled",
        resource_type="aws_s3_bucket",
        check=CheckCondition(attribute="versioning.enabled", condition="equals", values=[False]),
        severity="Medium",
        stride="Tampering",
        description="d",
        mitigation="m",
    )
    change = PlannedChange(
        address="aws_s3_bucket.b",
        resource_type="aws_s3_bucket",
        resource_name="b",
        action=ChangeAction.update,
        before={"versioning": [{"enabled": True}]},
        after={"versioning": [{"enabled": False}]},
    )
    introduced, _ = DeltaScanner()._evaluate_change(change, [rule])
    assert len(introduced) == 1
    assert introduced[0].value_before == [True]
    assert introduced[0].value_after == [False]


def test_version_flag_reports_package_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert __version__ in result.output


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib needs Python 3.11+")
def test_package_version_matches_pyproject():
    import tomllib

    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    assert (
        tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["poetry"]["version"]
        == __version__
    )
