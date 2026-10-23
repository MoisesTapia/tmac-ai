"""
CLI tests for `tmac cfn`.

Validates: Requirement 17 (tmac-v1-2-cloudformation)
"""

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from tmac.cli import cli

CFN = Path(__file__).parent.parent / "fixtures" / "cfn"


@pytest.fixture
def runner():
    return CliRunner()


def _infra(tmp_path: Path, *fixtures: str) -> Path:
    infra = tmp_path / "infra"
    infra.mkdir()
    for name in fixtures:
        shutil.copy(CFN / name, infra / Path(name).name)
    return infra


def _cfn(runner, *args):
    return runner.invoke(cli, ["cfn", *args])


def test_critical_finding_exits_1(runner, tmp_path):
    infra = _infra(tmp_path, "services/s3_insecure.yaml")
    result = _cfn(runner, "--dir", str(infra), "-o", str(tmp_path / "r.html"))
    assert result.exit_code == 1
    assert "CFN scan complete:" in result.output


def test_high_without_critical_exits_2_with_fail_on_high(runner, tmp_path):
    infra = _infra(tmp_path, "services/cloudtrail_insecure.yaml")  # High + Medium
    result = _cfn(runner, "--dir", str(infra), "--fail-on", "high", "-o", str(tmp_path / "r.md"))
    assert result.exit_code == 2


def test_secure_templates_exit_0(runner, tmp_path):
    infra = _infra(tmp_path, "services/s3_secure.yaml", "services/iam_secure.yaml")
    result = _cfn(runner, "--dir", str(infra), "-o", str(tmp_path / "r.html"))
    assert result.exit_code == 0


def test_missing_directory_exits_3(runner, tmp_path):
    result = _cfn(runner, "--dir", str(tmp_path / "nope"), "-o", str(tmp_path / "r.html"))
    assert result.exit_code == 3


def test_invalid_template_exits_3_unless_lenient(runner, tmp_path):
    infra = _infra(tmp_path, "invalid/invalid_yaml.yaml")
    out = str(tmp_path / "r.json")
    assert _cfn(runner, "--dir", str(infra), "-r", "json", "-o", out).exit_code == 3
    assert _cfn(runner, "--dir", str(infra), "-r", "json", "-o", out, "--lenient").exit_code == 0


def test_default_report_name(runner, tmp_path, monkeypatch):
    infra = _infra(tmp_path, "services/s3_secure.yaml")
    monkeypatch.chdir(tmp_path)
    result = _cfn(runner, "--dir", str(infra), "-r", "md")
    assert result.exit_code == 0
    assert (tmp_path / "tmac-cfn-report.md").exists()
    assert "Report saved to tmac-cfn-report.md" in result.output


def test_json_report_and_quiet(runner, tmp_path):
    infra = _infra(tmp_path, "services/sg_insecure.yaml")
    out = tmp_path / "r.json"
    result = _cfn(runner, "--dir", str(infra), "-r", "json", "-o", str(out), "-q")
    assert result.output == ""
    rule_ids = {r["ruleId"] for r in json.loads(out.read_text())["runs"][0]["results"]}
    assert rule_ids == {"TMAC-CFN-SG-001", "TMAC-CFN-SG-002", "TMAC-CFN-SG-003"}


def test_exclude_and_severity_flags(runner, tmp_path):
    infra = _infra(tmp_path, "services/s3_insecure.yaml", "services/rds_insecure.yaml")
    out = tmp_path / "r.json"
    _cfn(
        runner, "--dir", str(infra), "-r", "json", "-o", str(out),
        "--exclude", "rds_*", "--severity", "critical",
    )  # fmt: skip
    rule_ids = {r["ruleId"] for r in json.loads(out.read_text())["runs"][0]["results"]}
    assert rule_ids == {"TMAC-CFN-S3-001"}


def test_scan_and_cfn_do_not_mix_frameworks(runner, tmp_path):
    infra = _infra(tmp_path, "services/s3_insecure.yaml")
    shutil.copy(CFN.parent / "s3_public_acl.tf", infra / "main.tf")
    for command, prefix in (("scan", "TMAC-AWS-"), ("cfn", "TMAC-CFN-")):
        out = tmp_path / f"{command}.json"
        runner.invoke(cli, [command, "--dir", str(infra), "-r", "json", "-o", str(out)])
        results = json.loads(out.read_text())["runs"][0]["results"]
        assert results and all(r["ruleId"].startswith(prefix) for r in results)


def test_help_lists_cfn_command(runner):
    assert "cfn" in runner.invoke(cli, ["--help"]).output
